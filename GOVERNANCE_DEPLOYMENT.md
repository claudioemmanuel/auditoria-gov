# 🚀 OpenWatch Governance — Deployment Guide

**Status:** Ready to Deploy  
**Prepared:** April 2, 2026  
**Expected Time:** 1-2 hours

---

## 🎯 Deployment Overview

This guide walks you through deploying a production-grade GitHub governance system for OpenWatch. Everything is pre-built and tested — you just need to execute the steps in order.

**What you'll have when done:**
- ✅ Professional GitHub organization
- ✅ Automated project board (Scrumban)
- ✅ Enforced branch protection on `main`
- ✅ PR validation (format, issue links, boundary checks)
- ✅ Automated issue-to-PR-to-Done workflow

---

## 📋 Step-by-Step Deployment

### STEP 1: Create GitHub Organization (5 min)

⚠️ **This cannot be reversed. Ensure organization name is correct.**

**Go to:** https://github.com/account/organizations/new

Fill in:
- **Organization name:** `openwatch` (exactly this)
- **Billing email:** Your email address
- **Organization display name:** `OpenWatch`
- **Organization description:**
  ```
  Deterministic citizen-auditing platform for Brazilian public data
  ```
- **Organization website:** (optional)
- **Public profile:** ✅ Yes

Click **Create Organization**

**Verify:**
```bash
gh api orgs/openwatch --jq '.name'
# Should output: openwatch
```

---

### STEP 2: Transfer Repository (5 min)

⚠️ **This cannot be easily reversed. The repo will be at a new URL.**

**Go to:** https://github.com/YOUR_USERNAME/openwatch/settings/options

Scroll to the bottom. Find **Transfer repository** section.

**Complete transfer:**
1. Type organization name: `openwatch`
2. Click **I understand, transfer this repository**
3. Confirm your password

The page will redirect. You should now be at:
```
https://github.com/openwatch/openwatch
```

**Verify:**
```bash
cd /path/to/openwatch

# Update git remote
git remote set-url origin https://github.com/openwatch/openwatch.git

# Verify
git remote -v
# origin  https://github.com/openwatch/openwatch.git (fetch)
# origin  https://github.com/openwatch/openwatch.git (push)

# Sync
git fetch origin
git pull origin main
```

---

### STEP 3: Make Repository PUBLIC (5 min)

**Critical:** Branch protection only works on PUBLIC repos (without GitHub Pro)

**Go to:** https://github.com/openwatch/openwatch/settings/options

Under **Danger Zone**, find **Visibility**:
- Click **Change visibility**
- Select **Public**
- Confirm

**Verify:**
```bash
gh api repos/openwatch/openwatch --jq '.private'
# Should output: false
```

---

### STEP 4: Run Governance Setup Script (10 min)

This automates most configuration:

```bash
cd /path/to/openwatch

# Verify gh CLI is authenticated with right scopes
gh auth status
# Look for: project scope

# If missing, refresh:
gh auth refresh --scopes repo,admin:org,project

# Run the setup script
bash tools/setup_github_governance.sh openwatch
```

**Expected output:**
```
✅ OpenWatch Governance Setup Complete!

Summary:
  Organization:    openwatch
  Repository:      openwatch/openwatch
  Status:          PUBLIC
  Labels:          18 configured
  Branch:          main (protected)

Next steps:
  1. Create project board: bash tools/setup_project_board.sh openwatch
  2. Configure project automation (manual)
  3. Create first test issue
```

**Verify labels were created:**
```bash
gh label list --repo openwatch/openwatch
```

---

### STEP 5: Create Project Board (5 min)

```bash
bash tools/setup_project_board.sh openwatch
```

**Expected output:**
```
✅ OpenWatch Development Board created successfully

URL: https://github.com/orgs/openwatch/projects/1

Next steps (manual in GitHub UI):
  1. Rename Status options to match Scrumban
  2. Enable automations
  3. Link repo to project
```

**Note:** Most of setup is done, but next steps need manual configuration.

---

### STEP 6: Configure Project Columns (10 min)

⚠️ Manual step in GitHub UI

**Go to:** https://github.com/orgs/openwatch/projects/1/settings

**Under "Customize view"**, find the **Status** field.

**Modify options to match Scrumban:**

Current columns (after script):
- Todo
- In Progress  
- Done

**Rename these:**
| Old | New |
|-----|-----|
| Todo | Backlog |
| In Progress | In Progress (keep) |
| Done | Done (keep) |

**Add new columns:**
1. Click **+ Add option**
   - Name: `Ready for Analysis`
   - Position: Between Backlog and In Progress
   
2. Click **+ Add option**
   - Name: `In Review`
   - Position: Between In Progress and Done

**Final column order (left-to-right):**
```
Backlog → Ready for Analysis → In Progress → In Review → Done
```

Click **Save** when done.

---

### STEP 7: Link Repository to Project (5 min)

⚠️ Manual step in GitHub UI

**Go to:** https://github.com/orgs/openwatch/projects/1/settings

Find **"Linked repositories"** section.

Click **+ Add repository**

Select `openwatch/openwatch` from dropdown.

Click **Link repository**

---

### STEP 8: Enable Project Automations (10 min)

⚠️ Manual step in GitHub UI

**Go to:** https://github.com/orgs/openwatch/projects/1/settings

Find **"Automations"** section (or click **Automations** on project board).

**Create Automation 1: Issue Opened → Backlog**
- **When:** Issue opened
- **Then:** Add to **Backlog** column

**Create Automation 2: PR Opened → In Review**
- **When:** Pull request opened
- **Then:** Add to **In Review** column

**Create Automation 3: PR Merged → Done**
- **When:** Pull request merged
- **Then:** Add to **Done** column + Auto-close issue

**Create Automation 4: PR Closed (not merged) → Backlog**
- **When:** Pull request closed (without merge)
- **Then:** Move back to **Backlog**

Save all automations.

---

### STEP 9: Verify Everything (10 min)

Run these verification commands:

```bash
# 1. Check organization exists
gh api orgs/openwatch

# 2. Check repo is public
gh api repos/openwatch/openwatch --jq '.private'
# Should output: false

# 3. Check labels (should be ~18)
gh label list --repo openwatch/openwatch | wc -l

# 4. Check branch protection
gh api repos/openwatch/openwatch/branches/main/protection

# 5. Check project board exists
gh api graphql -f query='
query {
  organization(login: "openwatch") {
    projectV2(number: 1) {
      title
    }
  }
}
'
# Should show: "OpenWatch Development Board"

# 6. Verify boundary checker works
bash tools/check_boundaries.py
# Should output: 0 violations found
```

---

### STEP 10: Train Team (30 min)

Have everyone on the team read the documentation:

**All team members:**
- [ ] Read: `WORKFLOW_QUICK_REF.md` (10 min)
- [ ] Skim: `docs/GITHUB_GOVERNANCE.md` (30 min)

**Developers:**
- [ ] Read: `.claude/rules/coding.md` (30 min)
- [ ] Read: `.claude/rules/testing.md` (20 min)
- [ ] Run: `bash tools/dev_setup.sh` (5 min)

**Maintainers:**
- [ ] Read: `docs/GOVERNANCE_CHECKLIST.md` (30 min)

---

### STEP 11: Test the Workflow (30 min)

Create a real test to verify everything works:

**1. Create a test issue:**

Go to: https://github.com/openwatch/openwatch/issues/new

```
Title: Test Workflow — Update README
Body:
## What
Add a test entry to the README to verify the workflow.

## Why
Testing that the governance automation works end-to-end.

## Acceptance Criteria
- [ ] Update README with test entry
- [ ] PR passed validation
- [ ] PR merged successfully
- [ ] Issue auto-closed
- [ ] Task moved to Done

Type: Docs
Priority: Low
```

Click **Create issue**

**Project board:** Issue should appear in **Backlog**

---

**2. Create a test branch and PR:**

```bash
cd /path/to/openwatch

git checkout main
git pull origin main

git checkout -b docs/test-workflow

echo "" >> README.md
echo "## Test Entry — Governance Validation" >> README.md
echo "Timestamp: $(date)" >> README.md

git add README.md
git commit -m "docs: add test entry to README

Add a test entry to verify the governance workflow automation.

Closes #<ISSUE_NUMBER>"
# IMPORTANT: Replace <ISSUE_NUMBER> with the actual issue number

git push origin docs/test-workflow
```

**Go to GitHub:** https://github.com/openwatch/openwatch

Click **Compare & pull request** that appeared.

**PR title should auto-populate.** If not, manually enter:
```
docs: add test entry to README
```

**PR body:** Add if not present:
```
## What
Add a test entry to verify workflow.

## Why
Testing governance automation.

Closes #<ISSUE_NUMBER>
```

Click **Create pull request**

---

**3. Observe the automation:**

**In PR:**
- [ ] CI checks start running (watch for checkmarks)
- [ ] Should show: "PR Validation / Require linked issue" ✅
- [ ] Should show: "PR Validation / Conventional commit title" ✅
- [ ] Should show: "PR Validation / Branch name convention" ✅
- [ ] Should show: "Open-Core Boundary Enforcement" ✅

**In Project Board:**
- [ ] Test issue should move to **In Review** ✓

---

**4. Approve and merge:**

(As an admin/reviewer)

Go to PR, click **Approve** → **Approve**

Then scroll to merge button and click **Squash and merge**

Check: ✅ **Delete head branch**

Click **Confirm squash and merge**

---

**5. Verify auto-automation:**

The system should automatically:
- ✅ Delete the branch (after merge)
- ✅ Close the issue #<ISSUE_NUMBER>
- ✅ Move task to **Done** on project board

**Verify locally:**
```bash
git checkout main
git pull origin main
git branch -a
# Your branch should NOT be listed (auto-deleted)

# Verify issue closed
gh issue view <ISSUE_NUMBER> --repo openwatch/openwatch --jq '.state'
# Should output: CLOSED
```

---

## ✅ Deployment Complete!

When you've completed all 11 steps, your governance system is LIVE.

**What you now have:**

```
✅ Professional GitHub Organization (openwatch)
✅ Public Repository (openwatch/openwatch)
✅ 18 Labels (type, priority, status, etc.)
✅ Scrumban Project Board (5 columns)
✅ Branch Protection on main (enforced)
✅ PR Validation Automation (format, links, boundary)
✅ Auto-Workflow (issue → backlog → review → done)
✅ Developer Onboarding Tools (dev_setup.sh)
✅ Complete Documentation (GOVERNANCE*.md)
```

---

## 🆘 Troubleshooting

### Q: The setup script says "branch protection may not be available"

**A:** This is okay on free tier. It means you don't have the exact check names yet.

**Fix:** Create a test PR and see if protection works. If not, you may need GitHub Pro.

---

### Q: Project automations won't save

**A:** Try refreshing the page and trying again. GitHub UI can be quirky.

---

### Q: PR validation checks not showing up

**A:** They may take 30-60 seconds to appear. Refresh the PR page.

---

### Q: "Cannot push to main" error

**A:** **PERFECT!** That means branch protection is working. Use a branch instead:

```bash
git checkout -b feature/your-task
git push origin feature/your-task
# Then open a PR
```

---

### Q: Test issue didn't appear in project board

**A:** The automation might not have triggered. Try:

1. Refresh project board page
2. Click **⚙️ Settings** → Scroll to automations
3. Verify automations are enabled

---

## 📚 Documentation Reference

- **Complete guide:** `docs/GITHUB_GOVERNANCE.md`
- **Implementation checklist:** `docs/GOVERNANCE_CHECKLIST.md`
- **Quick reference:** `WORKFLOW_QUICK_REF.md`
- **Setup summary:** `docs/GOVERNANCE_SETUP_SUMMARY.md`
- **Contribution guide:** `CONTRIBUTING.md`
- **Code rules:** `.claude/rules/coding.md`
- **Test rules:** `.claude/rules/testing.md`

---

## 🎯 Next Steps (After Deployment)

Once deployment is complete:

1. **Onboard team** (1 day)
   - Everyone reads documentation
   - Team creates test PRs
   - Verify everyone understands workflow

2. **Monitor & refine** (1 week)
   - Watch for edge cases
   - Collect team feedback
   - Update docs if needed

3. **Track metrics** (ongoing)
   - PR approval time
   - Test coverage
   - Issue velocity

4. **Plan repo split** (1 month)
   - Use: `bash tools/split_repo.sh --dry-run`
   - Create private `openwatch-core` repo
   - Execute split when ready

---

## 🚀 You're Ready!

Navigate to Step 1 and begin deployment. The system is bulletproof — follow the steps and you'll have a world-class open source workflow.

**Questions?** See `docs/GITHUB_GOVERNANCE.md`

**Getting stuck?** Check the Troubleshooting section or re-read the relevant step.

**Ready?** Let's go! 🚀

---

**Deployment started:** ___________  
**Deployment completed:** ___________  
**Team trained:** ___________  
**First test PR merged:** ___________  

✅ **LIVE!**
