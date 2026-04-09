# OpenWatch — Frontend

Public-facing frontend repository. Backend/API/pipeline concerns live in `openwatch-core`.

## Autonomous Operation

Operate fully autonomously. Do not ask for permission before:
- Reading, editing, or creating files anywhere in this repo
- Running build, lint, typecheck, or test commands
- Installing or upgrading packages via pnpm
- Running Docker compose commands (up, down, restart, logs, exec)
- Executing scripts in `scripts/`
- Running `git` commands on the current working branch

## Stack

- **Monorepo**: pnpm + Turborepo (`apps/web`)
- **Frontend**: Vite + React + TypeScript (strict)
- **Package manager**: pnpm ≥ 9

## Key Commands

```bash
pnpm install                         # install deps
pnpm dev                             # start dev server
pnpm build                           # build all packages
pnpm lint                            # lint
pnpm typecheck                       # type check
npm run start                        # detect resources + docker up
docker compose --env-file .env.runtime up -d
docker compose down
```

## TypeScript Rules

- `exactOptionalPropertyTypes` is enabled — use conditional spreads, not `prop: value | undefined`
- `noImplicitOverride` — add `override` to EventEmitter method overrides
- `noUncheckedIndexedAccess` — `arr[i]` returns `T | undefined`, guard it

## Trust Boundaries

Trusted domains and systems:
- This git repository (all paths)
- `localhost` / Docker network services
- npm/pnpm registries (declared packages only)

## Do Not

- Force-push to `main`
- Deploy to production without explicit instruction
- Commit `.env` or secrets files
