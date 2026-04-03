#!/usr/bin/env bash
# =============================================================================
# OpenWatch — Open-Core Repository Split Migration Script
# =============================================================================
#
# STRATEGY (openwatch_temp):
#
#   1. Copy  openwatch/         → openwatch_temp/     (full safety copy)
#   2. Filter openwatch_temp/   → keep ONLY protected paths (git filter-repo)
#   3. Rename openwatch_temp/   → openwatch-core/     (protected, BSL 1.1)
#   4. Clean  openwatch/        → remove protected paths (MIT public repo)
#
# REMOTE STRATEGY:
#   - openwatch          (existing public GitHub repo) → push cleaned version
#   - openwatch-core     → new PRIVATE GitHub repo created via GitHub API
#
# Usage:
#   bash tools/split_repo.sh [--dry-run]
#
# Prerequisites:
#   git-filter-repo:  pip install git-filter-repo
#   curl:             for GitHub API calls (creates the private repo)
#   GITHUB_TOKEN env var set with repo creation permission
#
# Run from the monorepo root or via: cd /path/to/openwatch && bash tools/split_repo.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT_DIR="$(dirname "${REPO_ROOT}")"
REPO_NAME="$(basename "${REPO_ROOT}")"        # openwatch
TEMP_DIR="${PARENT_DIR}/openwatch_temp"        # full safety copy
CORE_DIR="${PARENT_DIR}/openwatch-core"        # final private core repo
GITHUB_OWNER="${GITHUB_OWNER:-openwatch-br}"
CORE_REMOTE="https://github.com/${GITHUB_OWNER}/openwatch-core.git"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
step()    { echo ""; echo "===> $1"; }
info()    { echo "     $1"; }
dry()     { echo "     [DRY-RUN] $1"; }
run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    dry "$*"
  else
    eval "$*"
  fi
}

# ---------------------------------------------------------------------------
# Protected paths — moved to openwatch-core, removed from public repo
#
# Two-layer path set covers both legacy (shared/worker/api) and
# canonical (core/packages) structures that coexist during the transition.
# The split script removes ALL of these from the public repo.
#
# PUBLIC (stays in openwatch):
#   apps/web/, packages/config/, packages/utils/, packages/models/(base/canonical/signals/vocabulary/coverage/graph)
#   packages/connectors/(6 public), packages/sdk/, packages/ui/
#   apps/api/app/routers/public.py, apps/api/alembic/, tests/public/
# ---------------------------------------------------------------------------
PROTECTED_PATHS=(
  # ── Canonical protected packages (core/) ──────────────────────────────────
  "core/typologies"
  "core/analytics"
  "core/er"
  "core/ai"
  "core/baselines"
  "core/services"
  "core/queries"
  "core/pipelines"
  "core/scheduler"
  # ── Canonical protected packages (packages/) ──────────────────────────────
  "packages/db"
  "packages/models/openwatch_models/orm.py"
  "packages/models/openwatch_models/raw.py"
  "packages/models/openwatch_models/radar.py"
  "packages/models/openwatch_models/public_filter.py"
  # ── Protected connectors (packages/connectors) ────────────────────────────
  "packages/connectors/openwatch_connectors/veracity.py"
  "packages/connectors/openwatch_connectors/bacen.py"
  "packages/connectors/openwatch_connectors/datajud.py"
  "packages/connectors/openwatch_connectors/tce_pe.py"
  "packages/connectors/openwatch_connectors/tce_rj.py"
  "packages/connectors/openwatch_connectors/tce_rs.py"
  "packages/connectors/openwatch_connectors/tce_sp.py"
  "packages/connectors/openwatch_connectors/tcu.py"
  "packages/connectors/openwatch_connectors/tse.py"
  "packages/connectors/openwatch_connectors/camara.py"
  "packages/connectors/openwatch_connectors/senado.py"
  "packages/connectors/openwatch_connectors/bndes.py"
  "packages/connectors/openwatch_connectors/jurisprudencia.py"
  "packages/connectors/openwatch_connectors/querido_diario.py"
  "packages/connectors/openwatch_connectors/transferegov.py"
  "packages/connectors/openwatch_connectors/anvisa_bps.py"
  "packages/connectors/openwatch_connectors/receita_cnpj.py"
  "packages/connectors/openwatch_connectors/orcamento_bim.py"
  # ── Internal API and infrastructure ──────────────────────────────────────
  "apps/api/app/routers/internal.py"
  "infra/aws"
  "infra/caddy"
  "infra/docker/docker-compose.prod.yml"
  "infra/docker/docker-compose.yml"
  # ── Legacy paths (shared/ worker/ api/) ──────────────────────────────────
  "shared/typologies"
  "shared/analytics"
  "shared/er"
  "shared/ai"
  "shared/baselines"
  "shared/services"
  "shared/repo"
  "shared/scheduler"
  "shared/models/orm.py"
  "shared/models/raw.py"
  "worker/tasks"
  "worker/worker_app.py"
  "worker/run_pipeline.py"
  "api/app/routers/internal.py"
  "api/app/adapters/core_adapter.py"
  "api/core_client.py"
  "docker-compose.yml"
  "docker-compose.prod.yml"
  # Protected legacy connectors
  "shared/connectors/veracity.py"
  "shared/connectors/bacen.py"
  "shared/connectors/datajud.py"
  "shared/connectors/tce_pe.py"
  "shared/connectors/tce_rj.py"
  "shared/connectors/tce_rs.py"
  "shared/connectors/tce_sp.py"
  "shared/connectors/tcu.py"
  "shared/connectors/tse.py"
  "shared/connectors/camara.py"
  "shared/connectors/senado.py"
  "shared/connectors/bndes.py"
  "shared/connectors/jurisprudencia.py"
  "shared/connectors/querido_diario.py"
  "shared/connectors/transferegov.py"
  "shared/connectors/anvisa_bps.py"
  "shared/connectors/receita_cnpj.py"
  "shared/connectors/orcamento_bim.py"
)

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
step "Pre-flight checks"

# Detect git-filter-repo: prefer uv-venv, fall back to system PATH
if command -v git-filter-repo &>/dev/null; then
  GIT_FILTER_REPO="git-filter-repo"
elif [[ -f "${REPO_ROOT}/.venv/Scripts/git-filter-repo" ]]; then
  GIT_FILTER_REPO="${REPO_ROOT}/.venv/Scripts/git-filter-repo"
elif [[ -f "${REPO_ROOT}/.venv/bin/git-filter-repo" ]]; then
  GIT_FILTER_REPO="${REPO_ROOT}/.venv/bin/git-filter-repo"
else
  echo "ERROR: git-filter-repo not found."
  echo "       Install with: pip install git-filter-repo   OR   uv pip install git-filter-repo"
  exit 1
fi
info "git-filter-repo: ${GIT_FILTER_REPO}"

if [[ "$DRY_RUN" == "false" ]] && [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "WARNING: GITHUB_TOKEN not set. Cannot auto-create remote repo."
  echo "         Set it or create the repo manually before running step 4."
fi

if [[ -d "${TEMP_DIR}" ]]; then
  echo "ERROR: ${TEMP_DIR} already exists. Remove it first:  rm -rf ${TEMP_DIR}"
  exit 1
fi

if [[ -d "${CORE_DIR}" ]]; then
  echo "ERROR: ${CORE_DIR} already exists. Remove it first:  rm -rf ${CORE_DIR}"
  exit 1
fi

info "Source monorepo: ${REPO_ROOT}"
info "Temp copy:       ${TEMP_DIR}"
info "Core target:     ${CORE_DIR}  →  ${CORE_REMOTE}"
info "Public target:   ${REPO_ROOT} (in-place cleanup)"
info "Dry run:         ${DRY_RUN}"

# ---------------------------------------------------------------------------
# Step 1: Full safety copy → openwatch_temp
# ---------------------------------------------------------------------------
step "1. Creating full safety copy → openwatch_temp"
info "cp -r ${REPO_ROOT} ${TEMP_DIR}"
if [[ "$DRY_RUN" == "false" ]]; then
  cp -r "${REPO_ROOT}" "${TEMP_DIR}"
fi

# ---------------------------------------------------------------------------
# Step 2: Filter openwatch_temp to ONLY protected paths (becomes core repo)
# ---------------------------------------------------------------------------
step "2. Filtering openwatch_temp to protected paths only (git filter-repo)"
info "Protected paths: ${#PROTECTED_PATHS[@]} items"
for p in "${PROTECTED_PATHS[@]}"; do
  info "  + ${p}"
done

if [[ "$DRY_RUN" == "false" ]]; then
  FILTER_ARGS=()
  for p in "${PROTECTED_PATHS[@]}"; do
    FILTER_ARGS+=(--path "${p}")
  done
  # Also keep root config files the core needs
  FILTER_ARGS+=(
    # Legacy shared support files (needed by worker tests during transition)
    --path "shared/db.py"
    --path "shared/db_sync.py"
    --path "shared/config.py"
    --path "shared/logging.py"
    --path "shared/middleware"
    --path "shared/utils"
    --path "shared/connectors/base.py"
    --path "shared/connectors/http_client.py"
    --path "shared/connectors/domain_guard.py"
    --path "shared/models/canonical.py"
    --path "shared/models/base.py"
    --path "shared/models/signals.py"
    --path "shared/models/vocabulary.py"
    --path "shared/models/coverage.py"
    --path "shared/models/coverage_v2.py"
    --path "shared/models/graph.py"
    # Full packages layer (core needs everything)
    --path "packages"
    # Workspace and tooling
    --path "pyproject.toml"
    --path "uv.lock"
    --path "Makefile"
    --path "LICENSE-BSL"
    --path "NOTICE-BSL"
    --path ".env.example"
    --path ".env.production.example"
    --path ".gitignore"
    --path "docker-compose.yml"
    --path "docker-compose.prod.yml"
    --path "infra"
    # Core tests
    --path "tests/core"
    --path "tests/worker"
    --path "tests/typologies"
    --path "tests/er"
    --path "tests/analytics"
    --path "tests/baselines"
    --path "tests/services"
    --path "tests/repo"
    --path "tests/scheduler"
    --path "tests/tasks"
    --path "tests/ai"
    # Legacy tests (needed during transition)
    --path "tests/test_config.py"
  )

  cd "${TEMP_DIR}"
  "${GIT_FILTER_REPO}" "${FILTER_ARGS[@]}" --force
  cd "${REPO_ROOT}"
fi

# ---------------------------------------------------------------------------
# Step 3: Set BSL 1.1 license on core repo + add README notice
# ---------------------------------------------------------------------------
step "3. Setting BSL license and NOTICE on core repo"
if [[ "$DRY_RUN" == "false" ]]; then
  # Compute change date: 4 years from today
  CHANGE_DATE=$(python3 -c "from datetime import date; d = date.today(); print(d.replace(year=d.year+4).isoformat())")

  # Write parameterized LICENSE (BSL 1.1 with concrete dates)
  cp "${REPO_ROOT}/LICENSE-BSL" "${TEMP_DIR}/LICENSE"
  # Replace the generic change date with the computed concrete date
  sed -i "s/Four years from the date each file was committed/${CHANGE_DATE}/g" "${TEMP_DIR}/LICENSE"

  # Copy the NOTICE file
  if [[ -f "${REPO_ROOT}/NOTICE-BSL" ]]; then
    cp "${REPO_ROOT}/NOTICE-BSL" "${TEMP_DIR}/NOTICE"
    # NOTICE-BSL contains placeholder date 2030-04-03 (computed at PR creation time).
    # Replace it with the authoritative CHANGE_DATE computed above so the
    # NOTICE always reflects the actual split execution date + 4 years.
    sed -i "s/2030-04-03/${CHANGE_DATE}/g" "${TEMP_DIR}/NOTICE"
  fi

  cd "${TEMP_DIR}"
  git add LICENSE NOTICE 2>/dev/null || git add LICENSE
  git commit -m "chore: apply BSL 1.1 license and NOTICE to openwatch-core

Change Date: ${CHANGE_DATE} (converts to Apache 2.0 at that date)
Licensor: claudioemmanuel / OpenWatch BR" \
    --author "claudioemmanuel <claudioemmanuel@users.noreply.github.com>" \
    || true
  cd "${REPO_ROOT}"
fi

# ---------------------------------------------------------------------------
# Step 4: Rename openwatch_temp → openwatch-core
# ---------------------------------------------------------------------------
step "4. Renaming openwatch_temp → openwatch-core"
run_cmd "mv '${TEMP_DIR}' '${CORE_DIR}'"

# ---------------------------------------------------------------------------
# Step 5: Create private remote + push core
# ---------------------------------------------------------------------------
step "5. Creating private GitHub repo: ${GITHUB_OWNER}/openwatch-core"
if [[ "$DRY_RUN" == "true" ]]; then
  dry "gh api orgs/${GITHUB_OWNER}/repos --method POST -f name=openwatch-core -F private=true"
  dry "cd ${CORE_DIR} && git remote set-url origin ${CORE_REMOTE} && git push --mirror"
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  # Repo may already exist (created by setup_org.sh)
  if ! gh api "repos/${GITHUB_OWNER}/openwatch-core" >/dev/null 2>&1; then
    gh api "orgs/${GITHUB_OWNER}/repos" --method POST \
      -f name="openwatch-core" \
      -F private=true \
      -f description="OpenWatch Core — typologies, analytics, entity resolution, pipelines (BSL 1.1)" | \
      grep -E '"full_name"|"html_url"'
  fi

  cd "${CORE_DIR}"
  git remote add origin "${CORE_REMOTE}"
  git push --mirror
  cd "${REPO_ROOT}"
else
  echo "     SKIPPED (GITHUB_TOKEN not set). Run manually:"
  echo "     cd ${CORE_DIR}"
  echo "     git remote add origin ${CORE_REMOTE}"
  echo "     git push --mirror"
fi

# ---------------------------------------------------------------------------
# Step 6: Remove protected paths from the public repo (in-place)
# ---------------------------------------------------------------------------
step "6. Removing protected paths from public repo"
if [[ "$DRY_RUN" == "false" ]]; then
  cd "${REPO_ROOT}"
  for p in "${PROTECTED_PATHS[@]}"; do
    if [[ -e "${p}" ]]; then
      info "  removing: ${p}"
      git rm -rf "${p}" --quiet || true
    fi
  done
  # Also remove now-orphaned internal API router
  if [[ -e "api/app/routers/internal.py" ]]; then
    git rm -f "api/app/routers/internal.py" --quiet || true
  fi
else
  for p in "${PROTECTED_PATHS[@]}"; do
    dry "git rm -rf ${p}"
  done
fi

# ---------------------------------------------------------------------------
# Step 7: Commit the cleanup in public repo
# ---------------------------------------------------------------------------
step "7. Committing public repo cleanup"
if [[ "$DRY_RUN" == "false" ]]; then
  cd "${REPO_ROOT}"
  git add -A
  git commit -m "chore(split): remove protected core modules from public repo

All typology logic, analytics, entity resolution, enrichment connectors,
and internal pipelines have been moved to openwatch-core (BSL 1.1).

The public layer now contains only:
- FastAPI public router (via dual-mode CoreClient adapter)
- Generic government data connectors (6 connectors)
- Public API response schemas
- SDK packages, frontend, documentation

Core is accessed via CORE_SERVICE_URL + CORE_API_KEY in production." \
    --author "claudioemmanuel <claudioemmanuel@users.noreply.github.com>"
fi

# ---------------------------------------------------------------------------
# Step 8: Verify boundary checker on cleaned public repo
# ---------------------------------------------------------------------------
step "8. Verifying public repo boundaries"
echo "     Running tools/check_boundaries.py..."
if [[ "$DRY_RUN" == "false" ]]; then
  python "${REPO_ROOT}/tools/check_boundaries.py"
else
  dry "python tools/check_boundaries.py"
fi

# ---------------------------------------------------------------------------
# Step 9: Push cleaned public repo
# ---------------------------------------------------------------------------
step "9. Pushing public repo to origin"
if [[ "$DRY_RUN" == "false" ]]; then
  cd "${REPO_ROOT}"
  git push origin main
else
  dry "git push origin main"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo " SPLIT COMPLETE"
echo "======================================================================="
if [[ "$DRY_RUN" == "true" ]]; then
  echo " DRY RUN — no changes made. Re-run without --dry-run to execute."
else
  echo " Public repo (MIT):    ${REPO_ROOT}"
  echo "                       github.com/${GITHUB_OWNER}/openwatch"
  echo ""
  echo " Private core (BSL):   ${CORE_DIR}"
  echo "                       github.com/${GITHUB_OWNER}/openwatch-core"
fi
echo ""
echo " Next steps:"
echo "   1. Add CORE_SERVICE_URL + CORE_API_KEY to GitHub Secrets in both repos"
echo "   2. Re-add all CI secrets (not transferred during split) in openwatch-core"
echo "   3. Update CI/CD in openwatch-core to deploy the core service"
echo "   4. Set CORE_SERVICE_URL in openwatch/.env.production.example"
echo "   5. Verify boundary checker passes: uv run python tools/check_boundaries.py"
echo "======================================================================="
