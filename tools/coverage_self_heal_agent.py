#!/usr/bin/env python3
"""Autonomous Docker-aware monitoring and self-healing agent for /coverage.

This tool runs an observe-diagnose-heal loop for a bounded duration (default: 1h)
and emits one structured JSON record per cycle.

Safety rules:
- No destructive operations (no deletes, no volume prune, no hard resets).
- Container restarts are rate-limited with per-target cooldown/backoff.
- Pipeline remediation is idempotent (re-trigger safe tasks only).
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_percent(value: str) -> float:
    """Parse Docker percent values like '12.3%' to float."""
    cleaned = value.strip().replace("%", "")
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def json_print(payload: dict[str, Any], log_path: Path | None) -> None:
    line = json.dumps(payload, ensure_ascii=True)
    print(line, flush=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")


@dataclass
class AgentConfig:
    duration_seconds: int = 3600
    sleep_min_seconds: int = 10
    sleep_max_seconds: int = 30
    coverage_url: str = "http://localhost:8000/public/coverage/v2/summary"
    sources_url: str = "http://localhost:8000/public/coverage/v2/sources?offset=0&limit=100"
    analytics_url: str = "http://localhost:8000/public/coverage/v2/analytics"
    restart_backoff_seconds: int = 180
    max_restarts_per_target: int = 3
    max_logs_tail_lines: int = 160
    cpu_warn_percent: float = 85.0
    mem_warn_percent: float = 85.0
    dry_run: bool = False
    log_file: Path | None = None
    compose_files: list[str] = field(default_factory=list)


@dataclass
class CommandResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str


class CoverageSelfHealAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.start_ts = time.time()
        self.cycle_index = 0
        self.restart_history: dict[str, list[float]] = {}
        self.last_action_at: dict[str, float] = {}

    def run(self) -> int:
        deadline = self.start_ts + self.config.duration_seconds

        while time.time() < deadline:
            self.cycle_index += 1
            cycle_id = f"cycle-{self.cycle_index:05d}"

            snapshot = self.collect_snapshot()
            issues, gaps = self.diagnose(snapshot)
            actions = self.heal(snapshot, issues, gaps)

            payload = self.build_output(cycle_id, snapshot, issues, actions, gaps)
            json_print(payload, self.config.log_file)

            sleep_seconds = random.randint(
                self.config.sleep_min_seconds,
                self.config.sleep_max_seconds,
            )
            time.sleep(sleep_seconds)

        return 0

    def compose_prefix(self) -> list[str]:
        prefix = ["docker", "compose"]
        for compose_file in self.config.compose_files:
            prefix.extend(["-f", compose_file])
        return prefix

    def run_cmd(self, args: list[str], timeout: int = 30) -> CommandResult:
        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return CommandResult(
                ok=completed.returncode == 0,
                returncode=completed.returncode,
                stdout=completed.stdout.strip(),
                stderr=completed.stderr.strip(),
            )
        except Exception as exc:  # noqa: BLE001
            return CommandResult(ok=False, returncode=1, stdout="", stderr=str(exc))

    def fetch_json_via_curl(self, url: str, timeout: int = 15) -> tuple[dict[str, Any] | None, str | None]:
        result = self.run_cmd(["curl", "-fsS", "--max-time", str(timeout), url], timeout=timeout + 2)
        if not result.ok:
            return None, result.stderr or f"curl failed rc={result.returncode}"

        try:
            return json.loads(result.stdout), None
        except json.JSONDecodeError as exc:
            return None, f"invalid json from {url}: {exc}"

    def collect_docker_ps(self) -> list[dict[str, Any]]:
        compose_ps = self.run_cmd(self.compose_prefix() + ["ps", "--all", "--format", "json"])
        if compose_ps.ok and compose_ps.stdout:
            try:
                parsed = json.loads(compose_ps.stdout)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        raw_ps = self.run_cmd(
            [
                "docker",
                "ps",
                "--all",
                "--format",
                "{{json .}}",
            ]
        )
        rows: list[dict[str, Any]] = []
        if raw_ps.ok and raw_ps.stdout:
            for line in raw_ps.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def collect_docker_stats(self) -> dict[str, dict[str, float]]:
        stats = self.run_cmd(["docker", "stats", "--no-stream", "--format", "{{json .}}"], timeout=25)
        per_container: dict[str, dict[str, float]] = {}
        if not stats.ok or not stats.stdout:
            return per_container

        for line in stats.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = item.get("Name") or item.get("Container") or item.get("ID")
            if not name:
                continue
            per_container[str(name)] = {
                "cpu_percent": parse_percent(str(item.get("CPUPerc", "0"))),
                "memory_percent": parse_percent(str(item.get("MemPerc", "0"))),
            }
        return per_container

    def inspect_container_state(self, container_id_or_name: str) -> dict[str, Any]:
        cmd = ["docker", "inspect", container_id_or_name]
        result = self.run_cmd(cmd)
        if not result.ok or not result.stdout:
            return {}
        try:
            data = json.loads(result.stdout)
            if isinstance(data, list) and data:
                row = data[0]
                state = row.get("State", {})
                return {
                    "status": state.get("Status", "unknown"),
                    "health": (state.get("Health") or {}).get("Status", "unknown"),
                    "restart_count": int(row.get("RestartCount", 0)),
                }
        except Exception:  # noqa: BLE001
            return {}
        return {}

    def collect_logs(self, container_names: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in container_names:
            result = self.run_cmd(["docker", "logs", "--tail", str(self.config.max_logs_tail_lines), name])
            if result.ok:
                out[name] = result.stdout
            else:
                out[name] = result.stderr
        return out

    def collect_snapshot(self) -> dict[str, Any]:
        ps_rows = self.collect_docker_ps()
        stats_rows = self.collect_docker_stats()
        summary, summary_error = self.fetch_json_via_curl(self.config.coverage_url)
        sources, sources_error = self.fetch_json_via_curl(self.config.sources_url)
        analytics, analytics_error = self.fetch_json_via_curl(self.config.analytics_url)

        containers: list[dict[str, Any]] = []
        for row in ps_rows:
            cid = str(row.get("ID") or row.get("Id") or row.get("ContainerID") or row.get("Name") or "")
            name = str(row.get("Name") or row.get("Names") or cid)
            service = str(row.get("Service") or row.get("service") or "")
            status = str(row.get("Status") or row.get("State") or "")
            state = str(row.get("State") or "")

            inspect = self.inspect_container_state(cid or name)
            stat_key = name if name in stats_rows else cid
            usage = stats_rows.get(stat_key, {"cpu_percent": 0.0, "memory_percent": 0.0})

            containers.append(
                {
                    "id": cid,
                    "name": name,
                    "service": service,
                    "status": status,
                    "state": state,
                    "health": inspect.get("health", "unknown"),
                    "restart_count": inspect.get("restart_count", 0),
                    "cpu_percent": usage["cpu_percent"],
                    "memory_percent": usage["memory_percent"],
                }
            )

        # Correlate logs from key containers only to reduce overhead.
        log_targets = [
            c["name"]
            for c in containers
            if any(k in c["name"].lower() for k in ("worker", "postgres", "api", "redis"))
        ]
        logs = self.collect_logs(log_targets[:8])

        return {
            "containers": containers,
            "coverage_summary": summary,
            "coverage_summary_error": summary_error,
            "coverage_sources": sources,
            "coverage_sources_error": sources_error,
            "coverage_analytics": analytics,
            "coverage_analytics_error": analytics_error,
            "logs": logs,
        }

    def diagnose(self, snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        issues: list[dict[str, Any]] = []
        gaps: list[dict[str, str]] = []

        containers = snapshot["containers"]
        summary = snapshot.get("coverage_summary") or {}
        sources = snapshot.get("coverage_sources") or {}

        # Coverage endpoint availability.
        for key in ("coverage_summary_error", "coverage_sources_error", "coverage_analytics_error"):
            if snapshot.get(key):
                issues.append(
                    {
                        "type": "pipeline",
                        "description": f"{key} detected",
                        "affected_entities": ["/coverage"],
                        "root_cause": str(snapshot.get(key)),
                    }
                )

        running_count = 0
        unhealthy = 0
        for c in containers:
            status_text = f"{c.get('status', '')} {c.get('state', '')}".lower()
            is_running = "running" in status_text
            if is_running:
                running_count += 1

            if c.get("health") == "unhealthy" or "unhealthy" in status_text:
                unhealthy += 1
                issues.append(
                    {
                        "type": "container",
                        "description": "Container unhealthy",
                        "affected_entities": [c["name"]],
                        "root_cause": "healthcheck failing",
                    }
                )
                gaps.append(
                    {
                        "category": "container",
                        "description": f"unhealthy container {c['name']}",
                    }
                )

            if "exited" in status_text or "dead" in status_text:
                issues.append(
                    {
                        "type": "container",
                        "description": "Container stopped unexpectedly",
                        "affected_entities": [c["name"]],
                        "root_cause": c.get("status", "unknown"),
                    }
                )

            if int(c.get("restart_count", 0)) >= 5:
                issues.append(
                    {
                        "type": "container",
                        "description": "Possible restart loop",
                        "affected_entities": [c["name"]],
                        "root_cause": f"restart_count={c.get('restart_count', 0)}",
                    }
                )

            if c.get("cpu_percent", 0.0) > self.config.cpu_warn_percent:
                issues.append(
                    {
                        "type": "resource",
                        "description": "Container CPU pressure",
                        "affected_entities": [c["name"]],
                        "root_cause": f"cpu={c.get('cpu_percent', 0.0):.1f}%",
                    }
                )

            if c.get("memory_percent", 0.0) > self.config.mem_warn_percent:
                issues.append(
                    {
                        "type": "resource",
                        "description": "Container memory pressure",
                        "affected_entities": [c["name"]],
                        "root_cause": f"memory={c.get('memory_percent', 0.0):.1f}%",
                    }
                )

        totals = (summary.get("totals") or {}) if isinstance(summary, dict) else {}
        runtime = totals.get("runtime") or {}
        jobs_total = int(totals.get("jobs", 0) or 0)
        jobs_running = int(runtime.get("running", 0) or 0)
        jobs_failed = int(runtime.get("failed_or_stuck", 0) or 0)
        jobs_idle = max(jobs_total - jobs_running - jobs_failed, 0)

        if jobs_failed > 0:
            issues.append(
                {
                    "type": "job",
                    "description": "failed or stuck jobs reported by /coverage",
                    "affected_entities": ["coverage_runtime"],
                    "root_cause": f"failed_or_stuck={jobs_failed}",
                }
            )
            gaps.append(
                {
                    "category": "pipeline",
                    "description": f"{jobs_failed} jobs are failed/stuck",
                }
            )

        if jobs_idle > 0 and jobs_total > 0:
            gaps.append(
                {
                    "category": "resource",
                    "description": f"{jobs_idle} jobs idle according to pipeline snapshot",
                }
            )

        worker_running = [
            c
            for c in containers
            if "worker" in c["name"].lower()
            and "running" in f"{c.get('status', '')} {c.get('state', '')}".lower()
        ]
        if jobs_total > 0 and jobs_running == 0 and jobs_failed < jobs_total and worker_running:
            gaps.append(
                {
                    "category": "pipeline",
                    "description": "Idle workers while jobs appear pending or stale",
                }
            )
            issues.append(
                {
                    "type": "job",
                    "description": "Jobs not progressing while workers are available",
                    "affected_entities": [c["name"] for c in worker_running],
                    "root_cause": "possible missing trigger, queue mismatch, or upstream lock",
                }
            )

        # Source-level gaps from /coverage/v2/sources.
        source_items = []
        if isinstance(sources, dict):
            raw_items = sources.get("items")
            if isinstance(raw_items, list):
                source_items = raw_items

        stale_sources = 0
        for item in source_items:
            status = str(item.get("status", "")).lower()
            if status in {"stale", "error", "pending", "warning"}:
                stale_sources += 1
                name = str(item.get("connector") or item.get("name") or "source")
                issues.append(
                    {
                        "type": "data_source",
                        "description": f"source with non-healthy status: {status}",
                        "affected_entities": [name],
                        "root_cause": "ingestion lag or upstream source issue",
                    }
                )

        if stale_sources > 0:
            gaps.append(
                {
                    "category": "data_source",
                    "description": f"{stale_sources} data sources are stale/pending/error",
                }
            )

        # Typology analytics gaps if present.
        analytics = snapshot.get("coverage_analytics")
        if isinstance(analytics, dict):
            typologies = analytics.get("typologies")
            if isinstance(typologies, list):
                missing = [t for t in typologies if str(t.get("status", "")).lower() in {"missing", "stale", "partial"}]
                if missing:
                    gaps.append(
                        {
                            "category": "typology",
                            "description": f"{len(missing)} typologies have missing/partial/stale coverage",
                        }
                    )

        # Log correlation patterns.
        log_text = "\n".join(str(v) for v in snapshot.get("logs", {}).values())
        patterns = {
            "deadlock": r"deadlock|could not obtain lock|lock timeout",
            "timeout": r"timed out|statement timeout|soft time limit exceeded",
            "retry": r"task\.retry|retrying|max retries",
            "connectivity": r"connection refused|could not connect|name or service not known",
            "misconfiguration": r"no module named|keyerror|valueerror|traceback",
        }
        for label, pat in patterns.items():
            if re.search(pat, log_text, flags=re.IGNORECASE):
                issues.append(
                    {
                        "type": "database" if label in {"deadlock", "timeout"} else "job",
                        "description": f"log pattern detected: {label}",
                        "affected_entities": list(snapshot.get("logs", {}).keys())[:4],
                        "root_cause": f"pattern={label}",
                    }
                )

        return issues, gaps

    def can_restart(self, target: str) -> tuple[bool, str]:
        now = time.time()
        last = self.last_action_at.get(target, 0.0)
        if now - last < self.config.restart_backoff_seconds:
            return False, "restart cooldown active"

        history = [ts for ts in self.restart_history.get(target, []) if now - ts < 3600]
        self.restart_history[target] = history
        if len(history) >= self.config.max_restarts_per_target:
            return False, "max restarts per target reached"
        return True, "allowed"

    def restart_container(self, target: str) -> tuple[bool, str]:
        allowed, reason = self.can_restart(target)
        if not allowed:
            return False, reason

        if self.config.dry_run:
            self.last_action_at[target] = time.time()
            self.restart_history.setdefault(target, []).append(time.time())
            return True, "dry-run"

        result = self.run_cmd(["docker", "restart", target], timeout=45)
        if result.ok:
            self.last_action_at[target] = time.time()
            self.restart_history.setdefault(target, []).append(time.time())
            return True, "restarted"
        return False, result.stderr or "restart failed"

    def trigger_ingest_incremental(self) -> tuple[bool, str]:
        cmd = self.compose_prefix() + [
            "exec",
            "-T",
            "worker-primary",
            "python",
            "-c",
            "from worker.worker_app import app; r=app.send_task('worker.tasks.ingest_tasks.ingest_all_incremental'); print(r.id)",
        ]
        if self.config.dry_run:
            return True, "dry-run"
        result = self.run_cmd(cmd, timeout=60)
        if result.ok:
            return True, "ingest trigger dispatched"
        return False, result.stderr or "ingest trigger failed"

    def trigger_coverage_refresh(self) -> tuple[bool, str]:
        cmd = self.compose_prefix() + [
            "exec",
            "-T",
            "worker-primary",
            "python",
            "-c",
            "from worker.worker_app import app; r=app.send_task('worker.tasks.coverage_tasks.update_coverage_registry'); print(r.id)",
        ]
        if self.config.dry_run:
            return True, "dry-run"
        result = self.run_cmd(cmd, timeout=60)
        if result.ok:
            return True, "coverage refresh dispatched"
        return False, result.stderr or "coverage refresh failed"

    def trigger_cleanup_stale_runs(self) -> tuple[bool, str]:
        cmd = self.compose_prefix() + [
            "exec",
            "-T",
            "worker-primary",
            "python",
            "-c",
            "from worker.worker_app import app; r=app.send_task('worker.tasks.maintenance_tasks.cleanup_stale_runs', kwargs={'max_age_hours': 2}); print(r.id)",
        ]
        if self.config.dry_run:
            return True, "dry-run"
        result = self.run_cmd(cmd, timeout=60)
        if result.ok:
            return True, "cleanup stale runs dispatched"
        return False, result.stderr or "cleanup stale runs failed"

    def heal(
        self,
        snapshot: dict[str, Any],
        issues: list[dict[str, Any]],
        gaps: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        actions: list[dict[str, str]] = []
        containers = snapshot["containers"]

        # Container-level remediation.
        for c in containers:
            name = c["name"]
            status_text = f"{c.get('status', '')} {c.get('state', '')}".lower()
            is_unhealthy = c.get("health") == "unhealthy" or "unhealthy" in status_text
            is_stopped = "exited" in status_text or "dead" in status_text

            # Act only on service containers relevant to the ingestion platform.
            if not any(k in name.lower() for k in ("worker", "api", "postgres", "redis")):
                continue

            if is_unhealthy or is_stopped:
                ok, details = self.restart_container(name)
                actions.append(
                    {
                        "action": "restart_container",
                        "target": name,
                        "reason": "health/stopped container remediation",
                        "result": "success" if ok else f"failure ({details})",
                    }
                )

        # Pipeline-level remediation.
        has_job_issue = any(i.get("type") in {"job", "pipeline", "data_source"} for i in issues)
        has_pipeline_gap = any(g.get("category") in {"pipeline", "data_source", "typology"} for g in gaps)
        if has_job_issue or has_pipeline_gap:
            has_failed_stuck = any(
                i.get("type") == "job"
                and "failed or stuck jobs" in str(i.get("description", "")).lower()
                for i in issues
            )
            if has_failed_stuck:
                ok0, details0 = self.trigger_cleanup_stale_runs()
                actions.append(
                    {
                        "action": "requeue_job",
                        "target": "worker.tasks.maintenance_tasks.cleanup_stale_runs",
                        "reason": "clear orphaned stale runs before re-triggering pipeline",
                        "result": "success" if ok0 else f"failure ({details0})",
                    }
                )

            ok, details = self.trigger_ingest_incremental()
            actions.append(
                {
                    "action": "trigger_ingestion",
                    "target": "worker.tasks.ingest_tasks.ingest_all_incremental",
                    "reason": "pipeline/data-source issue detected",
                    "result": "success" if ok else f"failure ({details})",
                }
            )

            ok2, details2 = self.trigger_coverage_refresh()
            actions.append(
                {
                    "action": "requeue_job",
                    "target": "worker.tasks.coverage_tasks.update_coverage_registry",
                    "reason": "refresh /coverage after remediation trigger",
                    "result": "success" if ok2 else f"failure ({details2})",
                }
            )

        # DB-lock style issue: recycle heavy worker first (safe) instead of DB restarts.
        db_lock_issue = any("deadlock" in str(i.get("description", "")).lower() for i in issues)
        if db_lock_issue:
            heavy = next((c for c in containers if "worker-heavy" in c["name"].lower()), None)
            if heavy is not None:
                ok, details = self.restart_container(heavy["name"])
                actions.append(
                    {
                        "action": "fix_db_lock",
                        "target": heavy["name"],
                        "reason": "deadlock-like log pattern detected",
                        "result": "success" if ok else f"failure ({details})",
                    }
                )

        return actions

    def build_output(
        self,
        cycle_id: str,
        snapshot: dict[str, Any],
        issues: list[dict[str, Any]],
        actions: list[dict[str, str]],
        gaps: list[dict[str, str]],
    ) -> dict[str, Any]:
        containers = snapshot["containers"]
        summary = snapshot.get("coverage_summary") or {}
        totals = summary.get("totals") or {}
        runtime = totals.get("runtime") or {}

        running = [
            c
            for c in containers
            if "running" in f"{c.get('status', '')} {c.get('state', '')}".lower()
        ]
        unhealthy = [c for c in containers if c.get("health") == "unhealthy" or "unhealthy" in str(c.get("status", "")).lower()]

        avg_cpu = 0.0
        avg_mem = 0.0
        if running:
            avg_cpu = sum(float(c.get("cpu_percent", 0.0)) for c in running) / len(running)
            avg_mem = sum(float(c.get("memory_percent", 0.0)) for c in running) / len(running)

        jobs_total = int(totals.get("jobs", 0) or 0)
        jobs_running = int(runtime.get("running", 0) or 0)
        jobs_failed = int(runtime.get("failed_or_stuck", 0) or 0)
        jobs_idle = max(jobs_total - jobs_running - jobs_failed, 0)

        next_steps: list[str] = []
        if jobs_failed > 0:
            next_steps.append("verify failed/stuck jobs after re-trigger")
        if unhealthy:
            next_steps.append("re-check container health and restart counters")
        if not next_steps:
            next_steps.append("continue monitoring for regressions")

        return {
            "timestamp": utc_now_iso(),
            "cycle_id": cycle_id,
            "docker": {
                "containers_total": len(containers),
                "containers_running": len(running),
                "containers_unhealthy": len(unhealthy),
                "resource_usage": {
                    "cpu_percent": round(avg_cpu, 2),
                    "memory_percent": round(avg_mem, 2),
                },
            },
            "pipeline": {
                "jobs_total": jobs_total,
                "jobs_running": jobs_running,
                "jobs_failed": jobs_failed,
                "jobs_idle": jobs_idle,
            },
            "issues_detected": issues,
            "actions_taken": actions,
            "gaps_identified": gaps,
            "next_steps": next_steps,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Autonomous Docker-aware monitor and self-healing loop for /coverage",
    )
    parser.add_argument("--duration-seconds", type=int, default=3600)
    parser.add_argument("--sleep-min-seconds", type=int, default=10)
    parser.add_argument("--sleep-max-seconds", type=int, default=30)
    parser.add_argument("--coverage-url", default="http://localhost:8000/public/coverage/v2/summary")
    parser.add_argument("--sources-url", default="http://localhost:8000/public/coverage/v2/sources?offset=0&limit=100")
    parser.add_argument("--analytics-url", default="http://localhost:8000/public/coverage/v2/analytics")
    parser.add_argument("--restart-backoff-seconds", type=int, default=180)
    parser.add_argument("--max-restarts-per-target", type=int, default=3)
    parser.add_argument("--cpu-warn-percent", type=float, default=85.0)
    parser.add_argument("--mem-warn-percent", type=float, default=85.0)
    parser.add_argument("--max-logs-tail-lines", type=int, default=160)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-file", type=str, default="")
    parser.add_argument(
        "--compose-file",
        dest="compose_files",
        action="append",
        default=[],
        help="Repeat for multiple compose files, e.g. --compose-file docker-compose.yml",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.sleep_min_seconds <= 0 or args.sleep_max_seconds <= 0:
        print("sleep values must be > 0", file=sys.stderr)
        return 2
    if args.sleep_min_seconds > args.sleep_max_seconds:
        print("sleep-min-seconds cannot be greater than sleep-max-seconds", file=sys.stderr)
        return 2
    if args.duration_seconds <= 0:
        print("duration-seconds must be > 0", file=sys.stderr)
        return 2

    log_file = Path(args.log_file) if args.log_file else None
    config = AgentConfig(
        duration_seconds=args.duration_seconds,
        sleep_min_seconds=args.sleep_min_seconds,
        sleep_max_seconds=args.sleep_max_seconds,
        coverage_url=args.coverage_url,
        sources_url=args.sources_url,
        analytics_url=args.analytics_url,
        restart_backoff_seconds=args.restart_backoff_seconds,
        max_restarts_per_target=args.max_restarts_per_target,
        max_logs_tail_lines=args.max_logs_tail_lines,
        cpu_warn_percent=args.cpu_warn_percent,
        mem_warn_percent=args.mem_warn_percent,
        dry_run=args.dry_run,
        log_file=log_file,
        compose_files=args.compose_files,
    )
    return CoverageSelfHealAgent(config).run()


if __name__ == "__main__":
    raise SystemExit(main())
