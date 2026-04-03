# OpenWatch Wiki

Welcome to the OpenWatch project wiki.

OpenWatch is an open-source citizen auditing platform for Brazilian federal public data.

## Start Here

- [Current Status](./Current-Status)
- [Roadmap](./Roadmap)
- [Architecture](./Architecture)
- [Data Sources](./Data-Sources)
- [Typologies](./Typologies) (22 detectors)
- [Methodology](./Methodology)
- [Runbook (Local + Pipeline)](./Runbook)
- [Legal Compliance](./Legal-Compliance)
- [Contributing and Governance](./Contributing-and-Governance)
- [FAQ](./FAQ)

## Key Investigator Features

| Feature | Endpoint |
|---------|----------|
| Fuzzy entity search (companies + public servants) | `GET /public/entity/search` |
| Connection path between entities | `GET /public/graph/path` |
| Risk signal radar | `GET /public/radar` |
| Signal evidence chain | `GET /signal/{id}/provenance` |
| Data source quality status | `GET /public/sources` |

## Core Principles

- Deterministic risk detection (no black-box scoring)
- Cluster-aware entity resolution: signals follow entities through merges
- Reproducible evidence for each signal
- LGPD-by-design: CPF hashing, person search restricted to public-servant sources
- Public-interest mission with MIT license

## Canonical Repository Docs

- `README.md`
- `docs/ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CLAUDE.md`
