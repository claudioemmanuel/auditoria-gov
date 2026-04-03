# GitHub Organization Setup — openwatch-br

This document records the governance setup for the `openwatch-br` GitHub organization
and its repositories. Steps marked **[AUTOMATED]** are handled by `tools/setup_org.sh`;
steps marked **[MANUAL]** require action in the GitHub UI.

---

## Organization: openwatch-br

| Setting | Value |
|---------|-------|
| Slug | `openwatch-br` |
| URL | https://github.com/openwatch-br |
| Display name | OpenWatch |
| Description | Deterministic citizen-auditing platform for Brazilian federal public data |
| Website | https://openwatch.dev |
| Location | Brazil |
| Default repo permission | Read |
| Members can create repos | No (admins only) |

### Logo concept [MANUAL]

Upload a custom avatar at:
https://github.com/organizations/openwatch-br/settings/profile

Suggested concept: a magnifying glass positioned over a stylized map of Brazil,
with small signal/detection dots overlaid. Dark background (charcoal or deep navy),
teal accent for the magnifying glass, white dots for signals. Minimal, geometric style.

---

## Repositories

| Repository | Visibility | License | Purpose |
|-----------|-----------|---------|---------|
| `openwatch-br/openwatch` | **Public** | MIT | Public OSS layer: portal, API gateway, SDK, connectors |
| `openwatch-br/openwatch-core` | **Private** | BSL 1.1 | Protected core: typologies, analytics, pipelines, infra |

---

## Automated Setup

Run once after creating the organization:

```bash
# Authenticate with required scopes
gh auth login --scopes repo,admin:org,delete_repo

# Preview (no changes made)
bash tools/setup_org.sh --dry-run

# Execute
export GITHUB_USER=claudioemmanuel
bash tools/setup_org.sh
```

This script handles:
1. Org profile configuration (description, website, location)
2. Member privilege settings (read-only, no self-service repo creation)
3. Repository transfer (`claudioemmanuel/openwatch` → `openwatch-br/openwatch`)
4. Collaborator + owner assignment
5. Private core repo creation (`openwatch-br/openwatch-core`)
6. Branch protection on both repos
7. Label setup on `openwatch-br/openwatch`

---

## Repository Transfer Details

The transfer command (executed by `setup_org.sh`):
```bash
gh api repos/claudioemmanuel/openwatch/transfer \
  --method POST \
  -f new_owner=openwatch-br \
  -f new_name=openwatch
```

**Post-transfer checklist [MANUAL]:**

- [ ] Re-add CI secrets (not transferred automatically):
  - `PORTAL_TRANSPARENCIA_TOKEN`
  - `DATAJUD_API_KEY` (optional)
  - `INTERNAL_API_KEY`
  - `CPF_HASH_SALT`
  - `CORE_CI_ENABLED` (optional, gates private CI job)
  - `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (optional)
  - `CORE_SERVICE_URL` + `CORE_API_KEY` (post-split production)
  
  Settings URL: https://github.com/openwatch-br/openwatch/settings/secrets/actions

- [ ] Re-add deploy keys (revoked on transfer):
  Settings URL: https://github.com/openwatch-br/openwatch/settings/keys

- [ ] Update webhook payload URLs from `claudioemmanuel/openwatch` → `openwatch-br/openwatch`:
  Settings URL: https://github.com/openwatch-br/openwatch/settings/hooks

- [ ] Update Vercel project to point to `openwatch-br/openwatch`:
  https://vercel.com/dashboard → project → Settings → Git

---

## Branch Protection — `openwatch-br/openwatch` (public)

Applied by `setup_org.sh`. Full enforcement on public Free-plan repo.

| Rule | Status |
|------|--------|
| Required status checks (strict) | ✅ Enforced (public repo on Free) |
| Required PR reviews (1 approval) | ✅ Enforced |
| CODEOWNERS enforcement | ✅ Enforced |
| Require last-push approval | ✅ Enforced |
| Linear history | ✅ Enforced |
| No force pushes | ✅ Enforced |
| No branch deletions | ✅ Enforced |
| Required conversation resolution | ✅ Enforced |
| Stale review dismissal | ✅ Enforced |
| Enforce for admins | ✅ Enforced |

### Required status checks

```json
[
  "Python — Public Packages & API",
  "Frontend — Next.js",
  "PR Validation / Require linked issue",
  "PR Validation / Conventional commit title",
  "PR Validation / Branch name convention",
  "Open-Core Boundary Enforcement"
]
```

---

## Branch Protection — `openwatch-br/openwatch-core` (private)

On Free plan, private repo protection is **advisory only** (not enforced).
The following settings are applied but enforcement depends on voluntary compliance.

| Rule | Setting |
|------|---------|
| Required PR reviews (1 approval) | Set (advisory) |
| Linear history | Set (enforced) |
| No force pushes | Set (enforced) |
| No branch deletions | Set (enforced) |

---

## CODEOWNERS

The `openwatch-br/openwatch` repo uses `.github/CODEOWNERS` to require
`@claudioemmanuel` review on all PRs. Key rules:

```
*                          @claudioemmanuel
packages/connectors/       @claudioemmanuel
apps/api/                  @claudioemmanuel
.github/                   @claudioemmanuel
```

---

## Repository Split

To physically separate the monorepo into the two repositories:

```bash
# 1. Pre-flight
bash tools/split_repo_preflight.sh

# 2. Dry run
export GITHUB_TOKEN=$(gh auth token)
export GITHUB_OWNER=openwatch-br
bash tools/split_repo.sh --dry-run

# 3. Execute (irreversible — backup first)
cp -r . ../openwatch.backup
bash tools/split_repo.sh
```

See `tools/split_repo.sh` for the full protected-paths list and step-by-step logic.
