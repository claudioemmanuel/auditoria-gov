# GitHub Organization & Repository Governance Setup

This document contains the manual steps required to fully configure the OpenWatch GitHub organization and enforce the production-grade governance model. Steps marked **[AUTOMATED]** are handled by CI; steps marked **[MANUAL]** require one-time action in the GitHub UI or CLI.

---

## Phase 1 — Organization Setup [MANUAL]

### 1.1 Create the Organization

1. Go to: https://github.com/organizations/new
2. Fill in:
   - **Organization name**: `openwatch-br` (or `openwatch` if available)
   - **Contact email**: your email
   - **Plan**: Free

### 1.2 Configure Organization Profile

Navigate to **Organization Settings → Profile**:

| Field | Value |
|-------|-------|
| Display name | OpenWatch |
| Description | Deterministic citizen-auditing platform for Brazilian public data |
| URL | https://openwatch.dev (or your domain) |
| Twitter | (if applicable) |
| Location | Brazil |

Enable under **Settings → Member privileges**:
- Allow members to create repositories: ✅
- Allow forking of private repos: ❌

### 1.3 Transfer Repository

1. Go to current repo: **Settings → Danger Zone → Transfer**
2. Transfer to the new organization
3. Verify:
   - Default branch remains `main`
   - All collaborators are re-invited
   - CI secrets are re-configured (they are NOT transferred)

**CLI alternative:**
```bash
gh api repos/claudioemmanuel/openwatch/transfer \
  --method POST \
  -f new_owner=openwatch-br
```

---

## Phase 2 — Repository Configuration [MANUAL + AUTOMATED]

### 2.1 Verify Open Source Files [AUTOMATED]

These files already exist in the repo:

| File | Status |
|------|--------|
| `LICENSE` (AGPLv3 → should be MIT) | ⚠️ Update to MIT for public layer |
| `LICENSE-BSL` | ✅ Created |
| `README.md` | ✅ Exists |
| `CONTRIBUTING.md` | ✅ Updated |
| `CODE_OF_CONDUCT.md` | ✅ Exists |
| `SECURITY.md` | ✅ Exists |

### 2.2 Update LICENSE to MIT [MANUAL]

The current `LICENSE` is AGPLv3. For the public open-core layer, replace with MIT:

```bash
gh api repos/openwatch-br/openwatch/contents/LICENSE \
  --method PUT \
  -f message="chore: update public repo license to MIT" \
  -f content="$(base64 -w0 MIT-LICENSE-TEXT)"
```

Or update via GitHub UI: **Repository → LICENSE → Edit**.

MIT license text: https://opensource.org/licenses/MIT

### 2.3 Enable GitHub Features [MANUAL]

Navigate to **Settings → General**:

- [x] Issues — ✅ Enable
- [x] Projects — ✅ Enable
- [x] Discussions — ✅ Enable (optional)
- [x] Actions — ✅ Enable (already in use)
- [x] **Auto-delete head branches** — ✅ **MUST enable**
- [x] **Allow squash merging** — ✅ Enable
- [x] Allow merge commits — ❌ Disable (squash only)
- [x] Allow rebase merging — ❌ Disable (squash only)

---

## Phase 3 — Branch Protection [MANUAL — CRITICAL]

Navigate to: **Settings → Branches → Add rule** for `main`:

### Rule: `main`

| Setting | Value |
|---------|-------|
| Require a pull request before merging | ✅ |
| Required approvals | **1** |
| Dismiss stale reviews when new commits are pushed | ✅ |
| Require review from Code Owners | ✅ |
| Require status checks to pass | ✅ |
| Require branches to be up to date | ✅ |
| Required status checks | `Python — Public Packages & API`, `Frontend — Next.js`, `PR Validation / Require linked issue`, `PR Validation / Conventional commit title`, `PR Validation / Branch name convention` |
| Require conversation resolution | ✅ |
| Restrict pushes to matching branches | ✅ (only `@claudioemmanuel`) |
| Allow force pushes | ❌ |
| Allow deletions | ❌ |

**CLI equivalent (after org transfer):**
```bash
gh api repos/openwatch-br/openwatch/branches/main/protection \
  --method PUT \
  --input branch-protection.json
```

See `docs/branch-protection.json` for the full ruleset payload.

---

## Phase 4 — Labels Setup [MANUAL via CLI]

Run once to configure the full label set:

```bash
# Core workflow labels
gh label create "needs-triage"     --color "FFA500" --description "New — awaiting analysis"
gh label create "ready"            --color "0075CA" --description "Triaged and ready to start"
gh label create "in-progress"      --color "FBCA04" --description "Actively being worked on"
gh label create "in-review"        --color "E4E669" --description "PR open, awaiting review"
gh label create "blocked"          --color "B60205" --description "Blocked on external dependency"
gh label create "stale"            --color "CCCCCC" --description "No activity for 30 days"
gh label create "security"         --color "B60205" --description "Security-related"

# Type labels
gh label create "bug"              --color "D73A4A" --description "Something is broken"
gh label create "enhancement"      --color "A2EEEF" --description "New feature or improvement"
gh label create "refactor"         --color "6F42C1" --description "Code quality improvement"
gh label create "documentation"    --color "0075CA" --description "Documentation change"
gh label create "chore"            --color "E4E669" --description "Maintenance / tooling"
gh label create "ci"               --color "F9D0C4" --description "CI/CD changes"

# Priority labels
gh label create "priority: high"   --color "B60205" --description "High priority"
gh label create "priority: medium" --color "FBCA04" --description "Medium priority"
gh label create "priority: low"    --color "0E8A16" --description "Low priority"

# Scope labels
gh label create "scope: frontend"  --color "BFD4F2" --description "web/ changes"
gh label create "scope: api"       --color "D4C5F9" --description "api/ changes"
gh label create "scope: sdk"       --color "C2E0C6" --description "packages/sdk changes"
gh label create "scope: connector" --color "F9D0C4" --description "Public connector changes"
gh label create "scope: docs"      --color "E4E669" --description "Documentation changes"
gh label create "scope: core"      --color "B60205" --description "Protected core (internal only)"
```

---

## Phase 5 — Project Board (Scrumban) [MANUAL]

GitHub Projects v2 must be created via UI (GraphQL API requires elevated scope).

### 5.1 Create the Project

1. Go to: **Organization → Projects → New project**
2. Select: **Board** layout
3. Name: `OpenWatch Development Board`

### 5.2 Configure Columns

| Column | Meaning |
|--------|---------|
| **Backlog** | All new issues land here |
| **Ready for Analysis** | Triaged, approved to work on |
| **In Progress** | Branch created, work underway |
| **In Review** | PR open |
| **Done** | PR merged, issue closed |

### 5.3 Add Custom Fields

| Field | Type | Options |
|-------|------|---------|
| Priority | Single select | 🔴 High, 🟡 Medium, 🟢 Low |
| Type | Single select | Bug, Feature, Refactor, Docs, Chore |
| Sprint | Iteration | 2-week sprints |

### 5.4 Configure Automation Rules

In **Project Settings → Workflows**, enable:

| Trigger | Action |
|---------|--------|
| Item added to project | Set status → Backlog |
| Pull request opened | Set status → In Review |
| Pull request merged | Set status → Done |
| Issue closed | Set status → Done |

---

## Phase 6 — CI Secrets [MANUAL]

After org transfer, re-add secrets under **Organization Settings → Secrets → Actions**:

| Secret | Description |
|--------|-------------|
| `CORE_CI_ENABLED` | Set to `1` to enable core CI (only for internal runners) |
| `DEPLOY_ECR_ROLE` | AWS IAM role ARN for ECR push (GitHub OIDC) |
| `DEPLOY_ECS_ROLE` | AWS IAM role ARN for ECS deploy |
| `CLOUDFRONT_DISTRIBUTION_ID` | For frontend deploy |

---

## Enforcement Summary

| Rule | Method | Status |
|------|--------|--------|
| No direct push to main | Branch protection | [MANUAL] |
| PR requires 1 approval | Branch protection | [MANUAL] |
| CI must pass before merge | Branch protection + status checks | [MANUAL] |
| PR must link to an issue | `pr-validation.yml` | ✅ [AUTOMATED] |
| Conventional commit titles | `pr-validation.yml` | ✅ [AUTOMATED] |
| Branch naming convention | `pr-validation.yml` | ✅ [AUTOMATED] |
| No protected imports in public layer | `boundary-check.yml` | ✅ [AUTOMATED] |
| Stale issues closed after 37 days | `stale.yml` | ✅ [AUTOMATED] |
| Stale PRs closed after 21 days | `stale.yml` | ✅ [AUTOMATED] |
| Code owner approval on protected paths | `CODEOWNERS` | ✅ [AUTOMATED] |
| Auto-delete merged branches | Repo setting | [MANUAL] |

---

## Example Full Pipeline (Issue → Done)

```
1. Create issue using template: "feat(sdk): add entity search method"
   → Auto-labeled: needs-triage
   → Added to project: Backlog

2. Triage: label as ready, remove needs-triage
   → Project: Ready for Analysis

3. Start work:
   git checkout main && git pull origin main
   git checkout -b feat/sdk-entity-search

4. Implement + commit:
   git commit -m "feat(sdk): add entity search method"
   git push origin feat/sdk-entity-search

5. Open PR:
   Title: "feat(sdk): add entity search method"
   Body: "Closes #42"
   → Project: In Review
   → pr-validation.yml passes all checks
   → CI passes

6. Review: 1 approval received

7. Merge (squash):
   → Branch auto-deleted
   → Project: Done
   → Issue auto-closed (via "Closes #42")
   → issue-pipeline.yml posts cleanup checklist
```
