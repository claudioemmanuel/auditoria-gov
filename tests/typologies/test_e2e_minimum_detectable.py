import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.orm import Entity, Event, EventParticipant
from shared.typologies.t01_concentration import T01ConcentrationTypology
from shared.typologies.t02_low_competition import T02LowCompetitionTypology
from shared.typologies.t03_splitting import T03SplittingTypology
from shared.typologies.t04_amendments_outlier import T04AmendmentsOutlierTypology
from shared.typologies.t05_price_outlier import T05PriceOutlierTypology
from shared.typologies.t06_shell_company_proxy import T06ShellCompanyProxyTypology
from shared.typologies.t07_cartel_network import T07CartelNetworkTypology
from shared.typologies.t08_sanctions_mismatch import T08SanctionsMismatchTypology
from shared.typologies.t09_ghost_payroll_proxy import T09GhostPayrollProxyTypology
from shared.typologies.t10_outsourcing_parallel_payroll import T10OutsourcingParallelPayrollTypology


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


@pytest.mark.asyncio
async def test_t02_minimum_detectable_dataset_generates_signal(monkeypatch):
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()
    bidder_id = uuid.uuid4()

    events = [
        Event(
            id=event_id,
            type="licitacao",
            occurred_at=now - timedelta(days=3),
            source_connector="compras_gov",
            source_id="lic:1",
            value_brl=10000.0,
            attrs={"modality": "pregao"},
        )
    ]
    bidders = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=event_id,
            entity_id=bidder_id,
            role="bidder",
            attrs={},
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"p10": 3.0}

    monkeypatch.setattr("shared.typologies.t02_low_competition.get_baseline", _baseline)

    session = _FakeAsyncSession([events, bidders])
    signals = await T02LowCompetitionTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T02"
    assert signals[0].factors["n_bidders"] == 1


@pytest.mark.asyncio
async def test_t03_minimum_detectable_dataset_generates_signal():
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()

    events = [
        Event(
            id=e1,
            type="despesa",
            occurred_at=now - timedelta(days=10),
            source_connector="senado",
            source_id="ceaps:1",
            value_brl=40000.0,
            attrs={"modality": "dispensa", "catmat_group": "unknown"},
        ),
        Event(
            id=e2,
            type="despesa",
            occurred_at=now - timedelta(days=2),
            source_connector="senado",
            source_id="ceaps:2",
            value_brl=30000.0,
            attrs={"modality": "dispensa", "catmat_group": "unknown"},
        ),
    ]
    buyers = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=e1,
            entity_id=buyer_id,
            role="buyer",
            attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(),
            event_id=e2,
            entity_id=buyer_id,
            role="buyer",
            attrs={},
        ),
    ]

    session = _FakeAsyncSession([events, buyers])
    signals = await T03SplittingTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T03"
    assert signals[0].factors["n_purchases"] == 2


@pytest.mark.asyncio
async def test_t08_minimum_detectable_dataset_generates_signal():
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    sanction_event_id = uuid.uuid4()
    contract_event_id = uuid.uuid4()

    sanctions = [
        Event(
            id=sanction_event_id,
            type="sancao",
            occurred_at=now - timedelta(days=60),
            source_connector="portal_transparencia",
            source_id="sancao:1",
            attrs={
                "sanction_start": (now - timedelta(days=60)).isoformat(),
                "sanction_end": (now + timedelta(days=60)).isoformat(),
                "sanction_type": "CEIS",
            },
        )
    ]
    sanction_parts = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=sanction_event_id,
            entity_id=entity_id,
            role="sanctioned",
            attrs={},
        )
    ]

    contracts = [
        Event(
            id=contract_event_id,
            type="contrato",
            occurred_at=now - timedelta(days=5),
            source_connector="comprasnet_contratos",
            source_id="contrato:1",
            value_brl=500000.0,
            attrs={
                "contract_start": (now - timedelta(days=5)).isoformat(),
                "contract_end": (now + timedelta(days=360)).isoformat(),
            },
        )
    ]
    contract_parts = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=contract_event_id,
            entity_id=entity_id,
            role="supplier",
            attrs={},
        )
    ]

    session = _FakeAsyncSession([sanctions, sanction_parts, contracts, contract_parts])
    signals = await T08SanctionsMismatchTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T08"
    assert signals[0].severity.value == "critical"


# ── T01 Concentration ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t01_minimum_detectable_dataset_generates_signal(monkeypatch):
    """One procuring entity, one CATMAT group, one winner → HHI = 1.0 (monopoly)."""
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()
    winner_id = uuid.uuid4()
    procurer_id = uuid.uuid4()

    events = [
        Event(
            id=event_id,
            type="licitacao",
            occurred_at=now - timedelta(days=5),
            source_connector="compras_gov",
            source_id="lic:t01:1",
            value_brl=100000.0,
            attrs={"catmat_group": "material_escritorio"},
        )
    ]
    winners = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=event_id,
            entity_id=winner_id,
            role="winner",
            attrs={},
        )
    ]
    procurers = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=event_id,
            entity_id=procurer_id,
            role="procuring_entity",
            attrs={},
        )
    ]

    # HHI=1.0 single winner → must exceed p90=0.25 baseline
    async def _baseline(*_args, **_kwargs):
        return {"p90": 0.25, "p95": 0.40}

    monkeypatch.setattr("shared.typologies.t01_concentration.get_baseline", _baseline)

    session = _FakeAsyncSession([events, winners, procurers])
    signals = await T01ConcentrationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T01"
    assert signals[0].factors["hhi"] == 1.0
    assert signals[0].factors["top1_share"] == 1.0


# ── T04 Amendment Outlier ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t04_minimum_detectable_dataset_generates_signal(monkeypatch):
    """Contract with 6 amendments and 60% value increase → exceeds both thresholds."""
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id,
            type="contrato",
            occurred_at=now - timedelta(days=100),
            source_connector="comprasnet_contratos",
            source_id="contrato:t04:1",
            value_brl=1000000.0,
            attrs={
                "original_value": 1000000.0,
                "amendments_total_value": 600000.0,
                "amendment_count": 6,
            },
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"p95": 0.5, "p99": 1.0}

    monkeypatch.setattr("shared.typologies.t04_amendments_outlier.get_baseline", _baseline)

    session = _FakeAsyncSession([events])
    signals = await T04AmendmentsOutlierTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T04"
    assert signals[0].factors["amendment_count"] == 6
    assert signals[0].factors["pct_increase"] == 0.6


# ── T05 Price Outlier ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t05_minimum_detectable_dataset_generates_signal(monkeypatch):
    """Event with unit_price = 500, baseline p95 = 200, median = 50 → flagged."""
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id,
            type="licitacao",
            occurred_at=now - timedelta(days=10),
            source_connector="compras_gov",
            source_id="lic:t05:1",
            value_brl=500.0,
            attrs={"catmat_code": "CAT001", "unit_price": 500.0, "quantity": 10},
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"p95": 200.0, "p99": 400.0, "median": 50.0, "sample_size": 100}

    monkeypatch.setattr("shared.typologies.t05_price_outlier.get_baseline", _baseline)

    session = _FakeAsyncSession([events])
    signals = await T05PriceOutlierTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T05"
    assert signals[0].factors["unit_price"] == 500.0
    assert signals[0].factors["overpricing_ratio"] == 10.0
    assert signals[0].factors["catmat_code"] == "CAT001"
    assert signals[0].severity.value == "critical"  # > p99 and ratio > 5x


# ── T06 Shell Company ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t06_minimum_detectable_dataset_generates_signal():
    """Young company with zero capital + shared address (3 others) → composite >= 0.7."""
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    event_id = uuid.uuid4()

    shared_address = "Rua Ficticia 123, Sala 456, Brasilia DF"
    shared_phone = "61999999999"

    # Query 1: winners (EventParticipant)
    winners = [
        EventParticipant(
            id=uuid.uuid4(),
            event_id=event_id,
            entity_id=entity_id,
            role="winner",
            attrs={},
        )
    ]

    # Query 2: entities (via execute_chunked_in) — company type
    # Main entity + 3 others at same address → shared_address_score = 1.0
    other_entities = []
    for i in range(3):
        other_entities.append(
            Entity(
                id=uuid.uuid4(),
                type="company",
                name=f"Empresa Satelite {i} LTDA",
                name_normalized=f"empresa satelite {i} ltda",
                identifiers={"cnpj": f"1111111100{i:04d}"},
                attrs={
                    "address": shared_address,
                    "telefone": shared_phone,
                },
            )
        )

    entities = [
        Entity(
            id=entity_id,
            type="company",
            name="Empresa Fachada LTDA",
            name_normalized="empresa fachada ltda",
            identifiers={"cnpj": "12345678000190"},
            attrs={
                "data_abertura": (now - timedelta(days=100)).isoformat(),
                "capital_social": 0,
                "address": shared_address,
                "telefone": shared_phone,
            },
        ),
        *other_entities,
    ]

    # Query 3: events (via execute_chunked_in) — contract value
    events = [
        Event(
            id=event_id,
            type="licitacao",
            occurred_at=now - timedelta(days=10),
            source_connector="compras_gov",
            source_id="lic:t06:1",
            value_brl=500000.0,
            attrs={},
        )
    ]

    session = _FakeAsyncSession([winners, entities, events])
    signals = await T06ShellCompanyProxyTypology().run(session)

    assert len(signals) >= 1
    t06 = [s for s in signals if s.typology_code == "T06"]
    assert len(t06) >= 1
    assert t06[0].factors["composite_score"] >= 0.7


# ── T07 Cartel ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t07_minimum_detectable_dataset_generates_signal():
    """10 events, same buyer + catmat, 2 winners alternating, 2 bidders always together."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    winner_a = uuid.uuid4()
    winner_b = uuid.uuid4()

    events = []
    participants = []

    # 10 procurements in the same catmat group with the same buyer
    for i in range(10):
        eid = uuid.uuid4()
        events.append(
            Event(
                id=eid,
                type="licitacao",
                occurred_at=now - timedelta(days=30 + i * 10),
                source_connector="compras_gov",
                source_id=f"lic:t07:{i}",
                value_brl=50000.0,
                attrs={"catmat_group": "informatica"},
            )
        )
        # Buyer
        participants.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=eid,
                entity_id=buyer_id,
                role="buyer",
                attrs={},
            )
        )
        # Alternate winners: A wins even rounds, B wins odd rounds
        winner = winner_a if i % 2 == 0 else winner_b
        participants.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=eid,
                entity_id=winner,
                role="winner",
                attrs={},
            )
        )
        # Both A and B always bid together (co-participation)
        participants.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=eid,
                entity_id=winner_a,
                role="bidder",
                attrs={},
            )
        )
        participants.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=eid,
                entity_id=winner_b,
                role="bidder",
                attrs={},
            )
        )

    session = _FakeAsyncSession([events, participants])
    signals = await T07CartelNetworkTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T07"
    assert signals[0].factors["n_factors"] >= 2
    assert signals[0].factors["alternation_ratio"] <= 0.3


# ── T09 Ghost Payroll ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t09_minimum_detectable_dataset_generates_signal():
    """Servant in 3 organs + round values + compensation jump → composite >= 0.6."""
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()

    events = []
    participants = []

    # 3 remuneration events in different organs with round values and a jump
    values = [5000.0, 5000.0, 15000.0]  # 3rd is 3x the 2nd → jump_score = 0.8
    for i, (organ, val) in enumerate(zip(["organ_a", "organ_b", "organ_c"], values)):
        eid = uuid.uuid4()
        events.append(
            Event(
                id=eid,
                type="remuneracao",
                occurred_at=now - timedelta(days=90 - i * 30),  # chronological order
                source_connector=organ,
                source_id=f"rem:t09:{i}",
                value_brl=val,
                attrs={"organ_id": organ, "benefit_codes": []},
            )
        )
        participants.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=eid,
                entity_id=servant_id,
                role="servant",
                attrs={},
            )
        )

    session = _FakeAsyncSession([events, participants])
    signals = await T09GhostPayrollProxyTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T09"
    assert signals[0].factors["n_organs"] == 3
    assert signals[0].factors["composite_score"] >= 0.6


# ── T10 Outsourcing Parallel ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_t10_minimum_detectable_dataset_generates_signal():
    """3 contracts, same buyer-supplier, spanning >5 years, outsourcing keywords."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    contracts = []
    supplier_parts = []
    buyer_parts = []

    for i in range(3):
        cid = uuid.uuid4()
        contracts.append(
            Event(
                id=cid,
                type="contrato",
                occurred_at=now - timedelta(days=365 * (6 - i * 2)),
                source_connector="comprasnet_contratos",
                source_id=f"contrato:t10:{i}",
                value_brl=200000.0,
                description="Prestacao de servicos de limpeza e conservacao",
                attrs={
                    "original_value": 200000.0,
                    "amendment_count": 0,
                    "amendments_total_value": 0,
                },
            )
        )
        supplier_parts.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=cid,
                entity_id=supplier_id,
                role="supplier",
                attrs={},
            )
        )
        buyer_parts.append(
            EventParticipant(
                id=uuid.uuid4(),
                event_id=cid,
                entity_id=buyer_id,
                role="buyer",
                attrs={},
            )
        )

    session = _FakeAsyncSession([contracts, supplier_parts, buyer_parts])
    signals = await T10OutsourcingParallelPayrollTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T10"
    assert signals[0].factors["n_factors"] >= 2
    assert signals[0].factors["concentration"] is True
    assert signals[0].factors["outsourcing_flag"] is True
