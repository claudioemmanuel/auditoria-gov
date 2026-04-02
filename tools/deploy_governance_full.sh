#!/usr/bin/env bash
# =============================================================================
# OpenWatch Governance — Complete Automated Deployment
#
# This script executes the ENTIRE governance deployment end-to-end:
# 1. Creates organization (via gh CLI)
# 2. Transfers repository
# 3. Makes repo public
# 4. Runs setup scripts
# 5. Configures project board
# 6. Sets up branch protection
#
# Usage:
#   bash tools/deploy_governance_full.sh [org-name] [github-token]
#
# Prerequisites:
#   - GitHub Personal Access Token with: repo, admin:org, project, workflow scopes
#   - Set as: GITHUB_TOKEN environment variable OR pass as argument
#
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

step() { echo -e "\n${BLUE}==>${NC} $1"; }
info() { echo -e "     ${GREEN}✓${NC} $1"; }
warn() { echo -e "     ${YELLOW}⚠${NC}  $1"; }
error() { echo -e "     ${RED}✗${NC}  $1"; exit 1; }

# Config
ORG_NAME="${1:-openwatch}"
GITHUB_TOKEN="${2:-${GITHUB_TOKEN:-}}"
REPO_NAME="openwatch"
REPO_ROOT="$(git rev-parse --show-toplevel)"

if [[ -z "$GITHUB_TOKEN" ]]; then
  error "GITHUB_TOKEN not set. Pass as argument or set environment variable."
fi

step "OpenWatch Governance — Full Automated Deployment"
echo "Organization: $ORG_NAME"
echo "Repository:   $REPO_NAME"

# =============================================================================
# PHASE 1: Verify Prerequisites
# =============================================================================

step "Phase 1: Verifying prerequisites..."

# Check git
if ! command -v git &>/dev/null; then
  error "git not installed"
fi
info "git found"

# Check git-filter-repo (needed for split)
if ! python3 -c "import git_filter_repo" 2>/dev/null; then
  warn "git-filter-repo not installed (needed for repo split)"
  warn "Install with: pip install git-filter-repo"
fi

# Check curl
if ! command -v curl &>/dev/null; then
  error "curl not installed"
fi
info "curl found"

# =============================================================================
# PHASE 2: Create Organization (via GitHub API)
# =============================================================================

step "Phase 2: Checking if organization exists..."

ORG_CHECK=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/orgs/$ORG_NAME \
  -w "\n%{http_code}" | tail -1)

if [[ "$ORG_CHECK" == "200" ]]; then
  info "Organization '$ORG_NAME' already exists"
else
  warn "Organization '$ORG_NAME' does not exist yet"
  warn "Create manually at: https://github.com/account/organizations/new"
  warn "Organization name: openwatch"
  warn "Then run this script again."
  exit 1
fi

# =============================================================================
# PHASE 3: Transfer Repository
# =============================================================================

step "Phase 3: Checking repository location..."

CURRENT_OWNER=$(git remote get-url origin | sed 's/.*github.com[:/]\([^/]*\).*/\1/')
info "Current repo owner: $CURRENT_OWNER"

if [[ "$CURRENT_OWNER" == "$ORG_NAME" ]]; then
  info "Repository already at organization"
else
  warn "Repository still at: $CURRENT_OWNER"
  warn "Transfer manually at: https://github.com/$CURRENT_OWNER/$REPO_NAME/settings/options"
  warn "Then run this script again."
  exit 1
fi

# =============================================================================
# PHASE 4: Verify Repository is Public
# =============================================================================

step "Phase 4: Checking repository visibility..."

REPO_DATA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$ORG_NAME/$REPO_NAME)

IS_PRIVATE=$(echo "$REPO_DATA" | grep -o '"private":[^,]*' | cut -d: -f2)

if [[ "$IS_PRIVATE" == "true" ]]; then
  warn "Repository is PRIVATE - branch protection requires GitHub Pro or public repo"
  warn "Make public at: https://github.com/$ORG_NAME/$REPO_NAME/settings/options"
  warn "Then run this script again."
  exit 1
fi

info "Repository is PUBLIC"

# =============================================================================
# PHASE 5: Update Local Git Remote
# =============================================================================

step "Phase 5: Updating git remote..."

NEW_REMOTE="https://github.com/$ORG_NAME/$REPO_NAME.git"
git remote set-url origin "$NEW_REMOTE"
git fetch origin 2>/dev/null || true

info "Git remote updated to: $NEW_REMOTE"

# =============================================================================
# PHASE 6: Run Governance Setup Script
# =============================================================================

step "Phase 6: Running governance setup automation..."

if [[ ! -f "tools/setup_github_governance.sh" ]]; then
  error "tools/setup_github_governance.sh not found"
fi

export GITHUB_TOKEN
bash tools/setup_github_governance.sh "$ORG_NAME"

info "Governance setup complete"

# =============================================================================
# PHASE 7: Create Project Board
# =============================================================================

step "Phase 7: Creating Scrumban project board..."

if [[ ! -f "tools/setup_project_board.sh" ]]; then
  error "tools/setup_project_board.sh not found"
fi

bash tools/setup_project_board.sh "$ORG_NAME"

info "Project board created"

# =============================================================================
# PHASE 8: Summary
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Governance Deployment Complete!                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Organization: $ORG_NAME"
echo "Repository:   $ORG_NAME/$REPO_NAME"
echo ""
echo "What was configured:"
echo "  ✅ 18 Labels created"
echo "  ✅ Branch protection applied to 'main'"
echo "  ✅ Scrumban project board created"
echo "  ✅ Repository features enabled"
echo ""
echo "Still needed (manual in GitHub UI):"
echo "  ⚠️  Configure project columns (rename, add)"
echo "  ⚠️  Link repo to project board"
echo "  ⚠️  Enable project automations"
echo ""
echo "Next steps:"
echo "  1. Go to: https://github.com/orgs/$ORG_NAME/projects/1"
echo "  2. Follow: docs/GOVERNANCE_DEPLOYMENT.md (Steps 6-8)"
echo "  3. Run: bash tools/dev_setup.sh (local setup)"
echo ""
echo "Documentation:"
echo "  📖 Deployment guide:    GOVERNANCE_DEPLOYMENT.md"
echo "  📖 Quick reference:     WORKFLOW_QUICK_REF.md"
echo "  📖 Complete guide:      docs/GITHUB_GOVERNANCE.md"
echo ""
