"""Tests for T27 — BNDES Loan-Contract Nexus typology."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from shared.models.signals import SignalSeverity
from shared.typologies.t27_bndes_loan_nexus import T27BndesLoanNexusTypology


# ── Fake ORM session infrastructure ──────────────────────────────────────────


class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, responses):
        self._q = list(responses)

    async def execute(self, *_, **__):
        return _Scalars(self._q.pop(0))


# ── Fake ORM object factories ────────────────────────────────────────────────


def _now():
    return datetime.now(timezone.utc)


def _loan_event(
    *,
    entity_id,
    days_ago=180,
    value_brl=5_000_000.0,
    uf="RJ",
):
    eid = uuid.uuid4()
    dt = _now() - timedelta(days=days_ago)
    event = SimpleNamespace(
        id=eid,
        type="financiamento_bndes",
        attrs={
            "loan_date": dt.isoformat(),
            "uf": uf,
        },
        occurred_at=dt,
        description="Financiamento BNDES",
        value_brl=value_brl,
    )
    participant = SimpleNamespace(
        id=uuid.uuid4(),
        event_id=eid,
        entity_id=entity_id,
        role="borrower",
    )
    return event, participant


def _contract_event(
    *,
    entity_id,
    days_ago=30,
    value_brl=1_000_000.0,
    uf="RJ",
):
    eid = uuid.uuid4()
    dt = _now() - timedelta(days=days_ago)
    event = SimpleNamespace(
        id=eid,
        type="contrato",
        attrs={
            "contract_date": dt.isoformat(),
            "uf": uf,
        },
        occurred_at=dt,
        value_brl=value_brl,
    )
    participant = SimpleNamespace(
        id=uuid.uuid4(),
        event_id=eid,
        entity_id=entity_id,
        role="supplier",
    )
    return event, participant


# ── Zero-result cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zero_no_loans():
    """No BNDES loans → early exit."""
    session = _FakeSession([[]])
    signals = await T27BndesLoanNexusTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_contracts():
    """Loans exist but no contracts → no signals."""
    entity_id = uuid.uuid4()
    l, lp = _loan_event(entity_id=entity_id)
    session = _FakeSession([[l], [lp], []])
    signals = await T27BndesLoanNexusTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_matching_entity():
    """Loan and contract exist for different entities → no signals."""
    loan_entity = uuid.uuid4()
    contract_entity = uuid.uuid4()
    l, lp = _loan_event(entity_id=loan_entity)
    c, cp = _contract_event(entity_id=contract_entity)
    session = _FakeSession([[l], [lp], [c], [cp]])
    signals = await T27BndesLoanNexusTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_outside_window():
    """Loan and contract > 24 months apart → no signals."""
    entity_id = uuid.uuid4()
    l, lp = _loan_event(entity_id=entity_id, days_ago=800)
    c, cp = _contract_event(entity_id=entity_id, days_ago=30)
    session = _FakeSession([[l], [lp], [c], [cp]])
    signals = await T27BndesLoanNexusTypology().run(session)
    assert signals == []


# ── Positive cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_high_within_12_months():
    """Loan and contract within 12 months → HIGH signal."""
    entity_id = uuid.uuid4()
    l, lp = _loan_event(entity_id=entity_id, days_ago=180, uf="SP")
    c, cp = _contract_event(entity_id=entity_id, days_ago=30, uf="SP")
    session = _FakeSession([[l], [lp], [c], [cp]])

    signals = await T27BndesLoanNexusTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.HIGH
    assert sig.typology_code == "T27"
    assert sig.confidence == 0.88
    assert sig.factors["same_uf"] is True
    assert sig.factors["time_between_events_days"] <= 365


@pytest.mark.asyncio
async def test_medium_within_24_months():
    """Loan and contract within 24 months but > 12 months → MEDIUM signal."""
    entity_id = uuid.uuid4()
    l, lp = _loan_event(entity_id=entity_id, days_ago=500)
    c, cp = _contract_event(entity_id=entity_id, days_ago=30)
    session = _FakeSession([[l], [lp], [c], [cp]])

    signals = await T27BndesLoanNexusTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.MEDIUM
    assert sig.confidence == 0.70
    assert sig.factors["time_between_events_days"] > 365


# ── Metadata ─────────────────────────────────────────────────────────────────


def test_t27_metadata():
    t = T27BndesLoanNexusTypology()
    assert t.id == "T27"
    assert "BNDES" in t.name or "Nexo" in t.name
    assert "financiamento_bndes" in t.required_domains
    assert "contrato" in t.required_domains
    assert t.evidence_level == "indirect"
