# GitHub Organization & Governance Setup
## Production-Grade Workflow for OpenWatch

**Status:** Ready for Implementation  
**Last Updated:** April 2, 2026  
**Target:** `openwatch` Organization on GitHub

---

## Overview

This document outlines the complete setup for OpenWatch's GitHub organization, repository governance, and task execution pipeline. The system enforces a strict **Issue → Project → PR → Merge → Done** workflow using GitHub's native features and automation.

**Key Principles:**
- ✅ Every change must start with an Issue
- ✅ All work tracked in the development board (Projects v2)
- ✅ Pull requests require review and passing CI before merge
- ✅ `main` branch is always deployable and immutable
- ✅ Contributors guided by automation, not manual processes

---

## PHASE 1 — ORGANIZATION SETUP

### Checkpoint: Prerequisites

Before starting, ensure you have:

```bash
# ✅ GitHub CLI installed and authenticated
gh --version
gh auth login

# ✅ Verify you have 'project' scope
gh auth status

# ✅ Correct personal access token with:
# • repo (full repo control)
# • admin:org (org management)
# • project (project v2 access)
# • read:user (user profile)
```

### Step 1.1: Create GitHub Organization

**Via GitHub CLI:**

```bash
# Create organization (via web because CLI doesn't support org creation)
# Go to: https://github.com/account/organizations/new
# Organization name: openwatch
# Billing email: [your-email]
# Organization display name: OpenWatch
# Organization description: Deterministic citizen-auditing platform for Brazilian public data
```

**Via GitHub Web UI:**

1. Go to **https://github.com/account/organizations/new**
2. Fill in details:
   - **Organization name:** `openwatch`
   - **Billing email:** Your email
   - **Organization display name:** `OpenWatch`
   - **Organization description:** 
     ```
     Deterministic citizen-auditing platform for Brazilian public data
     ```
   - **Organization website:** (optional)
   - **Organization public profile:** ✅ Checked (Public)
3. Click **Create organization**

### Step 1.2: Configure Organization Settings

```bash
# After org is created, configure via UI or API
# Documentation visibility
# → Settings → General → Public profile: enabled
# → Settings → Access → Manage policies: set up team structure
```

**Teams to create:**
- `core` — Project maintainers (write access)
- `contributors` — External contributors (triage access)
- `admins` — Organization admins (owner access)

```bash
# Create teams via API or UI
# UI: Settings → Teams → New team
gh api graphql -f query='
mutation {
  createTeam(input: {
    organizationId: "ORG_ID"
    name: "core"
    description: "OpenWatch core maintainers"
    privacy: CLOSED
  }) {
    team {
      id
      name
    }
  }
}
'
```

### Step 1.3: Transfer Repository Ownership

⚠️ **this is irreversible — ensure the org exists first**

**Via GitHub Web UI:**

1. Go to repository: **https://github.com/YOUR_USERNAME/openwatch**
2. **Settings** → **General** (scroll down)
3. **Transfer** → Enter organization name: `openwatch`
4. Confirm transfer

**Via GitHub CLI:**

```bash
# NOTE: CLI doesn't have direct transfer command; use web UI or API

# Verify transfer completed
gh repo view openwatch/openwatch --web
```

**Post-Transfer Verification:**

```bash
# Update git remote to point to org repo
cd /path/to/openwatch
git remote set-url origin https://github.com/openwatch/openwatch.git

# Verify
git remote -v
# origin  https://github.com/openwatch/openwatch.git (fetch)
# origin  https://github.com/openwatch/openwatch.git (push)

# Sync with new remote
git fetch origin
git pull origin main
```

---

## PHASE 2 — REPOSITORY CONFIGURATION

### Step 2.1: Repository Visibility & Settings

All these settings must be PUBLIC or require GitHub Pro for private repos.

**Via GitHub Web UI:**
1. Go to **Settings** → **General**
2. **Visibility:** Change to **Public**
3. **Collaborators access (IMPORTANT):**
   - Disable: "Allow repository admins to create workflows"
   - Enable: "Require all discussions to be resolved"
   - Enable: "Require conversation resolution before merging"

### Step 2.2: Verify Open Source Files

Ensure the following files exist in the **root directory**:

```bash
# Check they exist
ls -la | grep -E "(LICENSE|README|CONTRIBUTING|CODE_OF_CONDUCT|SECURITY)"

# Expected output:
# -rw-r--r-- CODE_OF_CONDUCT.md
# -rw-r--r-- CONTRIBUTING.md
# -rw-r--r-- LICENSE
# -rw-r--r-- LICENSE-BSL
# -rw-r--r-- README.md
# -rw-r--r-- SECURITY.md
```

**Files present? ✅ No action needed.**

### Step 2.3: Enable GitHub Features

Navigate to **Settings** → scroll to "Features":

- ✅ **Issues** — enabled
- ✅ **Discussions** — enabled (for community Q&A)
- ✅ **Projects** — enabled (for development board)
- ✅ **Actions** — enabled (for CI/CD)
- ✅ **Wiki** — disabled (use docs/ instead)

### Step 2.4: Configure Labels

38 labels are required for the workflow. Run script to create them:

```bash
# The script has already been run and labels are created
# Verify labels exist:
gh label list --repo openwatch/openwatch

# Expected: 18 labels
# Types: bug, feature, refactor, docs, chore
# Priorities: high, medium, low
# Status: backlog, in-progress, in-review, done
# On-Hold, Question, Critical, Blocked, etc.
```

---

## PHASE 3 — PROJECT MANAGEMENT (SCRUMBAN BOARD)

### Step 3.1: Create Project (Scrumban Board)

**Prerequisites:**
```bash
# Verify gh CLI auth has 'project' scope
gh auth refresh --scopes repo,admin:org,project

# Set org as env var
export GITHUB_ORG=openwatch
```

**Run script to create board:**

```bash
bash tools/setup_project_board.sh openwatch
# Output should show:
# ✅ OpenWatch Development Board created successfully
# URL: https://github.com/orgs/openwatch/projects/1
```

### Step 3.2: Configure Project Columns

The script creates the project but columns need manual setup in the UI.

**Via GitHub Web UI:**

1. Go to **https://github.com/orgs/openwatch/projects**
2. Click on **OpenWatch Development Board**
3. Click **⚙️ Settings** (top right)
4. Under **Customize view**, modify Status field options:

**Rename existing columns:**
- `Todo` → `Backlog`
- `In Progress` → `In Progress` (keep as-is)
- `Done` → `Done` (keep as-is)

**Add new columns (in order):**
1. Create new status option: `Ready for Analysis`
2. Create new status option: `In Review`

**Final column order:**
```
┌──────────────────┬──────────────────┬──────────────────┬──────────┬──────────┐
│ Backlog          │ Ready for        │ In Progress      │ In       │ Done     │
│                  │ Analysis         │                  │ Review   │          │
└──────────────────┴──────────────────┴──────────────────┴──────────┴──────────┘
```

### Step 3.3: Link Repository to Project

1. Go to project **Settings** → **Linked repositories**
2. Click **Add repository**
3. Select `openwatch/openwatch`
4. Grant access

### Step 3.4: Configure Project Automations

⚠️ **These must be configured via the GitHub UI (not yet automated)**

**Automation 1: New Issues → Backlog**
- Go to **Settings** → **Automations**
- **When:** Issue opened
- **Then:** Move to **Backlog**

**Automation 2: PR On Review → In Review**
- **When:** Pull request opened
- **Then:** Move to **In Review**

**Automation 3: PR Merged → Done**
- **When:** Pull request merged
- **Then:** Move to **Done** + Close linked issue

**Automation 4: PR Closed (not merged) → Return to Backlog**
- **When:** Pull request closed (without merge)
- **Then:** Move item back to **Backlog** (user can reopen)

---

## PHASE 4 — BRANCH PROTECTION RULES

### Step 4.1: Apply Branch Protection to `main`

**Prerequisites:**
- ✅ Repository is **PUBLIC** (required for free accounts)
- ✅ All CI/CD workflows are configured and passing

**Via GitHub Web UI:**

1. Go to **Settings** → **Branches**
2. Click **Add rule** under "Branch protection rules"
3. Pattern: `main`

**Configure protection settings:**

```
PULL REQUESTS:
  ✅ Require a pull request before merging
     Require approvals: 1
  ✅ Require conversation resolution before merging
  ✅ Require status checks to pass before merging
     - Require branches to be up to date before merging

RULES:
  ✅ Require linear history
  ✅ Dismiss stale pull request approvals when new commits are pushed
  ✅ Require code owner review
  ✅ Restrict who can push to matching branches

ADMIN RULES:
  ✅ Enforce all the above settings for administrators
  
DELETION & RECREATION:
  ❌ Allow deletion
  ❌ Allow force pushes
```

**Required Status Checks (from CI/CD):**
```
• Python — Public Packages & API
• Frontend — Next.js
• PR Validation / Require linked issue
• PR Validation / Conventional commit title
• PR Validation / Branch name convention
• Open-Core Boundary Enforcement
```

### Step 4.2: Verify Branch Protection via API

```bash
# Query the current protection rules
gh api repos/openwatch/openwatch/branches/main/protection

# Should return all the settings configured above
# If you get 404, protection is not yet configured
```

---

## PHASE 5 — CI/CD & AUTOMATION

### Step 5.1: GitHub Actions Workflows

Verify these workflows exist and are enabled:

```bash
# Check workflows
ls -la .github/workflows/

# Expected workflows:
# • lint.yml (Python + frontend)
# • test.yml (backend test suite)
# • build.yml (Docker images)
# • boundary-check.yml (open-core enforcement)
```

**To enable workflows:**
1. Go to **Actions** → **General**
2. Ensure: ✅ "Allow GitHub Actions to create and approve pull requests"

### Step 5.2: Required Checks Configuration

Some checks trigger PR comments that enforce the workflow:

```bash
# These checks MUST be configured in CI workflows:

# 1. PR Validation / Require linked issue
#    → Uses GitHub API to verify issue link in PR body

# 2. PR Validation / Conventional commit title
#    → Validates commit format: feat(scope): message

# 3. PR Validation / Branch name convention
#    → Validates branch format: <type>/<task-name>

# 4. Open-Core Boundary Enforcement
#    → Runs tools/check_boundaries.py to verify public/private split
```

---

## PHASE 6 — TASK EXECUTION WORKFLOW

### 🚫 CARDINAL RULE

> **NO work without an Issue. NO commits without a branch. NO merge without a PR.**

### The Complete Workflow (from Issue to Done)

#### **STEP 1: Create Issue**

**Who:** Maintainer or contributor  
**Where:** https://github.com/openwatch/openwatch/issues

**Issue template:**
```markdown
## What
[Brief description of what needs to be done]

## Why
[Business context and motivation]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests added/updated
- [ ] Documentation updated

## Type
<!-- Select one: -->
- [ ] Feature
- [ ] Bug Fix
- [ ] Refactor
- [ ] Documentation
- [ ] Chore

## Priority
<!-- Select one: -->
- [ ] High
- [ ] Medium
- [ ] Low

## Labels
<!-- Add relevant labels: e.g., 'good first issue', 'help wanted' -->
```

**Automation:** New issue → **Backlog** (automatic)

---

#### **STEP 2: Triage & Analysis**

**Who:** Maintainers  
**Action:** Review the issue

**Valid issue?**
- ✅ **YES** → Approve, move to **Ready for Analysis**
- ❌ **NO** → Close with explanation

**How to move:**
```bash
# Via GitHub UI: Drag issue card to "Ready for Analysis" column
# OR via CLI:
gh project item-set-field <project-id> <item-id> Status "Ready for Analysis"
```

---

#### **STEP 3: Create Work Branch**

**Who:** Developer

**Prerequisites:**
```bash
cd /path/to/openwatch
git checkout main
git pull origin main
```

**Branch naming convention:**
```
<type>/<task-name>

Types: feature, fix, refactor, docs, chore
Task name: lowercase, hyphens only

Examples:
  feature/user-authentication
  fix/database-connection-timeout
  docs/api-endpoint-documentation
  refactor/extract-event-handler
  chore/update-dependencies
```

**Create branch:**
```bash
git checkout -b feature/task-name
# Example:
git checkout -b feature/user-authentication
```

---

#### **STEP 4: Implement Changes**

**During implementation:**
1. Follow all coding rules (see `.claude/rules/coding.md`)
2. Write tests as you go
3. Keep commits atomic and descriptive
4. Run checks frequently:
   ```bash
   uv run --extra test pytest -q
   cd web && npm run lint && npm run build && cd ..
   bash tools/check_boundaries.py
   ```

---

#### **STEP 5: Commit with Conventional Format**

**Commit message format:**
```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

**Example:**
```bash
git commit -m "feat(auth): add OAuth2 login support

Implements OAuth2 authentication using industry-standard libraries.
Supports GitHub, Google, and Microsoft authentication.

- Added OAuthProvider abstraction
- Implemented GitHub connector
- Added unit tests for token validation
- Updated documentation

Closes #42"
```

**Push to remote:**
```bash
git push origin feature/task-name
```

**Automation:** PR created → **In Progress** (if linked issue detected)

---

#### **STEP 6: Open Pull Request**

**On GitHub Web UI:**

1. Go to **https://github.com/openwatch/openwatch/compare**
2. Select:
   - **Base:** `main`
   - **Compare:** `feature/task-name`
3. Click **Create pull request**

**PR Title Format:**
```
<type>(<scope>): <description>

Examples:
feat(auth): add OAuth2 support
fix(api): handle null response in user endpoint
docs(readme): update installation instructions
```

**PR Description Template:**

```markdown
## What
[Brief description of what this PR accomplishes]

## Why
[Motivation, business context, why it's needed]

## How
Key implementation details worth highlighting.
- Decision 1: Why we chose X over Y
- Decision 2: Performance considerations

## Testing
- [x] Unit tests added/updated
- [x] Integration tests passing
- [x] Manual testing completed (if applicable)

## Checklist
- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Comments added for complex logic
- [x] Documentation updated (if needed)
- [x] No new warnings/errors
- [x] All tests pass locally

## Closes
Closes #<ISSUE_NUMBER>
```

**Critical:** Include the issue link in closing format:
```markdown
Closes #42
Fixes #43
Resolves #44
```

**Automation:**
- PR opened → **In Review** (automatic)
- CI checks run → comment with results
- Required approval → comment asking for review

---

#### **STEP 7: Code Review**

**Reviewer actions:**

```bash
# 1. Review code:
#    • Does it solve the problem?
#    • Are edge cases handled?
#    • Is it maintainable?
#    • Any security concerns?

# 2. Trigger CI:
#    • Push a comment to trigger workflow (if needed)

# 3. Approve:
#    • Approve the PR (1 required minimum)
```

**Author actions:**

If review requests changes:
```bash
git commit -am "fix: address review feedback"
git push origin feature/task-name
# Do NOT rebind — let reviewers see the conversation
```

---

#### **STEP 8: Merge to Main**

**When PR is approved AND all checks pass:**

```bash
# Option 1: Via GitHub Web UI
# Click "Squash and merge" (clean history)
# OR "Create a merge commit" (preserve branch history)

# Option 2: Via CLI
gh pr merge <PR_NUMBER> \
  --squash \
  --delete-branch \
  --auto
```

**Post-merge:**
- ✅ Branch automatically deleted (if enabled)
- ✅ Issue automatically closed
- ✅ Task moves to **Done** (automatic)

---

#### **STEP 9: Local Cleanup**

```bash
# 1. Switch back to main
git checkout main

# 2. Fetch latest
git pull origin main

# 3. Delete local branch
git branch -d feature/task-name

# 4. Verify cleanup
git branch -a
```

---

## PHASE 7 — EXAMPLE WORKFLOW (Concrete)

### Scenario: Add user authentication feature

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: CREATE ISSUE                                            │
└─────────────────────────────────────────────────────────────────┘

Title: Add OAuth2 user authentication
Type: Feature
Priority: High
Labels: frontend, security, good-first-issue

Description:
## What
Add OAuth2 authentication to the web frontend using GitHub, Google,
and Microsoft as identity providers.

## Why
Users need a secure way to log in. OAuth2 is industry standard and
reduces our security liability for password management.

## Acceptance Criteria
- [ ] OAuth2 flow implemented with 3 providers
- [ ] User session management working
- [ ] 90%+ test coverage
- [ ] API endpoint for /auth/callback secured
- [ ] Documentation updated with setup instructions

Automation: Issue created → added to Backlog

┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: TRIAGE                                                  │
└─────────────────────────────────────────────────────────────────┘

Maintainer review: ✅ Valid, high priority
Move to: Ready for Analysis

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: CREATE BRANCH                                           │
└─────────────────────────────────────────────────────────────────┘

git checkout main
git pull origin main
git checkout -b feature/oauth2-authentication

Status in board: Ready for Analysis → In Progress

┌─────────────────────────────────────────────────────────────────┐
│ STEP 4-5: IMPLEMENT & COMMIT                                    │
└─────────────────────────────────────────────────────────────────┘

# Create files, write tests...
# Run checks:
uv run --extra test pytest -q
cd web && npm run lint && npm run build && cd ..

# Commit atomically:
git commit -m "feat(auth): add OAuth2 provider abstraction

- Created OAuthProvider interface
- Added token validation logic
- Added unit tests

Closes #99"

git commit -m "feat(auth): implement GitHub OAuth2 connector

- Integrated GitHub OAuth2 endpoint
- Added callback handler
- Added integration tests

Related: #99"

git push origin feature/oauth2-authentication

┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: OPEN PR                                                 │
└─────────────────────────────────────────────────────────────────┘

Title: feat(auth): add OAuth2 authentication

Description:
## What
Added OAuth2 authentication with GitHub, Google, and Microsoft
identity providers.

## Why
Secure user login without managing passwords directly.

## How
- Provider abstraction for pluggable OAuth2 connectors
- Session management via secure cookies
- Test coverage: 94%

## Checklist
- [x] Tests pass
- [x] Boundary check passes
- [x] Documentation updated

Closes #99

Automation:
- PR created → linked to issue #99 → moved to In Review
- CI checks triggered → Results posted as PR comment

┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: CODE REVIEW                                             │
└─────────────────────────────────────────────────────────────────┘

Reviewer comment: "Please expand session timeout tests"

Author fixes:
git commit -m "test(auth): add session timeout coverage

- Added tests for 30-min idle timeout
- Added tests for max session duration
- Verified cleanup on timeout"

git push origin feature/oauth2-authentication

Reviewer: ✅ Approved

┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: MERGE                                                   │
└─────────────────────────────────────────────────────────────────┘

Click: "Squash and merge" + "Delete branch"

Result:
- Branch deleted automatically
- Issue #99 closed automatically
- Task moved to Done automatically

┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: CLEANUP                                                 │
└─────────────────────────────────────────────────────────────────┘

git checkout main
git pull origin main
git branch -d feature/oauth2-authentication

✅ Complete. Issue → Done. Next task!
```

---

## PHASE 8 — ENFORCEMENT & RULES

### Hard Rules (Enforced by Configuration)

```
❌ NO direct commits to main
   → Branch protection prevents pushes to main

❌ NO merge without PR
   → Branch protection requires PR

❌ NO merge without approval
   → Branch protection requires 1 approval

❌ NO merge without passing CI
   → Status checks required

❌ NO merge without resolved conversations
   → Conversation resolution required

❌ NO stale branches
   → Auto-delete after merge enabled
```

### Soft Rules (Enforced by PR Comments)

These are checked by GitHub Actions and commented on every PR:

```
⚠️  Missing issue link
    → "Please add 'Closes #123' to PR body"

⚠️  Non-conventional commit
    → "PR title should follow: <type>(<scope>): <message>"

⚠️  Bad branch name
    → "Branch should be: <type>/<task-name>"

⚠️  Boundary violation
    → "This change violates open-core boundary"
```

---

## PHASE 9 — MAINTENANCE & OPERATIONS

### Weekly

```bash
# Check for stale branches
gh repo view openwatch/openwatch --web
# Settings → Branches → Check auto-delete is working

# Monitor blocked PRs
gh pr list --repo openwatch/openwatch --state open --json title,number

# Verify labels are up to date
gh label list --repo openwatch/openwatch
```

### Monthly

```bash
# Clean up old issues (auto-close after 90 days of inactivity)
gh issue list --repo openwatch/openwatch --state open

# Review and update branch protection rules
gh api repos/openwatch/openwatch/branches/main/protection

# Audit team access
gh api orgs/openwatch/teams
```

### Quarterly

```bash
# Re-validate all CI/CD checks are working
# Update documentation if workflow changes
# Review contributor onboarding feedback
```

---

## APPENDIX A — GitHub APIs Used

```bash
# Create project (V2)
gh api graphql -f query='...' mutation

# Add project field
gh api graphql -f query='...' mutation

# Create issue
gh issue create --repo openwatch/openwatch --title "..." --body "..."

# Open PR
gh pr create --repo openwatch/openwatch --base main --title "..."

# Merge PR
gh pr merge <number> --squash --delete-branch

# Apply branch protection
gh api repos/openwatch/openwatch/branches/main/protection

# Query current protection
gh api repos/openwatch/openwatch/branches/main/protection

# List labels
gh label list --repo openwatch/openwatch

# Create label
gh label create --repo openwatch/openwatch --name "bug" --color "ff0000"
```

---

## APPENDIX B — Required GitHub Scopes

When authenticating with `gh`, ensure you have these scopes:

```
✅ repo              — Full control of repositories
✅ admin:org         — Full control of organizations
✅ project           — Read/write access to projects (v2)
✅ read:user         — User profile information
✅ workflow          — Manage repository GitHub Actions workflows
```

To update scopes:
```bash
gh auth refresh --scopes repo,admin:org,project,read:user,workflow
```

---

## APPENDIX C — Troubleshooting

### Issue: Branch protection API returns 404

**Cause:** Repository is private AND you don't have GitHub Pro

**Solution:**
1. Make repository public, OR
2. Upgrade to GitHub Pro/Team, OR
3. Use GitHub Enterprise

### Issue: Project board doesn't exist

**Cause:** Token missing `project` scope

**Solution:**
```bash
gh auth refresh --scopes repo,admin:org,project
bash tools/setup_project_board.sh openwatch
```

### Issue: PR automation doesn't trigger

**Cause:** Issue link not in PR body, or PR is draft

**Solution:**
1. Ensure PR body contains "Closes #123"
2. Remove draft status: click **Ready for review**
3. Wait 30 seconds for automation to trigger

### Issue: Branch protection blocks a legitimate merge

**Cause:** PR branch is stale (behind main)

**Solution:**
```bash
# Sync branch with main
git checkout feature/task-name
git fetch origin
git rebase origin/main
git push origin feature/task-name --force-with-lease

# Then merge button will be enabled
```

---

## Sign-Off Checklist

Before considering this governance system **LIVE**, verify:

- [ ] Organization created: `openwatch`
- [ ] Repository transferred to organization
- [ ] Repository is **PUBLIC**
- [ ] All 5 OSS files present (LICENSE, README, etc.)
- [ ] GitHub features enabled (Issues, Projects, Actions)
- [ ] 18 labels created
- [ ] Scrumban project board created with 5 columns
- [ ] Branch protection configured on `main`
- [ ] All status checks configured
- [ ] Team structure defined (admins, core, contributors)
- [ ] CI/CD workflows passing
- [ ] Documentation (this file) committed to repo
- [ ] Team trained on workflow
- [ ] First issue created as test

---

## Next Steps

1. **Today:** Follow PHASE 1-2 (org setup, visibility)
2. **Tomorrow:** Follow PHASE 3-4 (project board, protection)
3. **This week:** Run test workflow with real issue
4. **Ongoing:** Monitor and refine based on team feedback

---

**Questions?** See `.claude/rules/coding.md`, `.claude/rules/testing.md`, or `CONTRIBUTING.md`

**Latest update:** April 2, 2026  
**Maintainer:** OpenWatch Platform Team
