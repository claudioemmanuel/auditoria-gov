# Skill: Safe Refactor — AuditorIA Gov

## Purpose

Step-by-step workflow for refactoring code without changing behavior, preserving test coverage and guardrails.

## Workflow

### 1. Baseline

```bash
uv run --extra test pytest -q --tb=short
```

All tests must pass before touching anything. If they don't, fix tests first.

### 2. Scope the Change

- Identify which modules are affected: `shared/`, `api/`, `worker/`, `web/`.
- For `shared/` changes: 100% coverage must be maintained throughout.
- List files to be modified before starting.

### 3. Make Changes Incrementally

- One logical change per commit.
- No behavior changes — only structure, naming, or organization.
- If moving code across files, move first, then rename in a separate commit.

### 4. Verify After Each Commit

```bash
uv run --extra test pytest -q --cov=shared --cov-fail-under=100
```

### 5. Frontend (if applicable)

```bash
cd web && npm run lint && npm run build
```

### 6. Checklist Before PR

- [ ] All tests pass with 100% `shared/` coverage.
- [ ] No `import` paths broken.
- [ ] No behavior changes (same inputs → same outputs).
- [ ] `CLAUDE.md` / `docs/ARCHITECTURE.md` updated if public interfaces changed.
- [ ] PR description explains *why* the refactor was done.

## Rules

- Never combine refactor + feature in the same PR.
- Never skip tests to "fix them later".
- If coverage drops below 100%, the refactor is incomplete.
