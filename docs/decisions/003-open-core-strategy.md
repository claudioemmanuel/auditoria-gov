# ADR 003 — Open-Core Architecture Strategy

**Status:** Accepted  
**Date:** 2026-04-02  
**Deciders:** @claudioemmanuel

---

## Context

OpenWatch is a deterministic citizen-auditing platform that processes Brazilian federal public data
and applies corruption-risk typologies to generate evidence-based risk signals. The platform contains
two fundamentally different kinds of intellectual property:

1. **Public-benefit infrastructure** — the frontend, SDK, documentation, and generic utilities that
   enable community engagement, transparency, and adoption.

2. **Competitive IP** — the 28 typology algorithms (T01–T28), entity resolution logic, risk-scoring
   engine, AI/LLM integration, and data pipeline orchestration that represent years of domain
   expertise and constitute the platform's strategic defensibility.

Currently all code lives in a single monorepo with no formal access-control boundaries between these
two layers. This creates risk:

- Typology logic is visible to anyone who reads the repository.
- Competitors can replicate the detection methodology by studying the code.
- The proprietary advantage that sustains the platform's long-term viability is exposed.

## Decision

Adopt an **open-core** model that maximises transparency for community growth while protecting the
competitive IP that sustains the platform.

### Two-Layer Model

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC LAYER  (open source — MIT / Apache 2.0)             │
│  web/ · packages/sdk · packages/ui · packages/utils         │
│  packages/config · packages/db · packages/models            │
│  api/routers/public.py · docs/ · infra/ · .github/          │
└──────────────────────┬──────────────────────────────────────┘
                       │  API calls only (HTTP)
                       │  No direct imports
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PROTECTED CORE  (BSL 1.1 — private repository)             │
│  core/typologies/ (T01–T28)                                 │
│  core/er/ · core/ai/ · core/analytics/ · core/baselines/   │
│  core/services/ · core/queries/ · core/scheduler/           │
│  core/pipelines/ · shared/ · worker/ · packages/connectors/ │
│  api/routers/internal.py · api/alembic/                     │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Direction

The single inviolable rule:

> **Public modules MUST NOT import Core modules directly.**
> Core modules MAY depend on public packages (models, config, utils).

This is enforced by `import-linter` contracts (see `.import-linter`).

### Monorepo vs Split Repositories

In the short term, both layers coexist in this private monorepo. The `core/` directory is the
canonical home for protected packages. The `packages/` directory holds public packages.

When the public layer is ready for community release:
1. Run `git filter-repo` to extract public paths into `openwatch-public` (public GitHub repo).
2. The remaining private monorepo becomes `openwatch-core`.
3. `openwatch-core` installs public packages as dependencies from PyPI / npm.

### Licensing

| Layer | License | Scope |
|-------|---------|-------|
| `web/`, `packages/sdk`, `packages/ui`, `packages/utils`, `packages/config`, `packages/db`, `packages/models` | MIT | Full open-source freedom |
| `api/` (public endpoints only) | Apache 2.0 | Open-source with patent grant |
| `docs/` | CC-BY 4.0 | Attribution required |
| `core/*`, `shared/*`, `worker/*`, `packages/connectors/*` | BSL 1.1 | Source-available; production use requires commercial licence; converts to Apache 2.0 after Change Date |

BSL 1.1 terms for core:
- **Licensor:** OpenWatch contributors
- **Change Date:** Four years after each file's creation date
- **Change License:** Apache License, Version 2.0
- **Additional Use Grant:** You may use the Licensed Work to study the algorithms
  for personal research or academic purposes. You may NOT run the Licensed Work
  as a service competing with OpenWatch.

## Consequences

### Positive

- Community can contribute to frontend, SDK, utilities, and documentation.
- Platform remains defensible — competitors cannot simply fork the typology logic.
- BSL allows source visibility for transparency/audit requests without enabling competition.
- Clear contribution boundaries reduce ambiguity for external contributors.
- License converts to Apache 2.0 after 4 years, ensuring long-term open availability.

### Negative

- External contributors cannot improve the typology algorithms directly (by design).
- BSL requires tracking change dates per file (mitigated by using the initial commit date of
  the repository as a uniform change date).
- Some contributors may prefer a fully open model — this must be documented clearly.

### Neutral

- The monorepo structure is unchanged; only licensing and import boundaries are formalised.
- All tests continue to run against both layers internally.

## Alternatives Considered

| Option | Rejected Reason |
|--------|-----------------|
| Fully open-source (AGPL for all) | Typology logic would be freely replicable |
| Fully proprietary (no public repo) | Loses community trust and adoption |
| Dual-licensing (GPL + commercial) | Complex for contributors; BSL is simpler |
| Obfuscation only | Fragile; not a real access-control mechanism |

## References

- [Business Source License 1.1](https://mariadb.com/bsl11/)
- [Open-Core Model — Wikipedia](https://en.wikipedia.org/wiki/Open-core_model)
- [ADR 001 — Monorepo Split](./001-monorepo-split.md)
- [ADR 002 — Queries-Only Core Surface](./002-queries-only-core-surface.md)
