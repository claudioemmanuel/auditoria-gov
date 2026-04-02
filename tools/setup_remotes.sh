#!/usr/bin/env bash
# =============================================================================
# OpenWatch — Remote Repository Setup Script
# =============================================================================
#
# Run AFTER tools/split_repo.sh to configure GitHub secrets and verify
# both repositories are correctly accessible.
#
# Usage:
#   GITHUB_TOKEN=<token> bash tools/setup_remotes.sh
#
# Prerequisites:
#   - Both openwatch and openwatch-core repos must exist on GitHub
#   - GITHUB_TOKEN with 'repo' + 'admin:repo_hook' scopes
#   - CORE_SERVICE_URL: the deployed URL of openwatch-core API
#   - CORE_API_KEY: shared secret between public API and core service
# =============================================================================

set -euo pipefail

GITHUB_OWNER="${GITHUB_OWNER:-claudioemmanuel}"
GITHUB_TOKEN="${GITHUB_TOKEN:?Set GITHUB_TOKEN env var}"
CORE_SERVICE_URL="${CORE_SERVICE_URL:-}"
CORE_API_KEY="${CORE_API_KEY:-}"

step() { echo ""; echo "===> $1"; }
api()  { curl -sf -H "Authorization: token ${GITHUB_TOKEN}" "$@"; }

# ---------------------------------------------------------------------------
# Verify repos exist
# ---------------------------------------------------------------------------
step "Verifying GitHub repos"

PUBLIC_REPO=$(api "https://api.github.com/repos/${GITHUB_OWNER}/openwatch" | grep '"full_name"')
echo "  Public:  ${PUBLIC_REPO}"

CORE_REPO=$(api "https://api.github.com/repos/${GITHUB_OWNER}/openwatch-core" | grep '"full_name"')
echo "  Core:    ${CORE_REPO}"

# ---------------------------------------------------------------------------
# Set GitHub Actions secrets on the PUBLIC repo
# ---------------------------------------------------------------------------
step "Setting GitHub Secrets on public repo (openwatch)"

if [[ -z "${CORE_SERVICE_URL}" ]]; then
  echo "  CORE_SERVICE_URL not provided — skipping secret creation."
  echo "  Set it with: CORE_SERVICE_URL=https://core.yourhost.com bash tools/setup_remotes.sh"
else
  # GitHub requires the secret value to be base64-encoded + encrypted.
  # For simplicity, print the manual steps — use 'gh secret set' for automation.
  echo ""
  echo "  Run these commands to set secrets (requires gh CLI or GitHub UI):"
  echo ""
  echo "  gh secret set CORE_SERVICE_URL --body '${CORE_SERVICE_URL}' --repo ${GITHUB_OWNER}/openwatch"
  echo "  gh secret set CORE_API_KEY     --body '<your-key>'          --repo ${GITHUB_OWNER}/openwatch"
  echo ""
  echo "  Or via GitHub UI:"
  echo "  https://github.com/${GITHUB_OWNER}/openwatch/settings/secrets/actions"
fi

# ---------------------------------------------------------------------------
# Verify branch protection on main
# ---------------------------------------------------------------------------
step "Checking branch protection on main"
PROTECTION=$(api "https://api.github.com/repos/${GITHUB_OWNER}/openwatch/branches/main/protection" 2>/dev/null || echo "{}")
if echo "${PROTECTION}" | grep -q '"required_pull_request_reviews"'; then
  echo "  Branch protection: ENABLED"
else
  echo "  Branch protection: NOT CONFIGURED"
  echo "  Apply it with: bash docs/branch-protection.json (see docs/GITHUB_ORG_SETUP.md)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo " REMOTE SETUP COMPLETE"
echo "======================================================================="
echo ""
echo " Public repo:  https://github.com/${GITHUB_OWNER}/openwatch"
echo " Core repo:    https://github.com/${GITHUB_OWNER}/openwatch-core"
echo ""
echo " Remaining manual steps:"
echo "   1. Apply branch protection ruleset (docs/GITHUB_ORG_SETUP.md)"
echo "   2. Create Projects v2 Scrumban board (docs/GITHUB_ORG_SETUP.md)"
echo "   3. Set CORE_SERVICE_URL + CORE_API_KEY secrets"
echo "   4. Deploy openwatch-core service and update CORE_SERVICE_URL"
echo "======================================================================="
