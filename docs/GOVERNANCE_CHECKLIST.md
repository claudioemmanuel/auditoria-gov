# OpenWatch Governance — Implementation Checklist

**Start Date:** April 2, 2026  
**Status:** Ready for Implementation

---

## PHASE 1: Organization & Repository Setup

### 1.1 Create GitHub Organization ✓ REQUIRED

- [ ] Go to https://github.com/account/organizations/new  
- [ ] Organization name: `openwatch`  
- [ ] Billing email: Your email  
- [ ] Display name: `OpenWatch`  
- [ ] Description: `Deterministic citizen-auditing platform for Brazilian public data`  
- [ ] Public profile: ✅ Checked  

**Verification:**
```bash
gh api orgs/openwatch
# Should return org details
```

---

### 1.2 Transfer Repository to Organization ✓ REQUIRED

- [ ] Go to your repo: https://github.com/YOUR_USERNAME/openwatch/settings/general
- [ ] Scroll to **Transfer**
- [ ] Enter organization: `openwatch`
- [ ] Confirm transfer

**Verification:**
```bash
git remote set-url origin https://github.com/openwatch/openwatch.git
git remote -v
# Should show: origin https://github.com/openwatch/openwatch.git
```

---

### 1.3 Make Repository PUBLIC ✓ REQUIRED

⚠️ **CRITICAL:** Branch protection rules only work on PUBLIC repos (without GitHub Pro)

- [ ] Go to https://github.com/openwatch/openwatch/settings/options
- [ ] Under **Visibility**, select: **Public**
- [ ] Confirm

**Verification:**
```bash
gh api repos/openwatch/openwatch --jq '.private'
# Should output: false
```

---

### 1.4 Verify OSS Files ✓ REQUIRED

All these files must exist in repo root:

- [ ] LICENSE (MIT or Apache 2.0)
- [ ] README.md
- [ ] CONTRIBUTING.md
- [ ] CODE_OF_CONDUCT.md
- [ ] SECURITY.md

```bash
ls -la LICENSE README.md CONTRIBUTING.md CODE_OF_CONDUCT.md SECURITY.md
```

---

### 1.5 Enable GitHub Features ✓ REQUIRED

Go to https://github.com/openwatch/openwatch/settings

- [ ] **Issues** — enabled
- [ ] **Discussions** — enabled
- [ ] **Projects** — enabled
- [ ] **Actions** — enabled

---

## PHASE 2: Governance Automation

### 2.1 Create Labels ✓ REQUIRED

**Run the setup script:**
```bash
bash tools/setup_github_governance.sh openwatch
```

This creates 18 labels automatically.

**Verify:**
```bash
gh label list --repo openwatch/openwatch
# Should show ~18 labels
```

---

### 2.2 Create Project Board (Scrumban) ✓ REQUIRED

**Prerequisites:**
```bash
# Verify token has 'project' scope
gh auth status
# Should show: project scope

# If missing, refresh:
gh auth refresh --scopes repo,admin:org,project
```

**Run setup script:**
```bash
bash tools/setup_project_board.sh openwatch
```

**Expected output:**
```
✅  OpenWatch Development Board created successfully
URL: https://github.com/orgs/openwatch/projects/1
```

---

### 2.3 Configure Project Columns ⚠️ MANUAL

Go to https://github.com/orgs/openwatch/projects/1/settings

**Rename columns:**
- `Todo` → `Backlog`
- `In Progress` → `In Progress` (keep)
- `Done` → `Done` (keep)

**Add new columns:**
- Create: `Ready for Analysis` (between Backlog and In Progress)
- Create: `In Review` (between In Progress and Done)

**Final order:**
```
Backlog → Ready for Analysis → In Progress → In Review → Done
```

---

### 2.4 Link Repository to Project ⚠️ MANUAL

1. Go to: https://github.com/orgs/openwatch/projects/1/settings
2. Click **Linked repositories**
3. Click **Add repository**
4. Select `openwatch/openwatch`

---

### 2.5 Configure Project Automations ⚠️ MANUAL

Go to: https://github.com/orgs/openwatch/projects/1/settings

**Automation 1: "Issue opened"**
- When: Issue opened
- Then: Move to **Backlog**

**Automation 2: "PR opened"**
- When: Pull request opened
- Then: Move to **In Review**

**Automation 3: "PR merged"**
- When: Pull request merged
- Then: Move to **Done** and close linked issue

**Automation 4: "PR closed (not merged)"**
- When: Pull request closed (not merged)
- Then: Move back to **Backlog** (or keep in current state for re-work)

---

## PHASE 3: Branch Protection

### 3.1 Apply Branch Protection to `main` ✓ AUTOMATED

**Run setup script:**
```bash
bash tools/setup_github_governance.sh openwatch
```

This applies protection if it can. If it fails due to permissions, follow manual steps below.

---

### 3.2 Manual Branch Protection ⚠️ IF NEEDED

Go to: https://github.com/openwatch/openwatch/settings/branches

**Click: "Add rule" and enter pattern: `main`**

Configure each section:

**PULL REQUESTS:**
- ✅ Require a pull request before merging
  - Require approvals: **1**
- ✅ Require conversation resolution before merging
- ✅ Require status checks to pass before merging
  - ✅ Require branches to be up to date before merging

**RULES:**
- ✅ Require linear history
- ✅ Dismiss stale pull request approvals
- ✅ Require code owner reviews

**ADMIN OVERRIDE:**
- ✅ Enforce all settings for administrators

**DELETION:**
- ❌ Allow deletion
- ❌ Allow force pushes

---

### 3.3 Configure Required Status Checks ✓ AUTOMATED

These must match CI workflow names:

```
Required checks:
  • Python — Public Packages & API
  • Frontend — Next.js
  • PR Validation / Require linked issue
  • PR Validation / Conventional commit title
  • PR Validation / Branch name convention
  • Open-Core Boundary Enforcement
```

The setup script configures these automatically.

**Verify:**
```bash
gh api repos/openwatch/openwatch/branches/main/protection \
  --jq '.required_status_checks.contexts'

# Should list all required checks
```

---

## PHASE 4: CI/CD Workflows

### 4.1 Verify GitHub Actions Workflows ✓ AUTOMATED

These should already exist in `.github/workflows/`:

- [ ] `pr-validation.yml` — PR format checks
- [ ] `ci.yml` — Python & frontend tests
- [ ] `boundary-check.yml` — Open-core boundary enforcement
- [ ] `deploy.yml` — Deployment automation
- [ ] `issue-pipeline.yml` — Issue automation
- [ ] `stale.yml` — Close stale issues

**Verify:**
```bash
ls -la .github/workflows/
gh workflow list --repo openwatch/openwatch
```

---

### 4.2 Enable Actions ✓ AUTOMATED

Go to: https://github.com/openwatch/openwatch/settings/actions

- ✅ Actions enabled
- ✅ All workflows from this repository

---

## PHASE 5: Developer Onboarding

### 5.1 New Developer Setup

**Run dev setup script:**
```bash
bash tools/dev_setup.sh
```

This:
1. Installs Python + frontend dependencies
2. Sets up git pre-commit hooks
3. Validates local setup
4. Prints quick start guide

---

### 5.2 Documentation & Training

All team members should read:

- [ ] `docs/GITHUB_GOVERNANCE.md` — Complete workflow guide (1-2 hours)
- [ ] `CONTRIBUTING.md` — Contribution guidelines (15 min)
- [ ] `.claude/rules/coding.md` — Code standards (30 min)
- [ ] `.claude/rules/testing.md` — Test requirements (30 min)

---

### 5.3 First Test Workflow

Everyone should do this once:

```bash
# 1. Create a test issue
#    Title: "Test Issue [Your Name]"
#    Body: "This is a test of the workflow"
#    → Issue appears in Backlog

# 2. Create a test branch
git checkout -b feature/test-workflow

# 3. Make a simple change (e.g., update README)
echo "# Test" >> README.md

# 4. Commit with conventional format
git commit -m "docs: add test entry to README"

# 5. Push
git push origin feature/test-workflow

# 6. Create PR
#    → PR validation checks run
#    → If all pass, you can merge
#    → Issue moves to Done automatically

# 7. Clean up
git checkout main
git pull origin main
git branch -d feature/test-workflow
```

---

## PHASE 6: Enforcement Verification

### 6.1 Test Branch Protection

Try to push directly to main (should fail):

```bash
git checkout main
echo "test" > test.txt
git add test.txt
git commit -m "test"
git push origin main

# Expected: ERROR: branch protection prevents this
# ✅ Protection is working
```

---

### 6.2 Test PR Validation

Create a PR without issue link:

```bash
git checkout -b test/validation
echo "test" > test.txt
git add test.txt
git commit -m "test: this will fail"
git push origin test/validation

# Open PR without "Closes #" in body
# Expected: CI check fails with message about missing issue link
# ✅ Validation is working
```

Clean up:
```bash
git checkout main
git branch -D test/validation
git push origin --delete test/validation
```

---

### 6.3 Verify Boundary Checker

```bash
# Should pass with 0 violations
bash tools/check_boundaries.py

# Expected output:
# ✅ 0 violations found
# ⚠️  8 SPLIT-TODO warnings (connectors to move at split time)
```

---

## PHASE 7: Team Structure

### 7.1 Create GitHub Teams

Go to: https://github.com/orgs/openwatch/teams

Create teams:

- [ ] **core** — Maintainers (write access)
- [ ] **contributors** — Community (triage access)
- [ ] **admins** — Org owners (admin access)

---

### 7.2 Add Members

```bash
# Add current user as admin
gh api orgs/openwatch/memberships/YOUR_USERNAME \
  -X PUT \
  -f role:admin
```

---

## Completion Checklist

When all items below are ✅, the governance system is LIVE:

### Org & Repo Level
- [ ] Organization `openwatch` created
- [ ] Repository transferred to org
- [ ] Repository is PUBLIC
- [ ] All OSS files (LICENSE, README, etc.) present
- [ ] GitHub features enabled (Issues, Projects, Actions)

### Automation & Board
- [ ] 18 labels created
- [ ] Project board created (OpenWatch Development Board)
- [ ] Project columns configured (Backlog, Ready, In Progress, In Review, Done)
- [ ] Project linked to repository
- [ ] Automations configured (issue → backlog, PR → in review, etc.)

### Protection & CI/CD
- [ ] Branch protection applied to `main`
- [ ] All required status checks listed
- [ ] GitHub Actions workflows enabled
- [ ] First test PR created and merged successfully

### Team
- [ ] Teams created (core, contributors, admins)
- [ ] Members added
- [ ] Everyone has read governance docs

### Testing
- [ ] Branch push blocked (protection verified)
- [ ] PR validation checks work
- [ ] Boundary checker passes
- [ ] First real issue → PR → Done workflow completed

---

## Troubleshooting

### Issue: "Cannot set branch protection"

**Cause:** Repository is private (need GitHub Pro) or insufficient permissions

**Fix:**
1. Make repo public: Settings → Visibility → Public
2. OR upgrade to GitHub Pro
3. OR use GitHub Enterprise

---

### Issue: "gh command not found"

**Cause:** GitHub CLI not installed

**Fix:**
```bash
# macOS
brew install gh

# Windows (Chocolatey)
choco install gh

# Ubuntu/Debian
curl -fsSL https://cli.github.com/install.sh | sudo bash
```

---

### Issue: "Project board not created"

**Cause:** Token missing `project` scope

**Fix:**
```bash
gh auth refresh --scopes repo,admin:org,project
bash tools/setup_project_board.sh openwatch
```

---

### Issue: "PR validation failing wrongly"

**Cause:** PR title/branch/issue link format wrong

**Fix:**
- PR title: must be: `<type>(<scope>): message`
- Branch name: must be: `<type>/description`
- Issue link: must include: `Closes #123` or `Fixes #123`

See `docs/GITHUB_GOVERNANCE.md` for detailed examples.

---

## Timeline

**Recommended schedule:**

- **Day 1:** Phases 1-2 (org setup, labels, project board)
- **Day 2:** Phase 3-4 (branch protection, CI/CD)
- **This week:** Phase 5-6 (developer training, test workflow)
- **Ongoing:** Monitor and refine

---

## Quick Links

- Organization: https://github.com/orgs/openwatch
- Repository: https://github.com/openwatch/openwatch
- Project Board: https://github.com/orgs/openwatch/projects/1
- Branch Protection: https://github.com/openwatch/openwatch/settings/branches
- Labels: https://github.com/openwatch/openwatch/labels

---

**Questions?** See `docs/GITHUB_GOVERNANCE.md` or `CONTRIBUTING.md`

**Last updated:** April 2, 2026
