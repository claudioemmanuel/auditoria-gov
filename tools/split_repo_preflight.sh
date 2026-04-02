#!/usr/bin/env bash
# =============================================================================
# OpenWatch — Verify Split Readiness Pre-Flight Checklist
#
# This script verifies that the repo split can proceed safely.
# Use this BEFORE running: bash tools/split_repo.sh
#
# Usage:
#   bash tools/split_repo_preflight.sh
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
error() { echo -e "     ${RED}✗${NC}  $1"; }

FAILURES=0

step "OpenWatch Repo Split — Pre-Flight Checklist"

# =============================================================================
# 1. Git Status Clean
# =============================================================================

step "1. Checking git status..."

if [[ -n $(git status -s) ]]; then
  error "Git working directory is not clean. Commit or stash changes first."
  git status -s
  FAILURES=$((FAILURES + 1))
else
  info "Git working directory is clean"
fi

# =============================================================================
# 2. On main Branch
# =============================================================================

step "2. Checking current branch..."

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  warn "Current branch is: $CURRENT_BRANCH (should be: main)"
  warn "Switch to main first: git checkout main"
  FAILURES=$((FAILURES + 1))
else
  info "On main branch"
fi

# =============================================================================
# 3. git-filter-repo Installed
# =============================================================================

step "3. Checking git-filter-repo..."

if python3 -c "import git_filter_repo" 2>/dev/null; then
  info "git-filter-repo is installed"
else
  error "git-filter-repo not found. Install with: pip install git-filter-repo"
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# 4. Boundary Checker Passes
# =============================================================================

step "4. Running boundary checker..."

if bash tools/check_boundaries.py >/dev/null 2>&1; then
  info "Boundary checker passed (0 violations)"
else
  error "Boundary checker found violations. Fix before split."
  bash tools/check_boundaries.py
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# 5. Test Suite Passes
# =============================================================================

step "5. Running test suite..."

if command -v uv &>/dev/null; then
  if uv run --extra test pytest -q >/dev/null 2>&1; then
    info "All tests passing"
  else
    warn "Tests failing. Run: uv run --extra test pytest -q"
    FAILURES=$((FAILURES + 1))
  fi
else
  warn "uv not found, skipping tests"
fi

# =============================================================================
# 6. No Uncommitted Changes
# =============================================================================

step "6. Checking for uncommitted changes..."

if git diff-index --quiet HEAD --; then
  info "No uncommitted changes"
else
  error "Uncommitted changes detected. Commit first."
  git diff --stat
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# 7. Remote Up-to-Date
# =============================================================================

step "7. Checking if local is up-to-date with remote..."

git fetch origin >/dev/null 2>&1

LOCAL=$(git rev-parse main)
REMOTE=$(git rev-parse origin/main)

if [[ "$LOCAL" == "$REMOTE" ]]; then
  info "Local main is up-to-date with origin/main"
else
  warn "Local main is behind origin/main"
  warn "Run: git pull origin main"
  FAILURES=$((FAILURES + 1))
fi

# =============================================================================
# 8. GITHUB_TOKEN Set
# =============================================================================

step "8. Checking GITHUB_TOKEN..."

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  warn "GITHUB_TOKEN environment variable not set"
  warn "Set with: export GITHUB_TOKEN=<your-token>"
  warn "Token needs: repo, admin:org"
  FAILURES=$((FAILURES + 1))
else
  info "GITHUB_TOKEN is set"
fi

# =============================================================================
# 9. Backup Exists
# =============================================================================

step "9. Suggesting backup strategy..."

PARENT_DIR="$(dirname "$(git rev-parse --show-toplevel)")"
info "Parent directory: $PARENT_DIR"
info "Before split, create a backup:"
info "  cp -r $PARENT_DIR/openwatch $PARENT_DIR/openwatch.backup.$(date +%s)"

# =============================================================================
# Summary
# =============================================================================

echo ""
if [[ $FAILURES -eq 0 ]]; then
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║  ✅ All checks passed! Ready to split.                    ║"
  echo "╚════════════════════════════════════════════════════════════╝"
  echo ""
  echo "To proceed with split:"
  echo ""
  echo "  1. Create backup (recommended):"
  echo "     cp -r $PARENT_DIR/openwatch $PARENT_DIR/openwatch.backup"
  echo ""
  echo "  2. Run split (dry-run first):"
  echo "     bash tools/split_repo.sh --dry-run"
  echo ""
  echo "  3. If dry-run looks good, execute split:"
  echo "     bash tools/split_repo.sh"
  echo ""
  echo "  ⚠️  WARNING: Split is irreversible. Review dry-run output carefully."
  echo ""
else
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║  ❌ $FAILURES issue(s) found. Fix before split.            ║"
  echo "╚════════════════════════════════════════════════════════════╝"
  echo ""
  echo "Fix the issues above and run this script again."
  exit 1
fi
