# Skill: Code Review — AuditorIA Gov

## Purpose

Structured code review checklist tailored to AuditorIA Gov's architecture and guardrails.

## Checklist

### Security & Compliance

- [ ] No secrets, tokens, `.env`, or bulk datasets in the diff.
- [ ] No CPF/CNPJ logged in plaintext outside of audit-trail contexts.
- [ ] Any new outbound HTTP call passes through `shared/connectors/domain_guard.py`.
- [ ] Non-government domains have a `DomainException` with justification and review date.

### LLM Safety

- [ ] Every function calling an LLM uses `@explanatory_only` from `shared/ai/provider.py`.
- [ ] No LLM output influences risk signal creation or scoring.

### Testing

- [ ] New behavioral logic has corresponding tests in `tests/`.
- [ ] `shared/` modules maintain 100% coverage after the change.
- [ ] Typology changes include zero-result, positive, and boundary test cases.

### Data Integrity

- [ ] New typologies are registered in `shared/typologies/registry.py`.
- [ ] New connectors have a `SourceVeracityProfile` in `shared/connectors/veracity.py`.
- [ ] `docs/GOVERNANCE.md` updated for new data sources.

### Database

- [ ] No `CONCURRENTLY` inside Alembic migration functions.
- [ ] Large IN queries use `execute_chunked_in` from `shared/utils/query.py`.
- [ ] Migrations are reversible (downgrade implemented).

### Code Quality

- [ ] No `.dict()` — Pydantic v2 uses `.model_dump()`.
- [ ] Async session pattern consistent with existing code.
- [ ] PR is small and reviewable with explicit verification output.

## How to Use

When asked to review a PR or diff, work through this checklist top-to-bottom. Report each item as ✅ pass, ⚠️ warning, or ❌ fail with a file:line reference.
