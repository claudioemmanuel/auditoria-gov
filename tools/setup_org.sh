#!/usr/bin/env bash
# =============================================================================
# OpenWatch — GitHub Organization Setup & Repository Transfer
# =============================================================================
#
# Automates Steps 1c–1f of the OpenWatch open-core migration:
#   1c. Configure the openwatch-br organization profile and permissions
#   1d. Transfer claudioemmanuel/openwatch → openwatch-br/openwatch
#   1e. Add account owner with Admin rights
#   1f. Create openwatch-br/openwatch-core (private core repo)
#       Set branch protection on both repos
#
# Prerequisites:
#   - gh CLI installed and authenticated: gh auth login
#   - Minimum token scopes (least privilege):
#       * repo      — transfer/create repositories and manage branch protection
#       * admin:org — manage organization membership and permissions
#     Add additional scopes only if you extend this script to perform other operations.
#   - Organization openwatch-br already created at https://github.com/openwatch-br
#
# Usage:
#   export GITHUB_USER=claudioemmanuel
#   bash tools/setup_org.sh [--dry-run]
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

ORG="openwatch-br"
REPO="openwatch"
CORE_REPO="openwatch-core"
GITHUB_USER="${GITHUB_USER:-claudioemmanuel}"
SOURCE_REPO="${GITHUB_USER}/openwatch"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
step()  { echo -e "\n${BLUE}==>${NC} $1"; }
info()  { echo -e "     ${GREEN}✓${NC} $1"; }
warn()  { echo -e "     ${YELLOW}⚠${NC}  $1"; }
error() { echo -e "     ${RED}✗${NC}  $1"; }
dry()   { echo -e "     ${YELLOW}[DRY-RUN]${NC} would: $1"; }

run() {
  if [[ "$DRY_RUN" == "true" ]]; then
    local cmd=""
    printf -v cmd '%q ' "$@"
    cmd="${cmd% }"
    dry "$cmd"
  else
    "$@"
  fi
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
step "Pre-flight checks"

command -v gh >/dev/null || { error "gh CLI not found — install from https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || { error "Not authenticated. Run: gh auth login --scopes repo,admin:org"; exit 1; }
info "gh CLI authenticated"

if ! gh api "orgs/${ORG}" >/dev/null 2>&1; then
  error "Organization '${ORG}' does not exist."
  error "Create it at https://github.com/account/organizations/new then re-run."
  exit 1
fi
info "Organization ${ORG} found"

# ---------------------------------------------------------------------------
# Step 1c — Configure organization profile
# ---------------------------------------------------------------------------
step "1c: Configuring organization profile"

run "gh api 'orgs/${ORG}' --method PATCH \\
  -f name='OpenWatch' \\
  -f description='Deterministic citizen-auditing platform for Brazilian federal public data' \\
  -f blog='https://openwatch.dev' \\
  -f location='Brazil' \\
  -f email='' \\
  -f twitter_username='' > /dev/null"
info "Org profile updated: name, description, blog, location"

# Set member privileges: members can read, only admins create repos
run "gh api 'orgs/${ORG}' --method PATCH \\
  -f default_repository_permission='read' \\
  -F members_can_create_repositories=false \\
  -F members_can_create_public_repositories=false \\
  -F members_can_create_private_repositories=false > /dev/null"
info "Member privileges: read-only, repo creation restricted to admins"

# ---------------------------------------------------------------------------
# Step 1d — Transfer repository
# ---------------------------------------------------------------------------
step "1d: Transferring ${SOURCE_REPO} → ${ORG}/${REPO}"

# Check if already transferred
if gh api "repos/${ORG}/${REPO}" >/dev/null 2>&1; then
  info "Repository already exists at ${ORG}/${REPO} — skipping transfer"
else
  run "gh api 'repos/${SOURCE_REPO}/transfer' --method POST \\
    -f new_owner='${ORG}' \\
    -f new_name='${REPO}' > /dev/null"
  info "Transfer initiated for ${SOURCE_REPO} → ${ORG}/${REPO}"
  echo "     Waiting 10 seconds for transfer to complete..."
  [[ "$DRY_RUN" == "false" ]] && sleep 10
fi

# Verify visibility preserved (must stay public)
if [[ "$DRY_RUN" == "false" ]]; then
  VISIBILITY=$(gh api "repos/${ORG}/${REPO}" --jq '.visibility')
  if [[ "$VISIBILITY" == "public" ]]; then
    info "Visibility confirmed: ${VISIBILITY}"
  else
    warn "Unexpected visibility: ${VISIBILITY} (expected public)"
  fi
fi

# ---------------------------------------------------------------------------
# Step 1e — Add owner and admin rights
# ---------------------------------------------------------------------------
step "1e: Setting ${GITHUB_USER} as Owner and Admin"

# Ensure user is an org owner
run "gh api 'orgs/${ORG}/memberships/${GITHUB_USER}' --method PUT \\
  -f role='admin' > /dev/null"
info "${GITHUB_USER} set as org Owner"

# Grant admin on repo
run "gh api 'repos/${ORG}/${REPO}/collaborators/${GITHUB_USER}' --method PUT \\
  -f permission='admin' > /dev/null"
info "${GITHUB_USER} set as repo Admin"

# ---------------------------------------------------------------------------
# Step 2c — Create openwatch-core (private)
# ---------------------------------------------------------------------------
step "2c: Creating ${ORG}/${CORE_REPO} (private)"

if gh api "repos/${ORG}/${CORE_REPO}" >/dev/null 2>&1; then
  info "Repository ${ORG}/${CORE_REPO} already exists — skipping"
else
  run "gh api 'orgs/${ORG}/repos' --method POST \\
    -f name='${CORE_REPO}' \\
    -f description='OpenWatch Core — Typologies, analytics, entity resolution, data pipelines (BSL 1.1)' \\
    -F private=true \\
    -F has_issues=true \\
    -F has_projects=false \\
    -F has_wiki=false \\
    -F auto_init=true \\
    -f default_branch='main' > /dev/null"
  info "Created private repo ${ORG}/${CORE_REPO}"
fi

run "gh api 'repos/${ORG}/${CORE_REPO}/collaborators/${GITHUB_USER}' --method PUT \\
  -f permission='admin' > /dev/null"
info "${GITHUB_USER} set as admin on ${CORE_REPO}"

# ---------------------------------------------------------------------------
# Step 1f — Branch protection: openwatch (public)
# ---------------------------------------------------------------------------
step "1f: Applying branch protection to ${ORG}/${REPO} (main)"

PUBLIC_BP='{
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

if [[ "$DRY_RUN" == "false" ]]; then
  echo "$PUBLIC_BP" | gh api "repos/${ORG}/${REPO}/branches/main/protection" \
    --method PUT --input - > /dev/null 2>&1 && \
    info "Branch protection applied to ${ORG}/${REPO}/main" || \
    warn "Branch protection may not be fully enforced (public repo on Free plan gets full enforcement)"
else
  dry "Apply branch protection JSON to repos/${ORG}/${REPO}/branches/main/protection"
fi

# ---------------------------------------------------------------------------
# Branch protection: openwatch-core (private)
# ---------------------------------------------------------------------------
step "Branch protection: ${ORG}/${CORE_REPO} (main)"

CORE_BP='{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}'

if [[ "$DRY_RUN" == "false" ]]; then
  echo "$CORE_BP" | gh api "repos/${ORG}/${CORE_REPO}/branches/main/protection" \
    --method PUT --input - > /dev/null 2>&1 && \
    info "Branch protection applied to ${ORG}/${CORE_REPO}/main" || \
    warn "Branch protection on private repo on Free plan: linear history + no force push enforced; PR reviews advisory only"
else
  dry "Apply branch protection to repos/${ORG}/${CORE_REPO}/branches/main/protection"
fi

# ---------------------------------------------------------------------------
# Labels — OSS repo
# ---------------------------------------------------------------------------
step "Configuring labels on ${ORG}/${REPO}"

LABELS=(
  "type/feature|0366d6|New functionality"
  "type/bug|d73a4a|Something is broken"
  "type/refactor|a2eeef|Code improvement without behavior change"
  "type/docs|cfd3d7|Documentation only"
  "type/chore|fef2e7|Maintenance and dependencies"
  "priority/high|ff0000|Must be addressed immediately"
  "priority/medium|ffaa00|Address in current sprint"
  "priority/low|00aa00|Nice to have"
  "status/backlog|cccccc|Work not yet started"
  "status/ready|0366d6|Ready for implementation"
  "status/in-progress|d4af37|Currently being worked on"
  "status/in-review|ffc0cb|Under peer review"
  "help-wanted|33aa33|Good for community contributions"
  "good-first-issue|7057ff|Recommended for first-time contributors"
  "security|e11d48|Related to security concerns"
)

for entry in "${LABELS[@]}"; do
  IFS='|' read -r name color desc <<< "$entry"
  if [[ "$DRY_RUN" == "false" ]]; then
    gh label create --repo "${ORG}/${REPO}" \
      --name "$name" --color "$color" --description "$desc" 2>/dev/null || \
    gh label edit --repo "${ORG}/${REPO}" \
      "$name" --color "$color" --description "$desc" 2>/dev/null || true
  else
    dry "create/update label '$name'"
  fi
done
info "Labels configured"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
step "1f: Final verification"

if [[ "$DRY_RUN" == "false" ]]; then
  REPO_URL=$(gh api "repos/${ORG}/${REPO}" --jq '.html_url' 2>/dev/null || echo "unknown")
  CORE_URL=$(gh api "repos/${ORG}/${CORE_REPO}" --jq '.html_url' 2>/dev/null || echo "unknown")
  REPO_VIS=$(gh api "repos/${ORG}/${REPO}" --jq '.visibility' 2>/dev/null || echo "unknown")
  CORE_VIS=$(gh api "repos/${ORG}/${CORE_REPO}" --jq '.visibility' 2>/dev/null || echo "unknown")

  echo ""
  echo "  OSS repo:   ${REPO_URL}  [${REPO_VIS}]"
  echo "  Core repo:  ${CORE_URL}  [${CORE_VIS}]"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║  ✅ Step 1 — GitHub Org Setup Complete                              ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Organization:  https://github.com/${ORG}"
echo "  OSS repo:      https://github.com/${ORG}/${REPO}   (public, MIT)"
echo "  Core repo:     https://github.com/${ORG}/${CORE_REPO}  (private, BSL 1.1)"
echo ""
echo "  ─── MANUAL ACTIONS STILL REQUIRED ──────────────────────────────────"
echo ""
echo "  1. LOGO: Upload org avatar at:"
echo "     https://github.com/organizations/${ORG}/settings/profile"
echo "     Concept: magnifying glass over a map of Brazil with signal dots,"
echo "     dark background, teal/white color scheme."
echo ""
echo "  2. CI SECRETS: Re-add all secrets in new repo settings:"
echo "     https://github.com/${ORG}/${REPO}/settings/secrets/actions"
echo "     Required: PORTAL_TRANSPARENCIA_TOKEN, DATAJUD_API_KEY,"
echo "               INTERNAL_API_KEY, CPF_HASH_SALT"
echo "     Optional: CORE_CI_ENABLED, OPENAI_API_KEY, ANTHROPIC_API_KEY"
echo ""
echo "  3. DEPLOY KEYS: Re-add any deploy keys (revoked on transfer):"
echo "     https://github.com/${ORG}/${REPO}/settings/keys"
echo ""
echo "  4. WEBHOOKS: Update payload URLs from claudioemmanuel/openwatch"
echo "     to ${ORG}/${REPO}:"
echo "     https://github.com/${ORG}/${REPO}/settings/hooks"
echo ""
echo "  5. CORE REPO INIT: Run the repo split to populate openwatch-core:"
echo "     export GITHUB_TOKEN=\$(gh auth token)"
echo "     export GITHUB_OWNER=${ORG}"
echo "     bash tools/split_repo.sh --dry-run   # review first"
echo "     bash tools/split_repo.sh             # execute"
echo ""
echo "  6. VERCEL: Update project settings to point to ${ORG}/${REPO}"
echo "     https://vercel.com/dashboard → project settings → Git"
echo ""
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  DRY RUN — no changes were made. Remove --dry-run to execute."
fi
