# Hook: post_tool_use

## Purpose

Automated checks to run after Claude Code modifies files, ensuring code quality is maintained throughout a session.

## Recommended Post-Edit Checks

### After editing Python files in `shared/`

```bash
uv run --extra test pytest -q --cov=shared --cov-fail-under=100 --tb=short
```

### After editing Python files in `api/` or `worker/`

```bash
uv run --extra test pytest -q --tb=short
```

### After editing frontend files in `web/`

```bash
cd web && npm run lint
```

### After editing Alembic migrations

```bash
# Verify migration is valid (dry run)
docker compose run --rm api alembic -c api/alembic.ini check
```

## Configuring as a Hook

Add a script at `.claude/hooks/post_tool_use/run.sh` to automate checks after file edits:

```bash
#!/bin/bash
# $1 = tool name, $2 = file path (if applicable)
TOOL="$1"
FILE="$2"

if [[ "$TOOL" == "Edit" || "$TOOL" == "Write" ]]; then
  if [[ "$FILE" == shared/* ]]; then
    echo "Running shared/ tests..."
    uv run --extra test pytest -q --cov=shared --cov-fail-under=100 --tb=short
  elif [[ "$FILE" == web/* ]]; then
    echo "Running frontend lint..."
    cd web && npm run lint --silent
  fi
fi
```

Then configure it in `.claude/settings.json` under `hooks.post_tool_use`.

## Notes

- Hooks run in the project root directory.
- Hook failures should be treated as blockers — don't continue if coverage drops.
- Keep hook scripts fast; if a full test suite takes >30s, scope it to the changed module only.
