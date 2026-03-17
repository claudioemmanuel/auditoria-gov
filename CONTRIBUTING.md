# Contributing to AuditorIA Gov

Thanks for contributing to AuditorIA Gov.
This project is a civic-tech platform for reproducible anti-corruption risk analysis of Brazilian federal public data.

## Development Setup

### Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+
- Docker + Docker Compose

### Local setup

```bash
git clone https://github.com/claudioemmanuel/auditoria-gov.git
cd auditoria-gov
cp .env.example .env
```

Update `.env` with at least:

- `PORTAL_TRANSPARENCIA_TOKEN` for Portal da Transparencia jobs
- `CPF_HASH_SALT` for non-dev environments

Install dependencies:

```bash
uv sync --extra test
cd web && npm ci && cd ..
```

Start local stack:

```bash
docker compose up --build
```

Run migrations:

```bash
docker compose run --rm api alembic -c api/alembic.ini upgrade head
```

### Production deployment (AWS)

See `docs/DEPLOYMENT.md` for the full AWS setup guide (ECS Fargate + RDS + S3/CloudFront).
The Terraform configuration lives in `infra/aws/`. Never commit `terraform.tfvars` — it is gitignored.

## Project Layout

- `api/`: FastAPI app and Alembic migrations
- `worker/`: Celery workers and scheduled tasks
- `shared/`: Core domain logic (connectors, ER, typologies, analytics)
- `web/`: Next.js public interface
- `tests/`: backend/unit/integration-style test suite

## Adding a New Connector

1. Create a connector in `shared/connectors/<name>.py` implementing `BaseConnector`.
2. Define `list_jobs()`, `fetch()`, and `normalize()` with deterministic behavior.
3. Register it in `shared/connectors/__init__.py` (`ConnectorRegistry`).
4. Add or update ingestion orchestration if needed (`worker/tasks/ingest_tasks.py`, scheduler config).
5. Add tests in `tests/connectors/` and task-level tests in `tests/worker/` when relevant.
6. Document source/access requirements in `README.md`.

## Adding a New Typology

1. Create `shared/typologies/tXX_<name>.py` inheriting from `BaseTypology`.
2. Ensure factors and severity are deterministic and evidence-backed.
3. Register typology in `shared/typologies/registry.py`.
4. Add factor metadata in `shared/typologies/factor_metadata.py` when needed.
5. Add tests in `tests/typologies/` including registry and minimum-detectable coverage.
6. Update the typology table in `README.md`.

## Testing and Quality Requirements

Backend tests:

```bash
uv run --extra test pytest -q
```

Frontend checks:

```bash
cd web
npm run lint
npm run build
```

Coverage policy is strict: backend coverage target is `100%` (`pyproject.toml`, `fail_under = 100`).

## Pull Request Guidelines

- Open PRs against `main`.
- Keep PRs focused and logically scoped.
- Include problem statement, approach, and verification evidence.
- Reference related issue(s).
- Update docs when behavior, schema, connectors, or typologies change.

### PR Checklist

- [ ] Tests added/updated for changed behavior
- [ ] `uv run --extra test pytest -q` passes locally
- [ ] Frontend checks pass if UI was touched
- [ ] No secrets, tokens, or personal data were committed
- [ ] README/CONTRIBUTING/docs updated as needed

## Reporting Issues

- Use GitHub issue templates for bugs and feature requests.
- For security issues, do **not** open a public issue. Follow `SECURITY.md`.

## Code of Conduct

This project follows the Contributor Covenant v2.1. See `CODE_OF_CONDUCT.md`.
