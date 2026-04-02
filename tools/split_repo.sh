#!/usr/bin/env bash
# =============================================================================
# OpenWatch — Open-Core Repository Split Migration Script
# =============================================================================
#
# This script performs the physical split of the monorepo into:
#   - openwatch          (public, MIT)     — current repo, cleaned
#   - openwatch-core     (private, BSL)    — new private repo with protected modules
#
# Usage:
#   bash tools/split_repo.sh [--dry-run]
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - git with filter-repo: pip install git-filter-repo
#   - Run from the root of the openwatch monorepo
#   - Review OPEN_CORE_STRATEGY.md before running
#
# IMPORTANT: Take a full backup before running. This script is destructive.
# =============================================================================

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "[DRY RUN] No changes will be made."
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
CORE_REPO="openwatch-core"
CORE_DIR="/tmp/${CORE_REPO}"

echo ""
echo "==================================================================="
echo " OpenWatch Open-Core Split"
echo "==================================================================="
echo " Source (public):  ${REPO_ROOT}"
echo " Target (private): ${CORE_DIR} -> github:claudioemmanuel/${CORE_REPO}"
echo "==================================================================="
echo ""

# ---------------------------------------------------------------------------
# PROTECTED paths to move to openwatch-core
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
  "shared/models/graph.py"
  "shared/models/radar.py"
  "shared/models/coverage.py"
  "shared/models/coverage_v2.py"
  "worker/tasks"
  "worker/worker_app.py"
  "worker/run_pipeline.py"
  "api/app/routers/internal.py"
  "infra"
  "docker-compose.yml"
  "docker-compose.prod.yml"
  # Protected connectors
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

step() { echo ""; echo "--- $1 ---"; }

# ---------------------------------------------------------------------------
# Step 1: Create the private core repo clone
# ---------------------------------------------------------------------------
step "1. Cloning current repo to ${CORE_DIR}"
if [[ "$DRY_RUN" == "false" ]]; then
  rm -rf "${CORE_DIR}"
  git clone "${REPO_ROOT}" "${CORE_DIR}"
fi

# ---------------------------------------------------------------------------
# Step 2: Strip core clone to ONLY protected paths
# ---------------------------------------------------------------------------
step "2. Filtering core clone to protected paths only"
if [[ "$DRY_RUN" == "false" ]]; then
  cd "${CORE_DIR}"
  # Build --path args for git filter-repo
  FILTER_ARGS=()
  for p in "${PROTECTED_PATHS[@]}"; do
    FILTER_ARGS+=(--path "$p")
  done
  git filter-repo "${FILTER_ARGS[@]}" --force
  cd "${REPO_ROOT}"
fi

# ---------------------------------------------------------------------------
# Step 3: Add BSL license to core repo
# ---------------------------------------------------------------------------
step "3. Setting BSL 1.1 license on core repo"
if [[ "$DRY_RUN" == "false" ]]; then
  cp "${REPO_ROOT}/LICENSE-BSL" "${CORE_DIR}/LICENSE"
fi

# ---------------------------------------------------------------------------
# Step 4: Create private GitHub repo and push
# ---------------------------------------------------------------------------
step "4. Creating private GitHub repo: ${CORE_REPO}"
if [[ "$DRY_RUN" == "false" ]]; then
  gh repo create "claudioemmanuel/${CORE_REPO}" \
    --private \
    --description "OpenWatch core: typologies, analytics, entity resolution, pipelines (BSL 1.1)" \
    || echo "Repo may already exist, continuing..."

  cd "${CORE_DIR}"
  git remote set-url origin "https://github.com/claudioemmanuel/${CORE_REPO}.git"
  git push --mirror
  cd "${REPO_ROOT}"
fi

# ---------------------------------------------------------------------------
# Step 5: Remove protected paths from the public repo
# ---------------------------------------------------------------------------
step "5. Removing protected paths from public repo"
if [[ "$DRY_RUN" == "false" ]]; then
  for p in "${PROTECTED_PATHS[@]}"; do
    if [[ -e "${REPO_ROOT}/${p}" ]]; then
      git rm -rf "${REPO_ROOT}/${p}" 2>/dev/null || true
    fi
  done
fi

# ---------------------------------------------------------------------------
# Step 6: Add MIT license marker + verify
# ---------------------------------------------------------------------------
step "6. Verifying public repo is clean"
echo "Checking for protected imports in public layer..."
python "${REPO_ROOT}/tools/check_boundaries.py"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==================================================================="
echo " SPLIT COMPLETE"
echo "==================================================================="
echo " Public repo:  ${REPO_ROOT}  (MIT)"
echo " Private core: ${CORE_DIR}  -> github.com/claudioemmanuel/${CORE_REPO} (BSL 1.1)"
echo ""
echo " Next steps:"
echo "   1. Review git status in both repos"
echo "   2. Run tests: uv run --extra test pytest -q"
echo "   3. Update CI/CD to use CORE_SERVICE_URL env var"
echo "   4. Commit and push the public repo"
echo "   5. Update README with open-core notice"
echo "==================================================================="
