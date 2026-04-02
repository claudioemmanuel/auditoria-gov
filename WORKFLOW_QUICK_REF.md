# 🚀 OpenWatch Workflow — Quick Reference

## Every task starts with an Issue

```
┌──────────────────────────────┐
│  1. CREATE ISSUE             │
│  Go to: /issues/new          │
│  Fill: What, Why, Type       │
│  Board: Auto → Backlog       │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  2. APPROVE & ANALYZE        │
│  Maintainer reviews          │
│  Move to: Ready for Analysis │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  3. CREATE BRANCH            │
│  git checkout -b             │
│  <type>/<task-name>          │
│  Board: → In Progress        │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  4. CODE & COMMIT            │
│  Run tests locally           │
│  Commit atomically           │
│  Conventional format         │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  5. OPEN PR                  │
│  MUST include: Closes #123   │
│  Board: → In Review          │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  6. CODE REVIEW              │
│  ✅ Approved = 1 required    │
│  Fix feedback → push again   │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  7. MERGE                    │
│  Squash & merge              │
│  Delete branch               │
│  Issue auto-closes           │
└──────────────────────────────┘
              ↓
┌──────────────────────────────┐
│  8. DONE ✅                  │
│  Task: → Done                │
│  Issue: Closed               │
└──────────────────────────────┘
```

---

## Branch naming

```
<type>/<task-name>

✅ feature/oauth2-authentication
✅ fix/database-timeout-issue
✅ docs/api-documentation
✅ refactor/extract-event-handler
✅ chore/update-dependencies

❌ my-feature
❌ fix_bug
❌ update
```

## Commit format

```
<type>(<scope>): <message>

✅ feat(auth): add OAuth2 support
✅ fix(api): handle null response
✅ docs(readme): update setup guide
✅ chore(deps): upgrade axios

❌ fixed stuff
❌ update
❌ WIP
```

## PR title format

```
<type>(<scope>): <description>

✅ feat(sdk): implement entity search
✅ fix(api): resolve race condition
✅ docs(guide): add deployment steps
✅ refactor(ui): simplify card component

❌ add feature
❌ fix bug
❌ update
```

## Critical: How to link issue in PR

```
In PR description, you MUST add:

Closes #123
  or
Fixes #456
  or
Resolves #789

Without this, PR validation FAILS ❌
```

---

## Local workflow

```bash
# 1. Start fresh
git checkout main
git pull origin main

# 2. Create branch
git checkout -b feature/my-task

# 3. Edit & commit
git add .
git commit -m "feat(scope): message"

# 4. Pre-merge checks
uv run --extra test pytest -q
cd web && npm run lint && npm run build && cd ..
bash tools/check_boundaries.py

# 5. Push
git push origin feature/my-task

# 6. Open PR on GitHub
# Include: Closes #<issue-number>

# 7. After merge:
git checkout main
git pull origin main
git branch -d feature/my-task
```

---

## Protected branch rules

❌ Cannot push directly to `main`  
❌ Cannot merge without PR  
❌ Cannot merge without review (1 approval)  
❌ Cannot merge without passing CI  
❌ Cannot merge unresolved conversations  

---

## Required checks

These must pass before you can merge:

- Python – Public Packages & API
- Frontend – Next.js  
- PR Validation / Require linked issue
- PR Validation / Conventional commit title
- PR Validation / Branch name convention
- Open-Core Boundary Enforcement

---

## Common issues

### 🚫 "Cannot push to main"
**Fix:** Use a branch: `git checkout -b feature/...`

### 🚫 "PR validation failing"
**Check:**
- PR title follows: `<type>(<scope>): message`
- Branch name follows: `<type>/task-name`
- PR body includes: `Closes #<number>`

### 🚫 "Merge button disabled"
**Check:**
- All CI checks pass (wait for green checkmarks)
- At least 1 approval from reviewer
- Branch is up-to-date with main (`git rebase origin/main`)

### 🚫 "Boundary checker failing"
**Fix:** Don't import from protected paths in public code
- ❌ `from shared.typologies import ...` (in public layer)
- ✅ Use `CoreClient` instead

---

## Help

📖 Full guide: `docs/GITHUB_GOVERNANCE.md`  
🤝 Contribute: `CONTRIBUTING.md`  
⚡ Code rules: `.claude/rules/coding.md`  
🧪 Test rules: `.claude/rules/testing.md`  

---

## Dashboard links

Project board:  
https://github.com/orgs/openwatch/projects/1

Issues:  
https://github.com/openwatch/openwatch/issues

PRs:  
https://github.com/openwatch/openwatch/pulls

---

**Remember:** The workflow enforces best practices. Trust it. 🚀
