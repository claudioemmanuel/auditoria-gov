# Code & Doc Templates

Starter templates for common AuditorIA Gov components.

---

## New Typology Module

### `shared/typologies/TNN/__init__.py`

```python
from shared.typologies.TNN.detector import detect_tnn

__all__ = ["detect_tnn"]
```

### `shared/typologies/TNN/detector.py`

```python
"""
T<NN>: <Typology Name>

Detection rule: <plain-language description>
Data sources: <connector names>
Window: 5 years
"""
from __future__ import annotations

import asyncpg
from shared.utils.query import execute_chunked_in


async def detect_tnn(conn: asyncpg.Connection, run_id: int) -> list[dict]:
    """
    Returns a list of signal dicts for T<NN>.
    Each dict must contain: typology_code, entity_id, evidence, score.
    """
    # TODO: implement detection logic
    return []
```

### `tests/typologies/test_tnn.py`

```python
import pytest
from shared.typologies.TNN.detector import detect_tnn


@pytest.mark.asyncio
async def test_tnn_no_signals(db_conn):
    """Zero-result case: no qualifying data."""
    result = await detect_tnn(db_conn, run_id=1)
    assert result == []


@pytest.mark.asyncio
async def test_tnn_positive(db_conn, insert_test_data):
    """Positive case: data that should trigger the typology."""
    await insert_test_data(...)
    result = await detect_tnn(db_conn, run_id=1)
    assert len(result) >= 1
    assert result[0]["typology_code"] == "T<NN>"


@pytest.mark.asyncio
async def test_tnn_boundary(db_conn, insert_test_data):
    """Boundary case: value exactly at detection threshold."""
    # Insert data at the threshold and verify behavior
    pass
```

---

## New Connector

### `shared/connectors/<name>.py`

```python
"""
Connector for <Source Name>.

Source: <URL>
Rate limit: <N req/s>
Data: <description>
"""
from __future__ import annotations

from shared.connectors.base import BaseConnector
from shared.connectors.domain_guard import domain_guard


class <Name>Connector(BaseConnector):
    BASE_URL = "https://api.example.gov.br/v1"  # must be in domain_guard whitelist

    async def fetch_page(self, page: int) -> list[dict]:
        async with domain_guard(self.BASE_URL):
            response = await self.http_client.get(
                f"{self.BASE_URL}/endpoint",
                params={"page": page, "pageSize": 100},
            )
            response.raise_for_status()
            return response.json().get("data", [])
```

---

## ADR Document

### `docs/decisions/NNN-title.md`

```markdown
# ADR-NNN: Title

**Status:** Accepted
**Date:** YYYY-MM-DD

## Context

Why this decision was needed. What problem it solves.

## Decision

What was decided, in one or two sentences.

## Consequences

**Positive:**
- ...

**Negative / Trade-offs:**
- ...

## References

- Related code: `shared/path/to/file.py`
- Related ADR: ADR-NNN
```
