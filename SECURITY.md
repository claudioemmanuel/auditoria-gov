# Security Policy

## Scope

Report security issues that could impact confidentiality, integrity, availability, or user safety, including:

- Authentication/authorization bypass (if introduced in future private/admin surfaces)
- Remote code execution, command injection, SQL injection
- Sensitive data exposure (tokens, raw personal identifiers, internal secrets)
- LGPD-related privacy failures (for example storing raw CPF where hashing is expected)
- Supply-chain compromise risks in dependencies or build pipeline

Out-of-scope by default:

- Requests for support or setup help
- Non-security code style issues
- Theoretical concerns without a reproducible scenario

## Responsible Disclosure

Please report vulnerabilities privately through GitHub Security Advisories:

- https://github.com/claudioemmanuel/auditoria-gov/security/advisories/new

If private advisories are unavailable, open a minimal public issue asking for a private contact channel and **do not** include exploit details.

## What to Include in a Report

- Affected component/file/path
- Clear reproduction steps (or proof of concept)
- Impact assessment and attack preconditions
- Suggested remediation (if available)
- Whether you believe the issue is already being exploited

## Response Timeline (Targets)

- Acknowledgement: within 72 hours
- Triage decision: within 14 days
- Remediation target: within 30 days for high severity, as soon as practical for critical severity

Timelines may vary for complex issues, but status updates will be shared during triage/remediation.

## Disclosure and Credit

Please allow time for a fix before public disclosure.
After remediation, coordinated disclosure and reporter attribution are welcome unless you request anonymity.
