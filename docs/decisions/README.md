# Architecture Decision Records (ADRs)

This directory tracks significant architectural decisions made in OpenWatch.

## Format

Each ADR is a Markdown file named `NNN-short-title.md` with the following structure:

```markdown
# ADR-NNN: Title

**Status:** Accepted | Superseded | Deprecated
**Date:** YYYY-MM-DD

## Context
Why this decision was needed.

## Decision
What was decided.

## Consequences
What changed as a result (positive and negative).
```

## Decisions to Document

The following key decisions are already in effect and should be formalized as ADRs:

| # | Decision | Status |
|---|----------|--------|
| 001 | Async-first architecture (FastAPI + asyncpg) | Accepted |
| 002 | Deterministic-only risk signals (LLM explanatory only) | Accepted |
| 003 | MIT license for public OSS layer | Accepted |
| 004 | domain_guard.py whitelist for all outbound HTTP | Accepted |
| 005 | 100% test coverage requirement for shared/ | Accepted |
| 006 | 5-year event windows for typology detection | Accepted |
| 007 | execute_chunked_in for large asyncpg IN queries | Accepted |

## Creating a New ADR

1. Copy the template above into a new file: `docs/decisions/NNN-title.md`
2. Fill in Context, Decision, and Consequences.
3. Add a row to the table above.
4. Reference the ADR in the relevant code (e.g., inline comment: `# See ADR-004`).
