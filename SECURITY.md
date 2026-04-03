# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch | ✅ Active |
| Other branches | ❌ Not supported |

We maintain security fixes only on the current `main` branch.

---

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

### Preferred method — GitHub Private Advisory

Use [GitHub's private security advisory](https://github.com/openwatch-br/openwatch/security/advisories/new)
to report a vulnerability confidentially. This keeps the report private until a fix is ready.

### Alternative — Email

If you prefer email, send details to the maintainer via the email address on
[their GitHub profile](https://github.com/claudioemmanuel).

---

## What to Include

Please include as much of the following as possible:

- **Type of vulnerability** (e.g., SSRF, injection, authentication bypass, data exposure)
- **Affected component** (file path or endpoint)
- **Steps to reproduce** (proof-of-concept code or request/response samples)
- **Potential impact** (data exposure scope, privilege escalation path, etc.)
- **Suggested fix** (if you have one)

---

## Response Timeline

| Stage | Target time |
|-------|------------|
| Initial acknowledgment | Within 48 hours |
| Vulnerability assessment | Within 5 business days |
| Fix developed and reviewed | Within 14 days (critical) / 30 days (other) |
| Coordinated disclosure | After fix is deployed |

We will keep you informed throughout the process and give credit in the release notes
(unless you prefer to remain anonymous).

---

## Scope

This policy covers:

- The `openwatch-br/openwatch` repository (public OSS layer)
- Any API endpoints served at the production URL

Out of scope:

- `openwatch-br/openwatch-core` (private core — report directly to maintainer)
- Third-party services and APIs consumed by OpenWatch (report to those vendors)
- Denial-of-service against rate-limited public endpoints
- Social engineering

---

## Safe Harbor

We consider security research conducted in good faith, following this policy, to be
authorized. We will not pursue legal action against researchers who:

- Avoid accessing or modifying data belonging to others
- Do not perform actions that degrade service availability
- Disclose findings privately before public disclosure
- Act within the scope defined above

---

## Acknowledgments

We thank all researchers who responsibly disclose vulnerabilities to us.
Credited disclosures will appear in the relevant release's changelog.
