# Reusable Prompt Templates

Copy-paste prompts for common OpenWatch development tasks.

---

## New Typology

```
Implement typology T<NN>: <name>.

Detection rule: <describe the pattern in plain language>
Relevant data: <connector/event type, e.g., licitacao + contrato>
Signal threshold: <e.g., same supplier wins >3 contracts in 30 days for same CNPJ>

Follow the pattern in shared/typologies/T03/ (splitting detection).
Register in shared/typologies/registry.py.
Add tests: zero-result, positive, and boundary cases in tests/typologies/test_t<NN>.py.
Use 5-year windows for all event queries.
Use execute_chunked_in from shared/utils/query.py for large IN queries.
```

---

## New Connector

```
Implement a new connector for <source name>.

Source URL: <base URL>
Data type: <e.g., procurement notices, contracts>
Rate limit: <e.g., 10 req/s>

Follow the pattern in shared/connectors/pncp.py.
Add a SourceVeracityProfile in shared/connectors/veracity.py.
Update shared/connectors/__init__.py.
Update docs/GOVERNANCE.md with the new source.
All HTTP must go through shared/connectors/domain_guard.py.
Add tests in tests/connectors/test_<name>.py using respx for HTTP mocking.
```

---

## New API Endpoint

```
Add a public API endpoint: GET /api/v1/<path>

Purpose: <describe what data it returns>
Filters: <e.g., entity_id, date_range, limit, offset>

Follow the pattern in api/app/routers/public.py.
Add the repository query in shared/repo/queries.py.
Return paginated results using the existing PaginatedResponse model.
Apply entity cluster resolution via resolve_entity_ids_with_clusters where entity_id filtering is involved.
```

---

## Debug a Typology (No Signals)

```
Typology T<NN> is producing zero signals. Help me debug.

Current data in DB:
- <event type>: <count> events, date range <start> to <end>
- <other relevant tables>

The typology logic is in shared/typologies/T<NN>/.
Check: window size, asyncpg param limits, data availability vs expected date range.
```

---

## Code Review Request

```
Please review this diff using the .claude/skills/review/SKILL.md checklist.

Focus areas: <e.g., security, test coverage, LLM safety>
Context: <what this change does>
```
