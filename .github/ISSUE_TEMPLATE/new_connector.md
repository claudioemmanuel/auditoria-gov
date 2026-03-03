---
name: New connector
about: Propose a new public data source connector
title: "[Connector]: "
labels: ["connector", "data-source", "needs-triage"]
assignees: []
---

## Data Source

- Official name:
- URL/API docs:
- Public or authenticated:
- Legal/license notes:

## Why this source matters

Describe anti-corruption or accountability value.

## Expected Jobs

List planned ingestion jobs (name + domain).

## Data Shape

What entities/events are expected (orgs, suppliers, contracts, payments, sanctions, etc.)?

## Access Constraints

- Rate limits:
- Pagination/cursor pattern:
- Historical range available:
- Required credentials/tokens:

## Normalization Notes

How should records map into canonical entities/events/edges?

## Acceptance Checklist

- [ ] Source is stable and officially documented
- [ ] Terms of use permit ingestion for civic auditing
- [ ] Proposed jobs are deterministic and testable
- [ ] Test plan for connector fetch + normalize exists
