# Contributing to OpenWatch

Thank you for your interest in contributing! OpenWatch is a citizen-auditing platform for
Brazilian federal data. This guide covers how to contribute to the **public OSS layer** of
the project.

## Contribution Scope

Community contributions are welcome in the following areas:

| Area | Examples |
|------|---------|
| **Web portal** (`apps/web/`) | UI/UX improvements, new views, accessibility fixes |
| **TypeScript SDK** (`packages/sdk/`) | New API wrappers, type improvements |
| **UI components** (`packages/ui/`) | Reusable component improvements |
| **Public connectors** (`packages/connectors/` — 6 public) | Bug fixes, rate-limit improvements |
| **Utilities** (`packages/utils/`, `packages/config/`) | Generic helper functions |
| **Documentation** | Translations, corrections, new guides |
| **Bug reports** | Any reproducible bug with clear steps |

> **Not in scope for external PRs:** Typology algorithms, risk scoring logic, entity resolution,
> enrichment connectors (20+), and the data pipeline. These live in `openwatch-core` and are
> maintained internally. See [`docs/OPEN_CORE_STRATEGY.md`](./docs/OPEN_CORE_STRATEGY.md).

---

## Getting Started

1. **Fork** the repository and clone your fork.
2. Install dependencies:
   ```bash
   uv sync --all-extras
   cd apps/web && npm ci
   ```
3. Create a branch following the naming convention:
   ```
   feat/<description>
   fix/<description>
   docs/<description>
   chore/<description>
   ```
4. Make your changes.
5. Ensure all checks pass before opening a PR (see below).

---

## Branch Naming

All branches must follow: `<type>/<short-description>`

| Type | When to use |
|------|------------|
| `feat` | New functionality |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `docs` | Documentation only |
| `chore` | Maintenance, dependencies, tooling |
| `ci` | CI/CD workflow changes |
| `test` | Adding or fixing tests |

Example: `feat/sdk-entity-search`, `fix/radar-pagination`, `docs/api-quickstart`

---

## Commit Conventions

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>
```

Examples:
```
feat(sdk): add entity search method with fuzzy matching
fix(web): correct radar pagination offset
docs(contributing): add branch naming table
chore(deps): bump fastapi to 0.115.5
```

**Rules:**
- Maximum 72 characters in the subject line.
- Use imperative mood in the description ("add", not "adds" or "added").
- Do not end with a period.
- Reference issues in the body when relevant: `Closes #42`

---

## Pull Request Process

1. **Link an issue** — every PR must reference an open issue with `Closes #<number>` or `Fixes #<number>` in the description.
2. **PR title** must follow conventional commits format.
3. **CI must pass** — all required checks must be green before merge.
4. **One approval** required from `@claudioemmanuel` (or designated reviewer).
5. **No force merges** — do not squash, rebase, or merge without approval.

### PR checklist (auto-enforced by CI)

- [ ] Branch name follows `<type>/<description>` convention
- [ ] PR title follows conventional commits format
- [ ] PR body contains `Closes #<issue>` or `Fixes #<issue>`
- [ ] `uv run ruff check packages/ apps/api/` passes
- [ ] `uv run pytest tests/public -q` passes
- [ ] Open-core boundary check passes (`uv run python tools/check_boundaries.py`)
- [ ] `cd apps/web && npm run lint && npm run build` passes

---

## Code Style

### Python

- **Formatter/linter:** [Ruff](https://docs.astral.sh/ruff/) — run `uv run ruff check --fix`
- **Type hints:** Required on all public functions
- **Docstrings:** Not required but welcome for complex functions
- **Async:** Prefer `async/await` for I/O-bound code; use `AsyncSession` for DB queries

### TypeScript / React

- **Linter:** ESLint with project config — run `npm run lint`
- **Types:** No `any` unless absolutely necessary; prefer explicit types
- **Components:** Functional components with TypeScript props interfaces
- **Styling:** Tailwind CSS utility classes; no inline styles

---

## Testing

### Python tests

```bash
# Run public tests only (no DB needed for many tests)
uv run pytest tests/public -q

# With coverage
uv run pytest tests/public --cov -q
```

New public tests go in `tests/public/`. Follow the existing conftest.py patterns.

### Frontend tests

```bash
cd apps/web && npm run build  # verifies typecheck + build
```

---

## Open-Core Boundary Rules

The public layer **must not import** from protected modules. The boundary checker enforces this:

```bash
uv run python tools/check_boundaries.py
```

Protected modules (do not import in `apps/`, `packages/`, or `tests/public/`):
- `core.*` — all core packages
- `openwatch_typologies.*`, `openwatch_er.*`, `openwatch_analytics.*`, etc.
- `shared.typologies.*`, `shared.er.*`, `shared.analytics.*`, etc.

If you need data from the core layer, use the `CoreClient` adapter pattern described in
`api/app/adapters/` and `docs/OPEN_CORE_STRATEGY.md`.

---

## Reporting Bugs

Open an issue using the [bug report template](./.github/ISSUE_TEMPLATE/bug_report.yml).

Please include:
- Steps to reproduce
- Expected vs actual behavior
- OpenWatch version / commit hash
- Relevant logs or error messages

---

## Security Vulnerabilities

**Do not open public issues for security findings.**
See [SECURITY.md](./SECURITY.md) for the responsible disclosure process.

---

## Questions

Open a [GitHub Discussion](https://github.com/openwatch-br/openwatch/discussions) for
questions, ideas, or general conversation about the project.
