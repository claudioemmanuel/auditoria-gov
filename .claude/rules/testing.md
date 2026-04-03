# Testing Rules — OpenWatch

## Coverage Requirement

- 100% line and branch coverage is required for all modules under `shared/`.
- Enforced by `pyproject.toml` (`--cov=shared --cov-fail-under=100`).
- Run: `uv run --extra test pytest -q`

## Async Tests

- All async test functions must be decorated with `@pytest.mark.asyncio`.
- Use `asyncpg` test fixtures from `tests/conftest.py`; do not open new DB connections in individual tests.

## HTTP Mocking

- Use `respx` for mocking outbound HTTP — no real network calls in tests.
- Fixtures for connector mocks live in `tests/connectors/`.

## Typology Tests

Every typology test file must cover three cases:
1. **Zero-result** — inputs that produce no signals.
2. **Positive** — inputs that produce at least one signal.
3. **Edge/boundary** — values at the detection threshold (e.g., exactly at the split limit).

## Frontend Tests

```bash
cd web
npm run lint      # ESLint
npm run build     # TypeScript + Next.js compilation check
```

No browser tests yet; lint + build is the acceptance bar.

## Test File Layout

- Mirror `shared/` structure: `tests/connectors/`, `tests/typologies/`, `tests/repo/`, etc.
- Each new module in `shared/` requires a corresponding test file in `tests/`.

## Running Tests

```bash
# Full backend suite
uv run --extra test pytest -q

# Single module
uv run --extra test pytest tests/typologies/test_t03.py -v

# With coverage report
uv run --extra test pytest --cov=shared --cov-report=term-missing
```
