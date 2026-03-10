# Core Tooling

Scaffolding scripts and automation for AuditorIA Gov development tasks.

## Planned Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `scaffold_typology.sh` | Generate T<NN> boilerplate (detector + tests + registry entry) | Planned |
| `scaffold_connector.sh` | Generate connector boilerplate (connector + veracity profile) | Planned |
| `check_coverage.sh` | Run coverage check and report modules below 100% | Planned |
| `validate_env.sh` | Verify all required .env variables are present | Planned |
| `db_reset.sh` | Drop and recreate local DB, run migrations, seed reference data | Planned |

## Usage Pattern

Scripts in this directory should:
1. Be POSIX shell (`#!/bin/sh`) for portability.
2. Be idempotent — safe to run multiple times.
3. Exit with code 0 on success, non-zero on failure.
4. Print a summary at the end: `✓ done` or `✗ failed: reason`.

## Creating a New Script

```bash
# 1. Create the script
touch tools/core/scaffold_typology.sh
chmod +x tools/core/scaffold_typology.sh

# 2. Add shebang and description
cat > tools/core/scaffold_typology.sh << 'EOF'
#!/bin/sh
# scaffold_typology.sh — generates T<NN> typology boilerplate
# Usage: ./tools/core/scaffold_typology.sh T99 "typology-name"
set -e
EOF

# 3. Add it to the table above
```
