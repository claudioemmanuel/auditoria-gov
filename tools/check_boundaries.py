#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
Boundary enforcement tool for the OpenWatch open-core split.

This script validates that files designated as PUBLIC do not import
from modules designated as PROTECTED CORE. Run this before publishing
the public repo, and in CI to prevent regressions.

Usage:
    python tools/check_boundaries.py [--strict]

Exit codes:
    0 — No violations found
    1 — Violations found (or --strict and warnings exist)
"""

import ast
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Classification: modules that must NEVER be imported from the public layer
# ---------------------------------------------------------------------------
PROTECTED_MODULES: list[str] = [
    "shared.typologies",
    "shared.analytics",
    "shared.er",
    "shared.ai",
    "shared.baselines",
    "shared.services",
    "shared.repo",
    "shared.scheduler",
    "shared.models.orm",   # DB schema — PROTECTED
    "shared.models.raw",   # Internal raw source models — PROTECTED
    # NOTE: shared.models.graph, .radar, .coverage_v2 are PUBLIC API schemas — not protected
    "worker.tasks",
    "worker.worker_app",
    # NOTE: api.app.routers.internal was protected when it only existed in the
    # private monorepo. It now lives in the public repo as a gateway proxy —
    # importing it from main.py is intentional and valid.
]

# Protected connector modules (enrichment strategy, not generic wrappers)
PROTECTED_CONNECTORS: list[str] = [
    "shared.connectors.veracity",
    "shared.connectors.bacen",
    "shared.connectors.datajud",
    "shared.connectors.tce_pe",
    "shared.connectors.tce_rj",
    "shared.connectors.tce_rs",
    "shared.connectors.tce_sp",
    "shared.connectors.tcu",
    "shared.connectors.tse",
    "shared.connectors.camara",
    "shared.connectors.senado",
    "shared.connectors.bndes",
    "shared.connectors.jurisprudencia",
    "shared.connectors.querido_diario",
    "shared.connectors.transferegov",
    "shared.connectors.anvisa_bps",
    "shared.connectors.receita_cnpj",
    "shared.connectors.orcamento_bim",
]

ALL_PROTECTED = PROTECTED_MODULES + PROTECTED_CONNECTORS

# ---------------------------------------------------------------------------
# Files/directories that represent the PUBLIC layer
# (post-split, these will be the only files in the public repo)
# ---------------------------------------------------------------------------
PUBLIC_PATHS: list[str] = [
    "apps/web/src",
    "packages/sdk",
    "packages/ui",
    "packages/utils",
    "packages/config",
    "packages/models/openwatch_models",
    "packages/connectors/openwatch_connectors/domain_guard.py",
    "packages/connectors/openwatch_connectors/http_client.py",
    # Public API surface
    "api/app/routers/public.py",
    "api/app/main.py",
    "api/app/deps.py",
    "api/core_client.py",
    "api/app/adapters",
    # Generic connectors kept in the public layer
    "shared/connectors/http_client.py",
    "shared/connectors/domain_guard.py",
    # Public models — response schemas (API contract)
    "shared/models/canonical.py",
    "shared/models/signals.py",
    "shared/models/vocabulary.py",
    "shared/models/base.py",
    "shared/models/graph.py",
    "shared/models/radar.py",
    "shared/models/coverage_v2.py",
    "shared/models/public_filter.py",
    "shared/logging.py",
    "shared/config.py",
]


# ---------------------------------------------------------------------------
# Files that are AUTHORIZED to import from both layers.
# The adapter is the intentional bridge — its monorepo-mode imports are expected.
# After the split, the monorepo fallback branch is deleted and this exemption
# is removed along with api/app/adapters/ entry in PUBLIC_PATHS.
# ---------------------------------------------------------------------------
ADAPTER_EXEMPT_PATHS: list[str] = []


# ---------------------------------------------------------------------------
# Post-split state: data-ingestion connectors live exclusively in
# `openwatch-core`. The public repo keeps only generic transport helpers.
# ---------------------------------------------------------------------------
CONNECTOR_SPLIT_TODO_PATHS: list[str] = []


def collect_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in paths:
        p = ROOT / rel
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
    return files


def _is_adapter_exempt(file: Path) -> bool:
    rel = str(file.relative_to(ROOT)).replace("\\", "/")
    return any(rel.startswith(exempt) for exempt in ADAPTER_EXEMPT_PATHS)


def _is_connector_split_todo(file: Path) -> bool:
    rel = str(file.relative_to(ROOT)).replace("\\", "/")
    return any(rel == p for p in CONNECTOR_SPLIT_TODO_PATHS)


def extract_imports(file: Path) -> list[tuple[int, str]]:
    """Return (line_no, module_name) for all imports in a Python file."""
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except SyntaxError:
        return []

    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))
    return imports


def check_violations(strict: bool = False) -> int:
    files = collect_python_files(PUBLIC_PATHS)
    violations: list[str] = []
    warnings: list[str] = []

    for file in files:
        rel_path = file.relative_to(ROOT)
        if _is_adapter_exempt(file):
            # core_adapter.py is the authorized bridge — exempt from boundary checks.
            # POST-SPLIT: remove this exemption when the monorepo fallback is deleted.
            continue
        is_connector_todo = _is_connector_split_todo(file)
        for line_no, module in extract_imports(file):
            for protected in ALL_PROTECTED:
                if module == protected or module.startswith(protected + "."):
                    msg = f"  {rel_path}:{line_no}  imports  {module!r}"
                    if is_connector_todo and (protected == "shared.models.raw" or protected == "shared.models.orm"):
                        # Connectors import raw/orm models — tracked as SPLIT-TODO warning
                        warnings.append(f"{msg}  [SPLIT-TODO: connector moves to core]")
                    elif protected in PROTECTED_MODULES:
                        violations.append(msg)
                    else:
                        # Protected connectors are warnings (enrichment strategy)
                        warnings.append(msg)

    if violations:
        print(f"\n🔴 BOUNDARY VIOLATIONS ({len(violations)}) — public files importing PROTECTED modules:\n")
        for v in violations:
            print(v)

    if warnings:
        print(f"\n🟡 BOUNDARY WARNINGS ({len(warnings)}) — public files importing PROTECTED connectors:\n")
        for w in warnings:
            print(w)

    if not violations and not warnings:
        print("✅ No boundary violations found. Public layer is clean.")
        return 0

    if violations:
        print(
            "\n❌ Fix violations before publishing the public repo."
            "\n   Replace direct imports with calls to core_client.py (API gateway pattern)."
        )
        return 1

    if warnings and strict:
        print("\n❌ Warnings treated as errors in --strict mode.")
        return 1

    if warnings:
        print("\n⚠️  Warnings found. These connectors should not be imported in the public layer post-split.")
        return 0

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenWatch boundary enforcement check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat connector warnings as errors",
    )
    parser.add_argument(
        "--list-protected",
        action="store_true",
        help="Print the full list of protected modules and exit",
    )
    args = parser.parse_args()

    if args.list_protected:
        print("Protected modules (NEVER import from public layer):\n")
        for m in ALL_PROTECTED:
            print(f"  {m}")
        sys.exit(0)

    print("OpenWatch Boundary Checker")
    print("=" * 50)
    print(f"Checking {len(collect_python_files(PUBLIC_PATHS))} public Python files...")
    sys.exit(check_violations(strict=args.strict))


if __name__ == "__main__":
    main()
