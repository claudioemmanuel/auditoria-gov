# Copilot CLI Model Auto-Rotation Usage Policy

This file configures automatic model selection for GitHub Copilot CLI sessions in this repository.

## Model Tier Reference

| Tier | Model | Use Case |
|------|-------|----------|
| 0 | GPT-5 mini | Triage, small fixes, reading code |
| 1 | GPT-5.4 mini | Standard implementation, tests, small refactors |
| 2 | Claude Sonnet 4.6 | Complex logic, architecture, code reviews |
| 3 | GPT-5.4 | Pipelines, deep debugging, performance |
| 4 | Claude Opus 4.6 | Last resort only |

## Selection Guidelines

**Tier 0 — GPT-5 mini**
Use for: reading files, quick triage, answering "what does this do?", one-line fixes, navigating the codebase.

**Tier 1 — GPT-5.4 mini**
Use for: standard feature implementation, writing tests, small-to-medium refactors, updating docs.
This is the default tier for most day-to-day coding tasks.

**Tier 2 — Claude Sonnet 4.6**
Use for: complex business logic, architectural decisions, multi-file refactors, pull request code reviews, security analysis.

**Tier 3 — GPT-5.4**
Use for: CI/CD pipeline design, deep debugging of performance or concurrency issues, large-scale migrations.

**Tier 4 — Claude Opus 4.6**
Use as a last resort only when lower tiers have failed or the task requires maximal reasoning depth.
Always prefer Tier 2 or 3 first.

## Auto-Rotation Rules

1. Start at Tier 1 for any new task.
2. Escalate one tier at a time if the response is incomplete, incorrect, or the task complexity warrants it.
3. Never skip tiers without justification.
4. De-escalate to a lower tier for follow-up tasks that are simpler.
5. Tier 4 requires explicit justification before use.

## OpenWatch-Specific Notes

- Typology logic and risk signal scoring must never be influenced by LLM output — use `@explanatory_only`.
- All outbound HTTP must go through `shared/connectors/domain_guard.py`.
- 100% test coverage is enforced for `shared/` — always verify with `uv run --extra test pytest -q`.
