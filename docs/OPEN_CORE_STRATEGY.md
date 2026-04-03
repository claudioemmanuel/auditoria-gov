# Open Core Strategy

OpenWatch uses an **open-core** model to balance transparency with sustainability.

## Repository Structure

| Repo | Visibility | License | Contents |
|------|-----------|---------|----------|
| [openwatch](https://github.com/openwatch-br/openwatch) | Public | MIT | Frontend, public API gateway, public schemas, docs |
| [openwatch-core](https://github.com/openwatch-br/openwatch-core) | Private | BSL 1.1 | Analytics engine, typologies, ER, workers, infrastructure |

## Why Open Core?

OpenWatch's mission is civic accountability. Full transparency of *what* is being detected (typology definitions, data sources) is essential for public trust. However, commercial-grade implementations of the analytics engine represent significant R&D investment.

The BSL 1.1 license on `openwatch-core`:
- Allows non-commercial research, journalism, academic study, and civic auditing
- Restricts competing commercial use until the change date (4 years)
- Automatically converts to Apache 2.0 on the change date

## Public Boundary

The following ALWAYS live in the public (`openwatch`) repo:
- Public API surface (`/public/*` endpoints)
- Next.js frontend
- Public typology catalog (names, descriptions, legal citations)
- Generic connector helpers (domain guard, HTTP client base)
- Shared config and utility packages
- Documentation and contribution guides

The following ALWAYS live in the private (`openwatch-core`) repo:
- Typology scoring logic (implementations)
- Entity resolution algorithms
- AI/LLM integration
- Celery pipeline workers
- Government API connector implementations
- Database ORM models
- Private infrastructure (Terraform, Caddy)

## Boundary Enforcement

Import boundary rules in `.import-linter` and the `boundary-check.yml` CI workflow prevent the public layer from importing private-layer code directly.
