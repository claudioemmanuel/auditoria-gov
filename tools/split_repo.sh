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
GITHUB_OWNER="${GITHUB_OWNER:-claudioemmanuel}"
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
# NOTE: shared/models/graph.py, radar.py, coverage_v2.py are PUBLIC (API schemas)
# ---------------------------------------------------------------------------
PROTECTED_PATHS=(
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
  "infra"
  "docker-compose.yml"
  "docker-compose.prod.yml"
  # Protected connectors (enrichment strategy + data pipeline)
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
    --path "shared/db.py"
    --path "shared/config.py"
    --path "shared/logging.py"
    --path "pyproject.toml"
    --path "uv.lock"
    --path "Makefile"
    --path "LICENSE-BSL"
    --path "docker-compose.dev-lite.yml"
  )

  cd "${TEMP_DIR}"
  "${GIT_FILTER_REPO}" "${FILTER_ARGS[@]}" --force
  cd "${REPO_ROOT}"
fi

# ---------------------------------------------------------------------------
# Step 3: Set BSL 1.1 license on core repo + add README notice
# ---------------------------------------------------------------------------
step "3. Setting BSL license on core repo"
if [[ "$DRY_RUN" == "false" ]]; then
  # Replace any existing LICENSE with BSL
  cp "${REPO_ROOT}/LICENSE-BSL" "${TEMP_DIR}/LICENSE"

  cd "${TEMP_DIR}"
  git add LICENSE
  git commit -m "chore: set BSL 1.1 license for openwatch-core" \
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
  dry "curl -X POST https://api.github.com/user/repos \\"
  dry "  -H 'Authorization: token \$GITHUB_TOKEN' \\"
  dry "  -d '{\"name\":\"openwatch-core\",\"private\":true,\"description\":\"OpenWatch core: typologies, analytics, entity resolution, pipelines (BSL 1.1)\"}'"
  dry "cd ${CORE_DIR} && git remote set-url origin ${CORE_REMOTE} && git push --mirror"
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  # Create the private repo via GitHub API
  curl -s -X POST "https://api.github.com/user/repos" \
    -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"openwatch-core\",
      \"private\": true,
      \"description\": \"OpenWatch core: typologies, analytics, entity resolution, pipelines (BSL 1.1)\"
    }" | grep -E '"full_name"|"html_url"|"message"'

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
echo "   1. Set CORE_SERVICE_URL + CORE_API_KEY in GitHub Secrets"
echo "   2. Update CI/CD in openwatch-core to deploy the core service"
echo "   3. Delete the monorepo fallback branch from api/app/adapters/core_adapter.py"
echo "   4. Remove adapter exemption from tools/check_boundaries.py"
echo "   5. Update README with open-core architecture notice"
echo "======================================================================="
