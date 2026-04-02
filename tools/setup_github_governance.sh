#!/usr/bin/env bash
# =============================================================================
# setup_github_governance.sh — Automated GitHub Organization & Governance Setup
#
# This script automates the setup of the OpenWatch GitHub organization,
# repository configuration, and governance workflows.
#
# Prerequisites:
#   - gh CLI installed and authenticated with proper scopes
#   - Repository already transferred to organization
#   - Repository is PUBLIC
#
# Usage:
#   bash tools/setup_github_governance.sh [--org-name] [--dry-run]
#
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Config
DRY_RUN=false
ORG_NAME="${1:-openwatch}"
REPO_NAME="openwatch"

if [[ "${2:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

# Helpers
step() { echo -e "\n${BLUE}==>${NC} $1"; }
info() { echo -e "     ${GREEN}✓${NC} $1"; }
warn() { echo -e "     ${YELLOW}⚠${NC}  $1"; }
error() { echo -e "     ${RED}✗${NC}  $1"; }
dry() { echo -e "     ${YELLOW}[DRY-RUN]${NC} $1"; }
run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    dry "$*"
  else
    eval "$*"
  fi
}

# =============================================================================
# PHASE 1: Verify Prerequisites
# =============================================================================

step "Verifying prerequisites..."

# Check gh CLI
if ! command -v gh &>/dev/null; then
  error "gh CLI not installed. Download from: https://cli.github.com"
  exit 1
fi
info "gh CLI found"

# Check authentication
if ! gh auth status &>/dev/null; then
  error "Not authenticated with gh CLI. Run: gh auth login"
  exit 1
fi
info "gh auth verified"

# Check scopes
AUTH_SCOPES=$(gh auth status 2>&1 | grep "Scopes:" | sed 's/.*Scopes://')
if [[ ! $AUTH_SCOPES =~ "project" ]]; then
  warn "Missing 'project' scope. Running: gh auth refresh --scopes repo,admin:org,project"
  run_cmd "gh auth refresh --scopes repo,admin:org,project"
fi
info "Required scopes present"

# Check org exists
if ! gh api orgs/$ORG_NAME &>/dev/null 2>&1; then
  error "Organization '$ORG_NAME' does not exist"
  error "Create it manually at: https://github.com/account/organizations/new"
  exit 1
fi
info "Organization '$ORG_NAME' exists"

# Check repo exists
if ! gh api repos/$ORG_NAME/$REPO_NAME &>/dev/null 2>&1; then
  error "Repository '$ORG_NAME/$REPO_NAME' does not exist"
  exit 1
fi
info "Repository '$ORG_NAME/$REPO_NAME' exists"

# Check repo is public
REPO_PRIVATE=$(gh api repos/$ORG_NAME/$REPO_NAME --jq '.private')
if [[ "$REPO_PRIVATE" == "true" ]]; then
  error "Repository must be PUBLIC to use branch protection (without GitHub Pro)"
  warn "Change at: https://github.com/$ORG_NAME/$REPO_NAME/settings/options#visibility"
  exit 1
fi
info "Repository is PUBLIC"

# =============================================================================
# PHASE 2: Create Labels (if missing)
# =============================================================================

step "Configuring labels..."

LABELS=(
  "type/feature:0366d6:New functionality"
  "type/bug:d73a4a:Something is broken"
  "type/refactor:a2eeef:Code improvement without behavior change"
  "type/docs:cfd3d7:Documentation only"
  "type/chore:fef2e7:Maintenance and dependencies"
  "priority/high:ff0000:Must be addressed immediately"
  "priority/medium:ffaa00:Address in current sprint"
  "priority/low:00aa00:Nice to have"
  "status/backlog:cccccc:Work not yet started"
  "status/ready:0366d6:Ready for implementation"
  "status/in-progress:d4af37:Currently being worked on"
  "status/in-review:ffc0cb:Under peer review"
  "status/done:90ee90:Completed"
  "blocked:ff0000:Something is blocking this"
  "help-wanted:33aa33:Good for community contributions"
  "good-first-issue:7057ff:Recommended for first-time contributors"
  "documentation:0075ca:Improves or adds documentation"
  "security:ff0000:Related to security concerns"
)

for label_config in "${LABELS[@]}"; do
  IFS=':' read -r name color description <<< "$label_config"
  
  # Check if label exists
  if gh label list --repo $ORG_NAME/$REPO_NAME --json name | grep -q "\"$name\""; then
    info "Label '$name' already exists"
  else
    run_cmd "gh label create --repo $ORG_NAME/$REPO_NAME --name '$name' --color '$color' --description '$description'"
    info "Label '$name' created"
  fi
done

# =============================================================================
# PHASE 3: Create Project Board
# =============================================================================

step "Creating Scrumban project board..."

if ! gh api orgs/$ORG_NAME/projects --jq '.[] | select(.name == "OpenWatch Development Board")' | grep -q "OpenWatch"; then
  warn "Project board will be created by: bash tools/setup_project_board.sh"
  warn "Please run that script next to create the board"
else
  info "Project board already exists"
fi

# =============================================================================
# PHASE 4: Configure Branch Protection
# =============================================================================

step "Configuring branch protection on 'main'..."

PROTECTION_PAYLOAD='{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Python — Public Packages & API",
      "Frontend — Next.js",
      "PR Validation / Require linked issue",
      "PR Validation / Conventional commit title",
      "PR Validation / Branch name convention",
      "Open-Core Boundary Enforcement"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "allow_fork_syncing": true
}'

run_cmd "gh api repos/$ORG_NAME/$REPO_NAME/branches/main/protection \
  -X PUT \
  -f required_status_checks='$PROTECTION_PAYLOAD' || true"

# Verify protection was applied
if gh api repos/$ORG_NAME/$REPO_NAME/branches/main/protection &>/dev/null 2>&1; then
  info "Branch protection successfully applied to 'main'"
else
  warn "Branch protection may not be available (create a test PR to verify)"
fi

# =============================================================================
# PHASE 5: Configure Repository Settings
# =============================================================================

step "Configuring repository settings..."

# Enable required features
run_cmd "gh api repos/$ORG_NAME/$REPO_NAME \
  -X PATCH \
  -f has_issues:=true \
  -f has_projects:=true \
  -f has_wiki:=false \
  -f has_downloads:=false" || true

info "Repository features configured"

# =============================================================================
# PHASE 6: Verify Workflows
# =============================================================================

step "Verifying GitHub Actions workflows..."

WORKFLOWS=(".github/workflows/")
if [[ -d "${WORKFLOWS[0]}" ]]; then
  WORKFLOW_COUNT=$(ls -1 ${WORKFLOWS[0]}*.yml 2>/dev/null | wc -l)
  info "$WORKFLOW_COUNT workflows found"
else
  warn "No GitHub Actions workflows directory found"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ✅ OpenWatch Governance Setup Complete!                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Summary:"
echo "  Organization:    $ORG_NAME"
echo "  Repository:      $ORG_NAME/$REPO_NAME"
echo "  Status:          PUBLIC"
echo "  Labels:          ${#LABELS[@]} configured"
echo "  Branch:          main (protected)"
echo ""
echo "Next steps:"
echo "  1. Create project board:"
echo "     bash tools/setup_project_board.sh $ORG_NAME"
echo ""
echo "  2. Configure project automation (manual in GitHub UI):"
echo "     https://github.com/orgs/$ORG_NAME/projects"
echo ""
echo "  3. Create first test issue:"
echo "     https://github.com/$ORG_NAME/$REPO_NAME/issues/new"
echo ""
echo "  4. Train team on workflow:"
echo "     See: docs/GITHUB_GOVERNANCE.md"
echo ""
