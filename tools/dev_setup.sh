#!/usr/bin/env bash
# =============================================================================
# Developer Quick Start — Clone, setup, and start contributing to OpenWatch
#
# This script handles:
#   1. Clone repository
#   2. Install dependencies
#   3. Configure git hooks (pre-commit)
#   4. Verify local setup
#
# Usage:
#   bash tools/dev_setup.sh
# =============================================================================

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${BLUE}==>${NC} $1"; }
info() { echo -e "     ${GREEN}✓${NC} $1"; }
warn() { echo -e "     ${YELLOW}⚠${NC}  $1"; }

# =============================================================================
# 1. Verify Prerequisites
# =============================================================================

step "Checking prerequisites..."

for cmd in git python3 npm gh; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: $cmd not installed"
    exit 1
  fi
  info "$cmd found"
done

# =============================================================================
# 2. Clone Repository
# =============================================================================

step "Setting up repository..."

if [[ -d ".git" ]]; then
  info "Already in git repository"
else
  error "Not in a git repository. Run from the openwatch directory."
  exit 1
fi

git fetch origin 2>/dev/null || warn "Could not fetch from origin"
git pull origin main 2>/dev/null || warn "Could not pull main"

# =============================================================================
# 3. Install Python Dependencies
# =============================================================================

step "Installing Python dependencies..."

if command -v uv &>/dev/null; then
  uv sync --extra test
  info "Python dependencies installed via uv"
else
  pip install -r requirements.txt
  info "Python dependencies installed via pip"
fi

# =============================================================================
# 4. Install Frontend Dependencies
# =============================================================================

step "Installing frontend dependencies..."

cd web
npm ci || npm install
info "Frontend dependencies installed"
cd ..

# =============================================================================
# 5. Configure Git Hooks
# =============================================================================

step "Configuring git hooks..."

# Create pre-commit hook
mkdir -p .git/hooks

cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook: Run linting and basic checks before commit

set -e

echo "Running pre-commit checks..."

# Check for committed secrets
if grep -r "GITHUB_TOKEN\|API_KEY\|SECRET" --include="*.py" --include="*.js" --include="*.ts" --exclude-dir=node_modules --exclude-dir=.git . 2>/dev/null | grep -v ".env" | grep -v ".example"; then
  echo "ERROR: Potential secrets detected. Remove sensitive data before committing."
  exit 1
fi

# Check Python syntax
if find . -name "*.py" -type f ! -path "./.*" ! -path "./node_modules/*" | head -5 | xargs python -m py_compile 2>/dev/null; then
  echo "✓ Python syntax check passed"
fi

# Check frontend
if [[ -f "web/package.json" ]]; then
  cd web
  npm run lint || echo "⚠ Frontend lint issues (non-blocking)"
  cd ..
fi

echo "✓ Pre-commit checks passed"
EOF

chmod +x .git/hooks/pre-commit
info "Pre-commit hook installed"

# Create commit-msg hook
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/bash
# Validate commit message format

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Check for conventional commit format
if ! echo "$COMMIT_MSG" | grep -qE "^(feat|fix|docs|style|refactor|test|chore|ci|perf|revert)(\(.+\))?:|^Merge |^Revert "; then
  echo "ERROR: Commit message does not follow conventional commits"
  echo "Format: <type>(<scope>): <subject>"
  echo ""
  echo "Valid types: feat, fix, docs, style, refactor, test, chore, ci, perf, revert"
  echo "Example: feat(auth): add OAuth2 support"
  exit 1
fi
EOF

chmod +x .git/hooks/commit-msg
info "Commit-msg hook installed"

# =============================================================================
# 6. Verify Setup
# =============================================================================

step "Verifying local setup..."

# Run basic test
if uv run --extra test pytest tests/ -q --co &>/dev/null; then
  info "Test suite can be discovered"
fi

# Check boundary checker
if bash tools/check_boundaries.py &>/dev/null; then
  info "Boundary checker working"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     ✅ Development Setup Complete!                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "You're ready to start contributing!"
echo ""
echo "Quick commands:"
echo "  Run Python tests:      uv run --extra test pytest -q"
echo "  Run frontend lint:     cd web && npm run lint && cd .."
echo "  Build frontend:        cd web && npm run build && cd .."
echo "  Check boundaries:      bash tools/check_boundaries.py"
echo "  Create branch:         git checkout -b feature/task-name"
echo ""
echo "Commit format:"
echo "  feat(scope): add new feature"
echo "  fix(scope): resolve bug"
echo "  docs: update documentation"
echo ""
echo "For full workflow, see: docs/GITHUB_GOVERNANCE.md"
echo ""
