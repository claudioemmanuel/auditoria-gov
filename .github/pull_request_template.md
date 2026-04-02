## Linked Issue

Closes #<!-- REQUIRED: Issue number. No PR without a linked issue. -->

## What

<!-- One paragraph describing what this PR does. -->

## Why

<!-- Why is this change needed? Reference the issue context. -->

## How

<!-- Brief description of the implementation approach. -->

## Type of Change

- [ ] `fix` — Bug fix
- [ ] `feat` — New feature
- [ ] `refactor` — Code refactor (no behavior change)
- [ ] `docs` — Documentation only
- [ ] `chore` — Maintenance / dependencies / tooling
- [ ] `ci` — CI/CD changes

## Checklist

- [ ] Linked issue exists and is in "In Progress" on the board
- [ ] Tests pass locally (`uv run --extra test pytest -q`)
- [ ] Frontend builds (`cd web && npm run build`) — if frontend changed
- [ ] No secrets, tokens, or credentials in diff
- [ ] `tools/check_boundaries.py` passes (no protected imports in public layer)
- [ ] Documentation updated (if behavior changed)
- [ ] Migration added (if DB schema changed)
- [ ] Branch is up to date with `main`

## Test Plan

<!-- How was this tested? What should reviewers verify? -->

## Screenshots (if UI change)

<!-- Before / After -->
