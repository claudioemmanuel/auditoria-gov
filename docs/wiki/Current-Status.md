# Current Status

Last updated: 2026-03-04

## Product Scope

- Public read-only web experience (no login required)
- FastAPI API + Celery workers + PostgreSQL + Next.js
- 10 connector modules ingesting 11 public source streams
- 18 deterministic typology detectors (T01-T18)

## Engineering Status

- CI enabled and passing on `main`
- OSS governance baseline completed:
  - AGPL-3.0 license
  - Contributor covenant code of conduct
  - Contributing and security policies
  - Issue and PR templates
  - Contributor guidance for Claude Code

## Operational Status

- Full local stack available with Docker Compose
- Scheduled processing pipeline configured via Celery Beat
- Optional LLM explanation layer with deterministic fallback

## Known Limits

- Some data sources require tokens and/or large local datasets
- Wiki git endpoint may require manual first-page initialization in GitHub UI before direct `.wiki.git` sync
