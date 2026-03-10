"""Tests for T02 Low Competition typology — situacao and modality filters."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.orm import Event, EventParticipant
from shared.models.signals import SignalSeverity
from shared.typologies.t01_concentration import T01ConcentrationTypology
from shared.typologies.t02_low_competition import T02LowCompetitionTypology
from shared.typologies.t03_splitting import T03SplittingTypology
from shared.typologies.t05_price_outlier import T05PriceOutlierTypology
from shared.typologies.t07_cartel_network import T07CartelNetworkTypology
from shared.typologies.t12_directed_tender import T12DirectedTenderTypology
from shared.typologies.t15_false_sole_source import T15FalseSoleSourceTypology


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeAsyncSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _stmt):
        if not self._responses:
            raise AssertionError("No fake response available for execute()")
        return _ScalarResult(self._responses.pop(0))


def _now():
    return datetime.now(timezone.utc)


def _licitacao(*, modality: str = "pregao", situacao: str = "", value: float = 50_000.0, **extra_attrs):
    return Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=5),
        source_connector="pncp",
        source_id=f"lic:{uuid.uuid4()}",
        value_brl=value,
        attrs={"modality": modality, "situacao": situacao, "catmat_group": "group_x", **extra_attrs},
    )


def _bidder(event_id: uuid.UUID) -> EventParticipant:
    return EventParticipant(
        id=uuid.uuid4(), event_id=event_id, entity_id=uuid.uuid4(), role="bidder", attrs={}
    )


# ---------------------------------------------------------------------------
# T02 — 5 cenários
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t02_skips_dispensa(monkeypatch):
    """Modalidade dispensa → sem sinal (0 licitantes é esperado por lei)."""
    e = _licitacao(modality="dispensa", situacao="")

    async def _baseline(*_, **__):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])
    signals = await T02LowCompetitionTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t02_skips_pregao_deserto(monkeypatch):
    """Modalidade pregão com situação=Deserta → sem sinal."""
    e = _licitacao(modality="pregao", situacao="Deserta")

    async def _baseline(*_, **__):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])
    signals = await T02LowCompetitionTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t02_critical_adjudicada_zero(monkeypatch):
    """Pregão homologado com 0 licitantes → sinal CRITICAL."""
    e = _licitacao(modality="pregao", situacao="Homologada")

    async def _baseline(*_, **__):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])  # no bidder participants → n_bidders=0
    signals = await T02LowCompetitionTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.CRITICAL
    assert signals[0].factors["situacao"] == "homologada"
    assert signals[0].factors["n_bidders"] == 0


@pytest.mark.asyncio
async def test_t02_high_unknown_situacao_zero(monkeypatch):
    """Pregão com situação desconhecida e 0 licitantes → sinal HIGH (conservador)."""
    e = _licitacao(modality="pregao", situacao="")

    async def _baseline(*_, **__):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])  # no bidders → n_bidders=0
    signals = await T02LowCompetitionTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.HIGH
    assert signals[0].factors["n_bidders"] == 0


@pytest.mark.asyncio
async def test_t02_medium_below_p10(monkeypatch):
    """Pregão homologado com 2 licitantes e p10=5 → sinal MEDIUM."""
    e = _licitacao(modality="pregao", situacao="Homologada")
    bidder1 = _bidder(e.id)
    bidder2 = _bidder(e.id)

    async def _baseline(*_, **__):
        return {"p10": 5.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], [bidder1, bidder2]])
    signals = await T02LowCompetitionTypology().run(session)

    assert len(signals) == 1
    assert signals[0].severity == SignalSeverity.MEDIUM
    assert signals[0].factors["n_bidders"] == 2


# ---------------------------------------------------------------------------
# Filtro situacao nas demais tipologias (1 teste cada)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t01_skips_void_situation(monkeypatch):
    """T01: licitação com situação=Deserta deve ser excluída do cálculo de HHI."""
    e = _licitacao(modality="pregao", situacao="Deserta", value=100_000.0)
    winner = EventParticipant(
        id=uuid.uuid4(), event_id=e.id, entity_id=uuid.uuid4(), role="winner", attrs={}
    )
    buyer = EventParticipant(
        id=uuid.uuid4(), event_id=e.id, entity_id=uuid.uuid4(), role="buyer", attrs={}
    )

    async def _baseline(*_, **__):
        return {"p90": 0.0, "p95": 0.1}  # very low thresholds → would flag if not filtered

    monkeypatch.setattr("shared.typologies.t01_concentration.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], [winner], [buyer]])
    signals = await T01ConcentrationTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t03_skips_void_dispensa():
    """T03: dispensa com situação=cancelada não deve gerar sinal de fracionamento."""
    buyer_id = uuid.uuid4()
    now = _now()
    e1 = Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=now - timedelta(days=10),
        source_connector="pncp",
        source_id="lic:1",
        value_brl=40_000.0,
        attrs={"modality": "dispensa", "situacao": "Cancelada", "catmat_group": "group_x"},
    )
    e2 = Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=now - timedelta(days=2),
        source_connector="pncp",
        source_id="lic:2",
        value_brl=40_000.0,
        attrs={"modality": "dispensa", "situacao": "Cancelada", "catmat_group": "group_x"},
    )
    buyer1 = EventParticipant(
        id=uuid.uuid4(), event_id=e1.id, entity_id=buyer_id, role="buyer", attrs={}
    )
    buyer2 = EventParticipant(
        id=uuid.uuid4(), event_id=e2.id, entity_id=buyer_id, role="buyer", attrs={}
    )

    session = _FakeAsyncSession([[e1, e2], [buyer1, buyer2]])
    signals = await T03SplittingTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t05_skips_void_licitacao(monkeypatch):
    """T05: licitação deserta com preço alto não deve gerar sinal de sobrepreço."""
    e = Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=5),
        source_connector="pncp",
        source_id="lic:1",
        value_brl=9_999_999.0,
        attrs={"modality": "pregao", "situacao": "Deserta", "catmat_code": "item_x", "unit_price": 9_999_999.0},
    )

    # get_baseline should never be called since event is filtered out
    called = []

    async def _baseline(*_, **__):
        called.append(True)
        return {"p95": 100.0, "p99": 200.0, "median": 50.0, "sample_size": 10}

    monkeypatch.setattr("shared.typologies.t05_price_outlier.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])
    signals = await T05PriceOutlierTypology().run(session)

    assert signals == []
    assert called == []  # confirm filter fired before baseline lookup


@pytest.mark.asyncio
async def test_t07_skips_void_events():
    """T07: eventos com situação=fracassada devem ser excluídos do grafo de cartel."""
    void_events = [
        _licitacao(modality="pregao", situacao="Fracassada")
        for _ in range(4)
    ]
    bidders = [_bidder(e.id) for e in void_events]

    session = _FakeAsyncSession([void_events, bidders])
    signals = await T07CartelNetworkTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t12_skips_void_competitive_events(monkeypatch):
    """T12: licitação competitiva com situação=Revogada não deve gerar sinal."""
    e = _licitacao(modality="pregao", situacao="Revogada")

    async def _baseline(*_, **__):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t12_directed_tender.get_baseline", _baseline)
    session = _FakeAsyncSession([[e], []])
    signals = await T12DirectedTenderTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t15_skips_void_inexigibilidade():
    """T15: inexigibilidade com situação=cancelada não deve gerar sinal."""
    e_inexig = Event(
        id=uuid.uuid4(),
        type="licitacao",
        occurred_at=_now() - timedelta(days=5),
        source_connector="pncp",
        source_id="lic:1",
        value_brl=50_000.0,
        attrs={"modality": "inexigibilidade", "situacao": "Cancelada", "catmat_group": "group_x"},
    )
    supplier = EventParticipant(
        id=uuid.uuid4(), event_id=e_inexig.id, entity_id=uuid.uuid4(), role="supplier", attrs={}
    )

    session = _FakeAsyncSession([[e_inexig], [supplier]])
    signals = await T15FalseSoleSourceTypology().run(session)

    assert signals == []
