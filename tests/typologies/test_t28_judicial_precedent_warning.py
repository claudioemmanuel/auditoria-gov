"""Tests for T28 — Judicial Precedent Warning typology."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from shared.models.signals import SignalSeverity
from shared.typologies.t28_judicial_precedent_warning import (
    T28JudicialPrecedentWarningTypology,
    _normalise_tax_id,
)


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


def _ruling_event(*, cnpj="12.345.678/0001-99", tribunal="STF"):
    eid = uuid.uuid4()
    dt = _now() - timedelta(days=60)
    event = SimpleNamespace(
        id=eid,
        type="jurisprudencia",
        attrs={"tribunal": tribunal, "ementa": ""},
        occurred_at=dt,
        description=f"Acórdão sobre fraude em licitação envolvendo CNPJ {cnpj}",
        value_brl=None,
    )
    return event


def _contract_event(*, entity_id, days_ago=30, value_brl=500_000.0):
    eid = uuid.uuid4()
    dt = _now() - timedelta(days=days_ago)
    event = SimpleNamespace(
        id=eid,
        type="contrato",
        attrs={"contract_date": dt.isoformat()},
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


def _entity(*, entity_id, tax_id="12345678000199", name="Empresa Teste"):
    return SimpleNamespace(
        id=entity_id,
        tax_id=tax_id,
        name=name,
        attrs={},
    )


# ── Zero-result cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zero_no_rulings():
    """No jurisprudencia events → early exit."""
    session = _FakeSession([[]])
    signals = await T28JudicialPrecedentWarningTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_contracts():
    """Rulings exist but no contracts → no signals."""
    r = _ruling_event()
    session = _FakeSession([[r], []])
    signals = await T28JudicialPrecedentWarningTypology().run(session)
    assert signals == []


@pytest.mark.asyncio
async def test_zero_no_cnpj_in_ruling():
    """Ruling text has no CNPJ/CPF → no tax_id matches → no signals."""
    eid = uuid.uuid4()
    dt = _now() - timedelta(days=60)
    ruling = SimpleNamespace(
        id=eid,
        type="jurisprudencia",
        attrs={"tribunal": "STF", "ementa": ""},
        occurred_at=dt,
        description="Acórdão genérico sem referência a CNPJ",
        value_brl=None,
    )
    session = _FakeSession([[ruling]])
    signals = await T28JudicialPrecedentWarningTypology().run(session)
    assert signals == []


# ── Positive cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_medium_cnpj_match():
    """CNPJ in ruling matches entity with active contract → MEDIUM signal."""
    entity_id = uuid.uuid4()
    cnpj = "12.345.678/0001-99"
    r = _ruling_event(cnpj=cnpj)
    c, cp = _contract_event(entity_id=entity_id)
    ent = _entity(entity_id=entity_id, tax_id="12345678000199")

    # Queue: rulings, contracts, contract_participants, entities
    session = _FakeSession([[r], [c], [cp], [ent]])

    signals = await T28JudicialPrecedentWarningTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.severity == SignalSeverity.MEDIUM
    assert sig.typology_code == "T28"
    assert sig.confidence == 0.65
    assert sig.factors["tribunal"] == "STF"
    assert sig.factors["contract_count"] == 1


# ── Unit tests ───────────────────────────────────────────────────────────────


def test_normalise_tax_id():
    assert _normalise_tax_id("12.345.678/0001-99") == "12345678000199"
    assert _normalise_tax_id("123.456.789-00") == "12345678900"
    assert _normalise_tax_id("00000000000") == "00000000000"


# ── Metadata ─────────────────────────────────────────────────────────────────


def test_t28_metadata():
    t = T28JudicialPrecedentWarningTypology()
    assert t.id == "T28"
    assert "Jurisprud" in t.name or "Alerta" in t.name
    assert "jurisprudencia" in t.required_domains
    assert "contrato" in t.required_domains
    assert t.evidence_level == "proxy"
    assert "fraude_licitatoria" in t.corruption_types
