# ADR-001: Monorepo Split — Public packages/ vs Private core/

## Status
Accepted

## Context
OpenWatch is a deterministic citizen-auditing platform that ingests and analyzes Brazilian federal public data using proprietary typology detectors, entity resolution, and risk scoring engines.

The original flat `shared/` structure mixed public infrastructure code (utils, models, connectors) with private IP (typologies T01–T28, ER algorithms, risk scoring, legal inference). This created:
- Risk of accidental open-sourcing of core competitive advantages
- No tooling enforcement of import boundaries
- Unclear ownership model for OSS contributors

## Decision
Restructure into a hard-boundary monorepo:

```
packages/   → public OSS libraries (config, utils, models, db, connectors)
core/       → private IP (typologies, er, analytics, baselines, services, ai, queries, pipelines)
apps/       → deployable services (api, web)
```

**Enforcement:**
- `.import-linter` contracts enforced in CI: `packages/*` and `apps/api` cannot import `core/*` directly
- The only allowed path from `apps/api` into core is through `core/queries/openwatch_queries` (pre-computed derived reads)
- `CODEOWNERS` requires owner approval for any change under `core/`
- The `ci.yml` core test job is secret-gated — absent in OSS forks → silently skipped

## Consequences

### Positive
- Zero-ambiguity IP boundary — every file is unambiguously PUBLIC or CORE
- CI enforces boundaries; PRs that violate them fail before merge
- OSS contributors can fork and contribute to `packages/` without seeing core IP
- `core/` can move to a private submodule in the future without changing the API

### Negative
- Higher complexity — more pyproject.toml files to maintain
- Cross-package imports require proper uv workspace configuration
- Migration from flat `shared/` structure required careful import rewriting

## Alternatives Considered
- **Keep flat shared/ with gitignore rules**: Rejected — no enforcement at PR time; risk of accidental exposure
- **Private submodule for core/**: Deferred — adds Git complexity; current approach supports both open and private in one repo
