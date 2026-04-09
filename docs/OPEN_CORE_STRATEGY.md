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

Three layers enforce the public/private split:

1. `tools/check_boundaries.py --strict` — AST static check against the protected-module list in the file itself.
2. `.import-linter` — contract-based import graph enforcement.
3. `tests/public/test_boundary_hygiene.py` — regression tests that pin the post-cleanup invariants.

See `PUBLIC_PRIVATE_BOUNDARY_REVIEW.md` for the 2026-04-09 cleanup audit.
