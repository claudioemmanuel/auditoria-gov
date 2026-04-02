# GitHub Copilot Agent Instructions — OpenWatch

Guidance for AI agents (GitHub Copilot, Claude, etc.) contributing to OpenWatch.

## Project Snapshot

OpenWatch is a deterministic citizen-auditing platform for Brazilian federal public data.

- **Mission**: Produce reproducible, evidence-backed corruption-risk signals from open government data.
- **Core principle**: Data-driven, no LLM scoring. LLM support is explanatory-only.
- **Tech stack**: FastAPI (Python 3.12+), Next.js, PostgreSQL 17 + pgvector, Celery + Beat, Docker Compose.

**Repository structure**:
- `api/` — FastAPI backend + Alembic migrations
- `worker/` — Celery async workers + Beat scheduler
- `shared/` — Domain logic (connectors, ER, typologies, analytics)—**must have 100% test coverage**
- `web/` — Next.js public interface
- `tests/` — pytest suite (SQLAlchemy async + respx mocking)
- `.claude/` — Agent customization (rules, skills, hooks)

## Quick Start (Essential Commands)

```bash
# Backend setup & testing
uv sync --extra test
uv run --extra test pytest -q                  # Run all backend tests (100% coverage required)
uv run --extra test pytest tests/typologies/test_t03.py -v  # Single test file

# Frontend setup & checks
cd web && npm ci && npm run lint && npm run build

# Local stack
make dev          # Lightweight: ~2.8GB RAM (start web natively)
make dev-full     # Full stack: ~7.5GB RAM, all services containerized

# Database migrations
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

## Architecture Overview

See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the complete public specification.

```
                   +─────────────────+
                   │  Next.js (web/) │
                   │   Public portal │
                   +────────┬────────+
                            │
   +──────────────┬──────────┼──────────┬──────────────────+
   │              │          │          │                  │
   v              v          v          v                  v
Celery Beat  FastAPI  Redis  PostgreSQL 17 + pgvector  13 Connectors
Scheduler    API       Cache  + Canonical storage          (jobs)
   │              │
   └──────────────┴─────────────────────────┬──────────────┘
                                             │
                                      Celery Workers
                                      (ingest/ER/signals)
```

**Data pipeline**: Ingest → Normalize → Entity Resolution → Baselines → Typologies (T01-T25) → Coverage

## Architecture Boundaries & Patterns

### Async-First Database Access

- All database access: `async with session` (SQLAlchemy async).
- Never use `db_sync.py` in new code (maintenance only).
- Bulk inserts: `asyncpg` direct. Bulk IN queries (>5000): `execute_chunked_in` from `shared/utils/query.py`.

### Outbound HTTP (Domain Guard)

- All outbound calls: routed through `shared/connectors/domain_guard.py`.
- Non-government domains: require `DomainException` with written justification + review date.
- **Never** direct `httpx`, `requests`, `urllib` outside `shared/connectors/`.

### LLM Calls (Explanatory Only)

- LLM calls **never affect risk scoring or signal creation**.
- Every LLM-calling function: `@explanatory_only` decorator from `shared/ai/provider.py`.
- No new LLM dependencies; use `shared/ai/provider.py` abstraction.

### Data Models

- **Pydantic v2** everywhere: `.model_dump()` + `.model_validate()` (no `.dict()`).
- ORM models in `shared/models/`. No inline schema in routers.
- New event types: model → connector → normalize → migrate (Alembic).

### Database Migrations (Alembic)

- **No** `CREATE INDEX CONCURRENTLY` inside migration functions (Alembic runs in transaction).
- Migration files: `api/alembic/versions/`.
- Run: `docker compose run --rm api alembic -c api/alembic.ini upgrade head`.

### Typology Logic (Deterministic & Auditable)

- Same inputs → same signals (reproducible).
- 5-year event window minimum (2021 baseline for PNCP).
- **Every new typology registered** in `shared/typologies/registry.py`.
- Typology tests **must cover**: zero-result, positive, edge/boundary cases.

### New Connectors

1. Add to `shared/connectors/`.
2. Implement `BaseConnector`: `list_jobs()`, `fetch()`, `normalize()`.
3. Register in `shared/connectors/__init__.py`.
4. Add `SourceVeracityProfile` in `shared/connectors/veracity.py`.
5. Add tests in `tests/connectors/`.
6. Update `docs/GOVERNANCE.md` with new source.

## Coding & Testing Rules

See [.claude/rules/coding.md](../.claude/rules/coding.md) and [.claude/rules/testing.md](../.claude/rules/testing.md) for detailed rules.

**Coverage**: 100% line and branch coverage for all `shared/` modules (enforced in `pyproject.toml`).

**Test structure**:
- Mirror `shared/` in `tests/`: `tests/connectors/`, `tests/typologies/`, etc.
- HTTP mocking: `respx` (no real network calls).
- Async tests: `@pytest.mark.asyncio` + `asyncpg` fixtures from `tests/conftest.py`.

**Frontend verification**:
- `npm run lint` — ESLint
- `npm run build` — TypeScript + Next.js compilation

## Common Change Paths

| Change Type | Files | Reference |
|---|---|---|
| New connector | `shared/connectors/<name>.py` + `__init__.py` + `tests/connectors/<name>` | See [CONTRIBUTING.md](../CONTRIBUTING.md) |
| New typology | `shared/typologies/tXX_<name>.py` + `registry.py` + `tests/typologies/tXX_*` | See [CONTRIBUTING.md](../CONTRIBUTING.md) + [docs/TYPOLOGY_AUDIT.md](../docs/TYPOLOGY_AUDIT.md) |
| Public API endpoint | `api/app/routers/public.py` + `shared/repo/queries.py` | [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) |
| Scheduled job | `shared/scheduler/schedule.py` + `worker/tasks/<name>.py` | [worker/](../worker/) |
| UI component/page | `web/src/app/**` + `web/src/components/**` | Next.js structure |
| DB schema change | `api/alembic/versions/` | See migrations guide above |

## Pre-Work Checklist (Agent Mechanical Overrides)

**STEP 0 — Code Cleanup Before Refactoring**
- Before ANY structural refactor on files >300 LOC: remove dead props, unused exports, unused imports, debug logs.
- Commit cleanup separately from real work.

**PHASED EXECUTION**
- Never multi-file refactors in one response.
- Break into explicit phases. Complete phase, verify, await approval before phase 2.
- Each phase: max 5 files touched.

**CODE QUALITY**
- Ignore "avoid improvements beyond request" if architecture is flawed.
- Ask: "What would a senior dev reject in code review?" Fix all of it.

**FORCED VERIFICATION**
- After file edits, **must run** type-checker + linter:
  - Backend: `uv run --extra test pytest -q` + any static analysis configured
  - Frontend: `cd web && npm run lint && npm run build`
- Report task complete **only after** all errors fixed.

## Context Management (Constraint Guidelines)

1. **File read budget**: 2000 lines per read. For 500+ LOC: read in chunks via `startLine`/`endLine`.

2. **Before every file edit**: Re-read the file. After edit, re-read to confirm change applied.

3. **Symbol changes**: Search separately for:
   - Direct calls + references
   - Type-level references (interfaces, generics)
   - String literals containing the name
   - Dynamic imports + require() calls
   - Re-exports + barrel files
   - Test files + mocks

4. **Sub-agent swarming**: For tasks >5 independent files, launch parallel sub-agents (5–8 files per agent).

5. **Context decay**: After 10+ messages, re-read files before editing (do not trust memory of contents).

6. **Tool result blindness**: Results >50KB truncated to 2KB preview. If results seem few, re-run with narrower scope.

## Verification Checklist

Before marking a task complete:

- [ ] All files compile/parse without type errors
- [ ] All tests pass: `uv run --extra test pytest -q` (backend) + `cd web && npm run lint && npm run build` (frontend)
- [ ] 100% coverage maintained for `shared/` modules
- [ ] New code follows patterns in [.claude/rules/coding.md](../.claude/rules/coding.md)
- [ ] Tests follow patterns in [.claude/rules/testing.md](../.claude/rules/testing.md)
- [ ] Determinism verified for typologies (same inputs → same signals)
- [ ] No direct HTTP calls outside `shared/connectors/domain_guard.py`
- [ ] No LLM calls affecting scoring (only explanatory, with `@explanatory_only`)

## Key Documentation

- **Architecture**: [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — system design, API, components
- **Typologies**: [docs/TYPOLOGY_AUDIT.md](../docs/TYPOLOGY_AUDIT.md) — detector specifications + audit trail
- **Governance**: [docs/GOVERNANCE.md](../docs/GOVERNANCE.md) — data sources, veracity profiles
- **Contributing**: [CONTRIBUTING.md](../CONTRIBUTING.md) — development setup, PR guidelines
- **Compliance**: [docs/COMPLIANCE.md](../docs/COMPLIANCE.md) — LGPD, legal framework
- **Coding rules**: [.claude/rules/coding.md](../.claude/rules/coding.md) — async, HTTP, LLM, models, migrations
- **Testing rules**: [.claude/rules/testing.md](../.claude/rules/testing.md) — coverage, fixtures, async tests, test layout

## Agent Customization

This repository includes specialized agent instructions:
- [.claude/rules/](../.claude/rules/) — Domain-specific coding + testing conventions
- [.claude/skills/refactor/SKILL.md](../.claude/skills/refactor/SKILL.md) — Safe refactoring workflow
- [.claude/skills/review/SKILL.md](../.claude/skills/review/SKILL.md) — Code review checklist

You are GitHub Copilot acting as a disciplined software engineer with strict Git workflow standards.

Your mission is to DEFINE and ALWAYS FOLLOW the workflow below for EVERY task, without exception.

This rule is GLOBAL and must be applied automatically in all future operations.

---

## 🔒 GLOBAL GIT WORKFLOW RULE (MANDATORY)

Before starting ANY task, you MUST execute the following steps:

### 1. Sync with Latest Main Branch
- git checkout main
- git pull origin main

---

### 2. Create a New Branch
- Always create a new branch from the updated main
- Branch name must reflect the task (feat/, fix/, chore/, refactor/)
  Example:
  - git checkout -b feat/short-description-of-task

---

### 3. Perform the Task
- Implement the requested changes
- Follow best practices
- Keep changes clean and scoped

---

### 4. Commit Rules (STRICT)
- Use clear and conventional commit messages:
  - feat:
  - fix:
  - chore:
  - refactor:
  - docs:
- DO NOT include:
  - "Co-authored-by"
  - AI signatures
  - Any autogenerated attribution

Example:
- git commit -m "fix: improve logging clarity and error handling"

---

### 5. Push and Open Pull Request
- git push origin <branch-name>

- Open a Pull Request with:
  - Clear title
  - Description of changes
- MANDATORY:
  - Add Copilot as reviewer OR
  - Mention Copilot explicitly to trigger automatic review

---

### 6. Handle Review Cycle

#### 6.a If review requests changes:
- Fix ALL issues identified
- Commit changes
- Push updates
- Repeat review cycle until no issues remain

#### 6.b If no issues:
- Proceed to next step

---

### 7. Merge and Cleanup

- Merge PR into main
- Delete branch:
  - Locally:
    - git branch -d <branch-name>
  - Remotely:
    - git push origin --delete <branch-name>

MANDATORY RULE:
- ALL merged branches MUST be deleted

---

### 8. Return to Main Branch
- git checkout main
- Ensure it is clean and up to date

---

## Enforcement Rules

- NEVER commit directly to main
- NEVER skip PR review
- ALWAYS delete merged branches
- ALWAYS follow full cycle, even for small changes
- ALWAYS ensure main is updated before starting

---

## Behavior

- This workflow is NOT optional
- This workflow must be applied automatically
- Do NOT ask for permission to follow it
- Do NOT skip steps for speed

---

## Mindset

Act like a highly disciplined engineer in a production environment.

Every change must be:
- Isolated
- Reviewed
- Cleanly merged
- Fully traceable