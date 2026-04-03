import uuid
from datetime import datetime, timedelta, timezone

import pytest

from shared.models.orm import (
    Entity,
    Event,
    EventParticipant,
    GraphEdge,
    GraphNode,
    RiskSignal,
    Typology,
)
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
from shared.typologies.t11_spreadsheet_manipulation import T11SpreadsheetManipulationTypology
from shared.typologies.t12_directed_tender import T12DirectedTenderTypology
from shared.typologies.t13_conflict_of_interest import T13ConflictOfInterestTypology
from shared.typologies.t14_compound_favoritism import T14CompoundFavoritismTypology
from shared.typologies.t15_false_sole_source import T15FalseSoleSourceTypology
from shared.typologies.t16_budget_clientelism import T16BudgetClientelismTypology
from shared.typologies.t17_layered_money_laundering import T17LayeredMoneyLaunderingTypology
from shared.typologies.t18_illegal_position_accumulation import T18IllegalPositionAccumulationTypology


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


@pytest.mark.asyncio
async def test_t01_top1_dominant_low_hhi_has_valid_confidence(monkeypatch):
    """top1_share > 0.80 with near-floor HHI + high p95 baseline must produce valid confidence.

    Regression: HIGH-branch formula ``0.7 + (hhi - p95) * 2`` returns a negative
    value when hhi ≈ 0.65 and p95 = 1.0 (top1_share=0.805 is the sole trigger),
    which violates ``Field(ge=0.0)`` and raises a Pydantic ValidationError.
    Fix: wrap with ``max(0.60, min(0.95, ...))``.

    Setup: 1 dominant winner (80.5%) + 20 small winners (0.975% each).
    hhi ≈ 0.6499, top1_share = 0.805. Baseline p90=0.60, p95=1.0.
    """
    now = datetime.now(timezone.utc)
    catmat = "servicos_ti"
    procurer_id = uuid.uuid4()
    big_winner_id = uuid.uuid4()
    big_event_id = uuid.uuid4()
    small_ids = [uuid.uuid4() for _ in range(20)]
    small_event_ids = [uuid.uuid4() for _ in range(20)]

    all_events = [
        Event(
            id=big_event_id,
            type="licitacao",
            occurred_at=now - timedelta(days=10),
            source_connector="compras_gov",
            source_id="lic:t01:regr:big",
            value_brl=80500.0,
            attrs={"catmat_group": catmat},
        )
    ] + [
        Event(
            id=eid,
            type="licitacao",
            occurred_at=now - timedelta(days=10),
            source_connector="compras_gov",
            source_id=f"lic:t01:regr:small:{i}",
            value_brl=975.0,
            attrs={"catmat_group": catmat},
        )
        for i, eid in enumerate(small_event_ids)
    ]

    all_winners = [
        EventParticipant(
            id=uuid.uuid4(), event_id=big_event_id,
            entity_id=big_winner_id, role="winner", attrs={},
        )
    ] + [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid,
            entity_id=wid, role="winner", attrs={},
        )
        for eid, wid in zip(small_event_ids, small_ids)
    ]

    all_procurers = [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid,
            entity_id=procurer_id, role="procuring_entity", attrs={},
        )
        for eid in [big_event_id] + small_event_ids
    ]

    async def _baseline(*_args, **_kwargs):
        return {"p90": 0.60, "p95": 1.0}

    monkeypatch.setattr("shared.typologies.t01_concentration.get_baseline", _baseline)

    session = _FakeAsyncSession([all_events, all_winners, all_procurers])
    signals = await T01ConcentrationTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.typology_code == "T01"
    assert sig.severity.value == "high"
    assert sig.factors["top1_share"] > 0.80
    # hhi ≈ 0.6499 → before fix: 0.7+(0.6499-1.0)*2 = -0.0002 → ValidationError
    assert 0.0 <= sig.confidence <= 1.0, f"confidence out of bounds: {sig.confidence}"
    assert sig.confidence == pytest.approx(0.60)


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

    session = _FakeAsyncSession([events, []])  # 2nd call: parts query returns empty
    signals = await T04AmendmentsOutlierTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T04"
    assert signals[0].factors["amendment_count"] == 6
    assert signals[0].factors["pct_increase"] == 0.6


@pytest.mark.asyncio
async def test_t04_count_only_flag_has_valid_confidence(monkeypatch):
    """amendment_count=6 with zero value increase must produce valid confidence.

    Regression: HIGH-branch formula ``0.6 + (pct_increase - p95) * 2`` returns -0.4
    when pct_increase=0 and p95=0.5, violating ``Field(ge=0.0)`` and raising a
    Pydantic ValidationError. Fix: wrap with ``max(0.60, min(0.88, ...))``.
    """
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id,
            type="contrato",
            occurred_at=now - timedelta(days=100),
            source_connector="comprasnet_contratos",
            source_id="contrato:t04:count:1",
            value_brl=1000000.0,
            attrs={
                "original_value": 1000000.0,
                "amendments_total_value": 0.0,   # zero value — pure count trigger
                "amendment_count": 6,             # > 5 → should_flag=True
            },
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"p95": 0.5, "p99": 1.0}

    monkeypatch.setattr("shared.typologies.t04_amendments_outlier.get_baseline", _baseline)

    session = _FakeAsyncSession([events, []])
    signals = await T04AmendmentsOutlierTypology().run(session)

    assert len(signals) == 1
    sig = signals[0]
    assert sig.typology_code == "T04"
    assert sig.severity.value == "high"
    assert sig.factors["pct_increase"] == 0.0
    # Before fix: min(0.88, 0.6+(0-0.5)*2) = min(0.88, -0.4) = -0.4 → ValidationError
    assert 0.0 <= sig.confidence <= 1.0, f"confidence out of bounds: {sig.confidence}"
    assert sig.confidence == pytest.approx(0.60)


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

    session = _FakeAsyncSession([events, []])  # 2nd call: parts query returns empty
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

    # Query 4: buyer participants (execute_chunked_in) — empty, no specific buyers needed
    session = _FakeAsyncSession([winners, entities, events, []])
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
    """Servant in 4 organs + round values + compensation jump + benefit codes → composite >= 0.7.

    Scoring breakdown (updated thresholds in t09):
      multi_organ_score = 0.9 (>= 4 organs) * 0.35 = 0.315
      round_number_score = 0.8 (>80% round)  * 0.20 = 0.160
      compensation_jump_score = 0.8 (3x jump) * 0.25 = 0.200
      benefit_codes_score = 0.5 (8 codes > 6) * 0.20 = 0.100
      composite = 0.775 >= 0.7
    """
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()

    events = []
    participants = []

    # 4 remuneration events in different organs with round values and a jump
    organs = ["organ_a", "organ_b", "organ_c", "organ_d"]
    values = [5000.0, 5000.0, 15000.0, 5000.0]  # 3rd is 3x the 2nd → jump_score = 0.8
    benefit_codes = [[], [], [], [f"BC{j:02d}" for j in range(8)]]  # last event: 8 codes > 6
    for i, (organ, val, bcodes) in enumerate(zip(organs, values, benefit_codes)):
        eid = uuid.uuid4()
        events.append(
            Event(
                id=eid,
                type="remuneracao",
                occurred_at=now - timedelta(days=120 - i * 30),  # chronological order
                source_connector=organ,
                source_id=f"rem:t09:{i}",
                value_brl=val,
                attrs={"organ_id": organ, "benefit_codes": bcodes},
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
    assert signals[0].factors["n_organs"] == 4
    assert signals[0].factors["composite_score"] >= 0.7


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


# ── T11 Spreadsheet Manipulation ──────────────────────────────────────


@pytest.mark.asyncio
async def test_t11_minimum_detectable_dataset_generates_signal(monkeypatch):
    """Contract with overpriced item (3× baseline) whose quantity increased via amendment."""
    now = datetime.now(timezone.utc)
    contract_id = uuid.uuid4()
    supplier_id = uuid.uuid4()

    # unit_price=300, baseline_median=100 → ratio=3.0 ≥ 2.0
    # quantity_delta=600 → overcharge = (300-100)*600 = 120,000 > R$ 100k → CRITICAL
    contracts = [
        Event(
            id=contract_id,
            type="contrato",
            occurred_at=now - timedelta(days=90),
            source_connector="comprasnet_contratos",
            source_id="contrato:t11:1",
            value_brl=500_000.0,
            attrs={
                "catmat_code": "CAT-ENG",
                "amendment_count": 2,
                "item_prices": [
                    {"item_code": "ITEM001", "unit_price": 300.0, "quantity": 1000},
                ],
                "amendments": [
                    {"item_code": "ITEM001", "quantity_delta": 600},
                ],
            },
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=contract_id, entity_id=supplier_id,
            role="supplier", attrs={},
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"median": 100.0}

    monkeypatch.setattr(
        "shared.typologies.t11_spreadsheet_manipulation.get_baseline", _baseline
    )

    session = _FakeAsyncSession([contracts, participants])
    signals = await T11SpreadsheetManipulationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T11"
    assert signals[0].factors["n_items_overpriced"] == 1
    assert signals[0].factors["net_overcharge_brl"] == 120_000.0
    assert signals[0].severity.value == "critical"


# ── T12 Directed Tender ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t12_minimum_detectable_dataset_generates_signal(monkeypatch):
    """3 pregao events, same buyer+catmat, same winner, 1 bidder each → directed tender."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    winner_id = uuid.uuid4()

    events = []
    participants = []

    for i in range(3):
        eid = uuid.uuid4()
        events.append(Event(
            id=eid,
            type="licitacao",
            occurred_at=now - timedelta(days=30 * (i + 1)),
            source_connector="compras_gov",
            source_id=f"lic:t12:{i}",
            value_brl=80_000.0,
            attrs={"modality": "pregao", "catmat_group": "informatica"},
        ))
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=buyer_id, role="buyer", attrs={},
        ))
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=winner_id, role="winner", attrs={},
        ))
        # winner is also the only bidder → n_bidders=1 ≤ p10 threshold
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=winner_id, role="bidder", attrs={},
        ))

    async def _baseline(*_args, **_kwargs):
        return {"p10": 3.0}

    monkeypatch.setattr(
        "shared.typologies.t12_directed_tender.get_baseline", _baseline
    )

    session = _FakeAsyncSession([events, participants])
    signals = await T12DirectedTenderTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T12"
    assert signals[0].factors["win_count"] == 3
    assert signals[0].factors["repeat_winner"] is True


# ── T13 Conflict of Interest ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_t13_minimum_detectable_dataset_generates_signal():
    """Buyer and supplier share SAME_SOCIO + SAME_ADDRESS edges → conflict of interest."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    event_id = uuid.uuid4()

    # SAME_SOCIO(0.4) + SAME_ADDRESS(0.30) = 0.70 ≥ 0.6, n_shared=2 ≥ 2
    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_SOCIO", weight=1.0,
        ),
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_ADDRESS", weight=1.0,
        ),
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=buyer_id),
        GraphNode(id=node_b_id, entity_id=supplier_id),
    ]
    events = [
        Event(
            id=event_id, type="licitacao",
            occurred_at=now - timedelta(days=30),
            source_connector="compras_gov", source_id="lic:t13:1",
            value_brl=200_000.0, attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=buyer_id,
            role="buyer", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=supplier_id,
            role="winner", attrs={},
        ),
    ]

    session = _FakeAsyncSession([edges, nodes, events, participants])
    signals = await T13ConflictOfInterestTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T13"
    assert signals[0].factors["n_shared_indicators"] == 2
    assert signals[0].factors["relationship_score"] >= 0.6
    assert "SAME_SOCIO" in signals[0].factors["indicator_types"]


# ── T14 Compound Favoritism ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t14_minimum_detectable_dataset_generates_signal():
    """Entity triggers T01+T02 with HIGH severity, meta_score=4, span=400 days."""
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    typ_t01_id = uuid.uuid4()
    typ_t02_id = uuid.uuid4()

    typologies = [
        Typology(id=typ_t01_id, code="T01"),
        Typology(id=typ_t02_id, code="T02"),
    ]

    # 2 HIGH signals → meta_score = 2+2 = 4 ≥ 4; span = 400 days ≥ 180
    component_signals = [
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t01_id, severity="high",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=400),
            period_end=now - timedelta(days=200),
        ),
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t02_id, severity="high",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=200),
            period_end=now,
        ),
    ]

    session = _FakeAsyncSession([typologies, component_signals])
    signals = await T14CompoundFavoritismTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T14"
    assert signals[0].factors["meta_score"] == 4
    assert signals[0].factors["n_component_typologies"] == 2
    assert signals[0].factors["temporal_span_days"] >= 180


# ── T15 False Sole-Source ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t15_minimum_detectable_dataset_generates_signal():
    """Supplier wins 2 inexigibilidade contracts; 3 alternative suppliers in same CATMAT."""
    now = datetime.now(timezone.utc)
    agency_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    alt_s1, alt_s2, alt_s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    catmat = "consultoria"
    inex1, inex2 = uuid.uuid4(), uuid.uuid4()
    comp1, comp2 = uuid.uuid4(), uuid.uuid4()

    events = [
        Event(id=inex1, type="licitacao", occurred_at=now - timedelta(days=90),
              source_connector="compras_gov", source_id="lic:t15:1",
              value_brl=80_000.0, attrs={"modality": "inexigibilidade", "catmat_group": catmat}),
        Event(id=inex2, type="licitacao", occurred_at=now - timedelta(days=30),
              source_connector="compras_gov", source_id="lic:t15:2",
              value_brl=90_000.0, attrs={"modality": "inexigibilidade", "catmat_group": catmat}),
        Event(id=comp1, type="licitacao", occurred_at=now - timedelta(days=180),
              source_connector="compras_gov", source_id="lic:t15:3",
              value_brl=75_000.0, attrs={"modality": "pregao", "catmat_group": catmat}),
        Event(id=comp2, type="licitacao", occurred_at=now - timedelta(days=150),
              source_connector="compras_gov", source_id="lic:t15:4",
              value_brl=85_000.0, attrs={"modality": "pregao", "catmat_group": catmat}),
    ]
    participants = [
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=agency_id, role="buyer", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=supplier_id, role="winner", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex2, entity_id=agency_id, role="buyer", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex2, entity_id=supplier_id, role="winner", attrs={}),
        # 3 distinct alternative suppliers in competitive events
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s1, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s2, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp2, entity_id=alt_s2, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp2, entity_id=alt_s3, role="winner", attrs={}),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T15FalseSoleSourceTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T15"
    assert signals[0].factors["n_inexigibilidade_contracts"] == 2
    assert signals[0].factors["n_alternative_suppliers"] >= 3


# ── T16 Budget Clientelism ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t16_minimum_detectable_dataset_generates_signal():
    """Amendment with no work plan + value 4× municipal revenue → n_flags=2."""
    now = datetime.now(timezone.utc)
    beneficiary_id = uuid.uuid4()
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id, type="emenda",
            occurred_at=now - timedelta(days=60),
            source_connector="transfere_gov", source_id="emenda:t16:1",
            value_brl=400_000.0,
            attrs={
                "plano_trabalho_registered": False,
                "municipality_revenue_brl": 100_000.0,  # ratio = 4.0 > 3.0
                "relator_id": "REL001",
            },
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=beneficiary_id,
            role="beneficiary", attrs={},
        )
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T16BudgetClientelismTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T16"
    assert signals[0].factors["n_flags"] >= 2
    assert signals[0].factors["plano_trabalho_registered"] is False


# ── T17 Layered Money Laundering ───────────────────────────────────────


@pytest.mark.asyncio
async def test_t17_minimum_detectable_dataset_generates_signal():
    """Two-hop ownership cycle; contract R$ 200k exceeds threshold → layered laundering."""
    now = datetime.now(timezone.utc)
    entity_a = uuid.uuid4()
    entity_b = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    contract_id = uuid.uuid4()

    # Directed cycle: entity_a → entity_b → entity_a (2 hops)
    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_SOCIO", weight=1.0,
        ),
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_b_id, to_node_id=node_a_id,
            type="SAME_SOCIO", weight=1.0,
        ),
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=entity_a),
        GraphNode(id=node_b_id, entity_id=entity_b),
    ]
    contracts = [
        Event(
            id=contract_id, type="contrato",
            occurred_at=now - timedelta(days=60),
            source_connector="comprasnet_contratos", source_id="contrato:t17:1",
            value_brl=200_000.0, attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=contract_id, entity_id=entity_a,
            role="winner", attrs={},
        )
    ]

    session = _FakeAsyncSession([edges, nodes, contracts, participants])
    signals = await T17LayeredMoneyLaunderingTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T17"
    assert signals[0].factors["cycle_length"] == 2


# ── T18 Illegal Position Accumulation ─────────────────────────────────


@pytest.mark.asyncio
async def test_t18_minimum_detectable_dataset_generates_signal():
    """Servant in 2 organs with 90-day overlap → illegal position accumulation."""
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()
    eid_a = uuid.uuid4()
    eid_b = uuid.uuid4()

    period_start_a = now - timedelta(days=180)
    period_end_a = now - timedelta(days=30)
    period_start_b = now - timedelta(days=120)
    period_end_b = now
    # overlap = [now-120d, now-30d] = 90 days ≥ 30

    events = [
        Event(
            id=eid_a, type="remuneracao",
            occurred_at=now - timedelta(days=180),
            source_connector="siape", source_id="rem:t18:1",
            value_brl=10_000.0,
            attrs={
                "organ_id": "ORGAN_A",
                "period_start": period_start_a.isoformat(),
                "period_end": period_end_a.isoformat(),
            },
        ),
        Event(
            id=eid_b, type="remuneracao",
            occurred_at=now - timedelta(days=120),
            source_connector="siape", source_id="rem:t18:2",
            value_brl=12_000.0,
            attrs={
                "organ_id": "ORGAN_B",
                "period_start": period_start_b.isoformat(),
                "period_end": period_end_b.isoformat(),
            },
        ),
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_a, entity_id=servant_id,
            role="servant", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_b, entity_id=servant_id,
            role="servant", attrs={},
        ),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T18IllegalPositionAccumulationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T18"
    assert signals[0].factors["n_organs"] == 2
    assert signals[0].factors["overlap_days"] >= 30


# ══════════════════════════════════════════════════════════════════════
# NEGATIVE / BOUNDARY TESTS — rules must NOT fire below threshold
# ══════════════════════════════════════════════════════════════════════


# ── T11 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t11_below_ratio_threshold_no_signal(monkeypatch):
    """Item with price ratio 1.5× baseline (< 2.0) must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    contract_id = uuid.uuid4()

    contracts = [
        Event(
            id=contract_id, type="contrato",
            occurred_at=now - timedelta(days=90),
            source_connector="comprasnet_contratos", source_id="contrato:t11:neg1",
            value_brl=200_000.0,
            attrs={
                "catmat_code": "CAT-ENG",
                "amendment_count": 1,
                "item_prices": [{"item_code": "ITEM001", "unit_price": 150.0}],
                "amendments": [{"item_code": "ITEM001", "quantity_delta": 1000}],
            },
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"median": 100.0}  # ratio = 150/100 = 1.5 < 2.0

    monkeypatch.setattr(
        "shared.typologies.t11_spreadsheet_manipulation.get_baseline", _baseline
    )

    session = _FakeAsyncSession([contracts, []])
    signals = await T11SpreadsheetManipulationTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t11_overpriced_item_no_quantity_increase_no_signal(monkeypatch):
    """Item ratio > 2.0 but quantity_delta ≤ 0 must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    contract_id = uuid.uuid4()

    contracts = [
        Event(
            id=contract_id, type="contrato",
            occurred_at=now - timedelta(days=90),
            source_connector="comprasnet_contratos", source_id="contrato:t11:neg2",
            value_brl=300_000.0,
            attrs={
                "catmat_code": "CAT-ENG",
                "amendment_count": 1,
                "item_prices": [{"item_code": "ITEM001", "unit_price": 300.0}],
                "amendments": [{"item_code": "ITEM001", "quantity_delta": -50}],
            },
        )
    ]

    async def _baseline(*_args, **_kwargs):
        return {"median": 100.0}  # ratio = 3.0 ≥ 2.0 but delta < 0

    monkeypatch.setattr(
        "shared.typologies.t11_spreadsheet_manipulation.get_baseline", _baseline
    )

    session = _FakeAsyncSession([contracts, []])
    signals = await T11SpreadsheetManipulationTypology().run(session)

    assert signals == []


# ── T12 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t12_only_two_wins_no_signal(monkeypatch):
    """Only 2 repeat wins (< _MIN_REPEAT_WINS=3) must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    winner_id = uuid.uuid4()

    events = []
    participants = []

    for i in range(2):  # only 2 events, below threshold of 3
        eid = uuid.uuid4()
        events.append(Event(
            id=eid, type="licitacao",
            occurred_at=now - timedelta(days=30 * (i + 1)),
            source_connector="compras_gov", source_id=f"lic:t12:neg:{i}",
            value_brl=50_000.0,
            attrs={"modality": "pregao", "catmat_group": "informatica"},
        ))
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=buyer_id, role="buyer", attrs={},
        ))
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=winner_id, role="winner", attrs={},
        ))
        participants.append(EventParticipant(
            id=uuid.uuid4(), event_id=eid, entity_id=winner_id, role="bidder", attrs={},
        ))

    async def _baseline(*_args, **_kwargs):
        return {"p10": 3.0}

    monkeypatch.setattr(
        "shared.typologies.t12_directed_tender.get_baseline", _baseline
    )

    session = _FakeAsyncSession([events, participants])
    signals = await T12DirectedTenderTypology().run(session)

    assert signals == []


# ── T13 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t13_single_indicator_no_signal():
    """Only 1 shared indicator (< _MIN_SHARED_INDICATORS=2) must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    event_id = uuid.uuid4()

    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="KINSHIP", weight=1.0,
        ),
        # Only 1 edge — n_shared=1 < 2
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=buyer_id),
        GraphNode(id=node_b_id, entity_id=supplier_id),
    ]
    events = [
        Event(
            id=event_id, type="licitacao",
            occurred_at=now - timedelta(days=30),
            source_connector="compras_gov", source_id="lic:t13:neg1",
            value_brl=100_000.0, attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=buyer_id,
            role="buyer", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=supplier_id,
            role="winner", attrs={},
        ),
    ]

    session = _FakeAsyncSession([edges, nodes, events, participants])
    signals = await T13ConflictOfInterestTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t13_unconnected_buyer_supplier_no_signal():
    """Buyer and supplier have no graph edges connecting them → no signal."""
    now = datetime.now(timezone.utc)
    buyer_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    unrelated_a = uuid.uuid4()
    unrelated_b = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    event_id = uuid.uuid4()

    # Edges exist but between unrelated entities, not buyer↔supplier
    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="KINSHIP", weight=1.0,
        ),
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_ADDRESS", weight=1.0,
        ),
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=unrelated_a),
        GraphNode(id=node_b_id, entity_id=unrelated_b),
    ]
    events = [
        Event(
            id=event_id, type="licitacao",
            occurred_at=now - timedelta(days=30),
            source_connector="compras_gov", source_id="lic:t13:neg2",
            value_brl=100_000.0, attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=buyer_id,
            role="buyer", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=event_id, entity_id=supplier_id,
            role="winner", attrs={},
        ),
    ]

    session = _FakeAsyncSession([edges, nodes, events, participants])
    signals = await T13ConflictOfInterestTypology().run(session)

    assert signals == []


# ── T14 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t14_single_typology_no_signal():
    """Only 1 distinct typology triggered (< _MIN_COMPONENT_COUNT=2) → no signal."""
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    typ_t01_id = uuid.uuid4()

    typologies = [Typology(id=typ_t01_id, code="T01")]

    component_signals = [
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t01_id, severity="critical",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=400),
            period_end=now,
        ),
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t01_id, severity="critical",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=300),
            period_end=now,
        ),
    ]  # meta_score = 6 but only 1 distinct typology

    session = _FakeAsyncSession([typologies, component_signals])
    signals = await T14CompoundFavoritismTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t14_short_temporal_span_no_signal():
    """Two typologies triggered but span only 60 days (< 180) → no signal."""
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    typ_t01_id = uuid.uuid4()
    typ_t02_id = uuid.uuid4()

    typologies = [
        Typology(id=typ_t01_id, code="T01"),
        Typology(id=typ_t02_id, code="T02"),
    ]

    component_signals = [
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t01_id, severity="high",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=60),
            period_end=now - timedelta(days=30),
        ),
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t02_id, severity="high",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=30),
            period_end=now,
        ),
    ]  # span = 60 days < 180

    session = _FakeAsyncSession([typologies, component_signals])
    signals = await T14CompoundFavoritismTypology().run(session)

    assert signals == []


# ── T15 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t15_only_two_alternative_suppliers_no_signal():
    """Only 2 alternative suppliers (< _MIN_ALTERNATIVE_SUPPLIERS=3) → no signal."""
    now = datetime.now(timezone.utc)
    agency_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    alt_s1, alt_s2 = uuid.uuid4(), uuid.uuid4()  # only 2

    catmat = "consultoria"
    inex1, inex2 = uuid.uuid4(), uuid.uuid4()
    comp1 = uuid.uuid4()

    events = [
        Event(id=inex1, type="licitacao", occurred_at=now - timedelta(days=90),
              source_connector="compras_gov", source_id="lic:t15:neg1",
              value_brl=80_000.0, attrs={"modality": "inexigibilidade", "catmat_group": catmat}),
        Event(id=inex2, type="licitacao", occurred_at=now - timedelta(days=30),
              source_connector="compras_gov", source_id="lic:t15:neg2",
              value_brl=80_000.0, attrs={"modality": "inexigibilidade", "catmat_group": catmat}),
        Event(id=comp1, type="licitacao", occurred_at=now - timedelta(days=180),
              source_connector="compras_gov", source_id="lic:t15:neg3",
              value_brl=75_000.0, attrs={"modality": "pregao", "catmat_group": catmat}),
    ]
    participants = [
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=agency_id, role="buyer", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=supplier_id, role="winner", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex2, entity_id=agency_id, role="buyer", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex2, entity_id=supplier_id, role="winner", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s1, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s2, role="winner", attrs={}),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T15FalseSoleSourceTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t15_single_repeat_inexigibilidade_no_signal():
    """Only 1 inexigibilidade contract (< _MIN_REPEAT_INEXIGIBILIDADE=2) → no signal."""
    now = datetime.now(timezone.utc)
    agency_id = uuid.uuid4()
    supplier_id = uuid.uuid4()
    alt_s1, alt_s2, alt_s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    catmat = "consultoria"
    inex1 = uuid.uuid4()
    comp1 = uuid.uuid4()

    events = [
        Event(id=inex1, type="licitacao", occurred_at=now - timedelta(days=90),
              source_connector="compras_gov", source_id="lic:t15:neg4",
              value_brl=80_000.0, attrs={"modality": "inexigibilidade", "catmat_group": catmat}),
        Event(id=comp1, type="licitacao", occurred_at=now - timedelta(days=180),
              source_connector="compras_gov", source_id="lic:t15:neg5",
              value_brl=75_000.0, attrs={"modality": "pregao", "catmat_group": catmat}),
    ]
    participants = [
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=agency_id, role="buyer", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=inex1, entity_id=supplier_id, role="winner", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s1, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s2, role="bidder", attrs={}),
        EventParticipant(id=uuid.uuid4(), event_id=comp1, entity_id=alt_s3, role="winner", attrs={}),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T15FalseSoleSourceTypology().run(session)

    assert signals == []


# ── T16 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t16_single_flag_no_signal():
    """Only 1 flag (no work plan, but revenue ratio ≤ 3×) → n_flags=1 → no signal."""
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id, type="emenda",
            occurred_at=now - timedelta(days=60),
            source_connector="transfere_gov", source_id="emenda:t16:neg1",
            value_brl=200_000.0,
            attrs={
                "plano_trabalho_registered": False,   # flag 1
                "municipality_revenue_brl": 100_000.0,  # ratio = 2.0 ≤ 3.0 → no flag
                "relator_id": "REL001",
            },
        )
    ]
    participants = []

    session = _FakeAsyncSession([events, participants])
    signals = await T16BudgetClientelismTypology().run(session)

    assert signals == []


# ── T17 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t17_acyclic_graph_no_signal():
    """One-directional graph (no cycle) must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    entity_a = uuid.uuid4()
    entity_b = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    contract_id = uuid.uuid4()

    # Only a → b, no back edge → no cycle
    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_SOCIO", weight=1.0,
        ),
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=entity_a),
        GraphNode(id=node_b_id, entity_id=entity_b),
    ]
    contracts = [
        Event(
            id=contract_id, type="contrato",
            occurred_at=now - timedelta(days=30),
            source_connector="comprasnet_contratos", source_id="contrato:t17:neg1",
            value_brl=500_000.0, attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=contract_id, entity_id=entity_a,
            role="winner", attrs={},
        )
    ]

    session = _FakeAsyncSession([edges, nodes, contracts, participants])
    signals = await T17LayeredMoneyLaunderingTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t17_cycle_but_value_below_threshold_no_signal():
    """Cycle detected but contract value < R$ 100k and no intra-community subcontractors → no signal."""
    now = datetime.now(timezone.utc)
    entity_a = uuid.uuid4()
    entity_b = uuid.uuid4()
    node_a_id = uuid.uuid4()
    node_b_id = uuid.uuid4()
    contract_id = uuid.uuid4()

    edges = [
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_a_id, to_node_id=node_b_id,
            type="SAME_SOCIO", weight=1.0,
        ),
        GraphEdge(
            id=uuid.uuid4(), from_node_id=node_b_id, to_node_id=node_a_id,
            type="SAME_SOCIO", weight=1.0,
        ),
    ]
    nodes = [
        GraphNode(id=node_a_id, entity_id=entity_a),
        GraphNode(id=node_b_id, entity_id=entity_b),
    ]
    contracts = [
        Event(
            id=contract_id, type="contrato",
            occurred_at=now - timedelta(days=30),
            source_connector="comprasnet_contratos", source_id="contrato:t17:neg2",
            value_brl=60_000.0,  # < MIN_INTRA_COMMUNITY_VALUE * 2 = 100k
            attrs={},
        )
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=contract_id, entity_id=entity_a,
            role="winner", attrs={},
        )
    ]

    session = _FakeAsyncSession([edges, nodes, contracts, participants])
    signals = await T17LayeredMoneyLaunderingTypology().run(session)

    assert signals == []


# ── T18 boundaries ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_t18_single_organ_no_signal():
    """Servant in only 1 organ (< 2 distinct organs) must NOT generate a signal."""
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()
    eid_a = uuid.uuid4()
    eid_b = uuid.uuid4()

    events = [
        Event(
            id=eid_a, type="remuneracao",
            occurred_at=now - timedelta(days=60),
            source_connector="siape", source_id="rem:t18:neg1",
            value_brl=8_000.0,
            attrs={
                "organ_id": "ORGAN_A",
                "period_start": (now - timedelta(days=60)).isoformat(),
                "period_end": now.isoformat(),
            },
        ),
        Event(
            id=eid_b, type="remuneracao",
            occurred_at=now - timedelta(days=30),
            source_connector="siape", source_id="rem:t18:neg2",
            value_brl=9_000.0,
            attrs={
                "organ_id": "ORGAN_A",  # same organ — only 1 distinct organ
                "period_start": (now - timedelta(days=30)).isoformat(),
                "period_end": now.isoformat(),
            },
        ),
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_a, entity_id=servant_id,
            role="servant", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_b, entity_id=servant_id,
            role="servant", attrs={},
        ),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T18IllegalPositionAccumulationTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t18_overlap_below_threshold_no_signal():
    """Servant in 2 organs but overlap only 20 days (< _MIN_OVERLAP_DAYS=30) → no signal."""
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()
    eid_a = uuid.uuid4()
    eid_b = uuid.uuid4()

    # ORGAN_A: [now-100d, now-50d]
    # ORGAN_B: [now-60d, now-40d]  overlap = [now-60d, now-50d] = 10 days < 30
    events = [
        Event(
            id=eid_a, type="remuneracao",
            occurred_at=now - timedelta(days=100),
            source_connector="siape", source_id="rem:t18:neg3",
            value_brl=8_000.0,
            attrs={
                "organ_id": "ORGAN_A",
                "period_start": (now - timedelta(days=100)).isoformat(),
                "period_end": (now - timedelta(days=50)).isoformat(),
            },
        ),
        Event(
            id=eid_b, type="remuneracao",
            occurred_at=now - timedelta(days=60),
            source_connector="siape", source_id="rem:t18:neg4",
            value_brl=9_000.0,
            attrs={
                "organ_id": "ORGAN_B",
                "period_start": (now - timedelta(days=60)).isoformat(),
                "period_end": (now - timedelta(days=40)).isoformat(),
            },
        ),
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_a, entity_id=servant_id,
            role="servant", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_b, entity_id=servant_id,
            role="servant", attrs={},
        ),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T18IllegalPositionAccumulationTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t18_ceaf_flag_fires_without_overlap():
    """CEAF flag set → signal generated even when periods do not overlap."""
    now = datetime.now(timezone.utc)
    servant_id = uuid.uuid4()
    eid_a = uuid.uuid4()
    eid_b = uuid.uuid4()

    # Non-overlapping: ORGAN_A ends at now-100d; ORGAN_B starts at now-90d
    events = [
        Event(
            id=eid_a, type="remuneracao",
            occurred_at=now - timedelta(days=200),
            source_connector="siape", source_id="rem:t18:ceaf1",
            value_brl=8_000.0,
            attrs={
                "organ_id": "ORGAN_A",
                "period_start": (now - timedelta(days=200)).isoformat(),
                "period_end": (now - timedelta(days=100)).isoformat(),
                "ceaf_flag": True,
            },
        ),
        Event(
            id=eid_b, type="remuneracao",
            occurred_at=now - timedelta(days=90),
            source_connector="siape", source_id="rem:t18:ceaf2",
            value_brl=9_000.0,
            attrs={
                "organ_id": "ORGAN_B",
                "period_start": (now - timedelta(days=90)).isoformat(),
                "period_end": (now - timedelta(days=30)).isoformat(),
            },
        ),
    ]
    participants = [
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_a, entity_id=servant_id,
            role="servant", attrs={},
        ),
        EventParticipant(
            id=uuid.uuid4(), event_id=eid_b, entity_id=servant_id,
            role="servant", attrs={},
        ),
    ]

    session = _FakeAsyncSession([events, participants])
    signals = await T18IllegalPositionAccumulationTypology().run(session)

    assert len(signals) == 1
    assert signals[0].typology_code == "T18"
    assert signals[0].factors["ceaf_match"] is True
    assert signals[0].severity.value == "critical"


@pytest.mark.asyncio
async def test_t14_low_meta_score_no_signal():
    """Two typologies triggered but MEDIUM severity → meta_score=2 < 4 → no signal."""
    now = datetime.now(timezone.utc)
    entity_id = uuid.uuid4()
    typ_t01_id = uuid.uuid4()
    typ_t02_id = uuid.uuid4()

    typologies = [
        Typology(id=typ_t01_id, code="T01"),
        Typology(id=typ_t02_id, code="T02"),
    ]

    # MEDIUM weight=1 each → meta_score = 1+1 = 2 < _MIN_META_SCORE=4
    component_signals = [
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t01_id, severity="medium",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=400),
            period_end=now - timedelta(days=200),
        ),
        RiskSignal(
            id=uuid.uuid4(), typology_id=typ_t02_id, severity="medium",
            entity_ids=[str(entity_id)],
            period_start=now - timedelta(days=200),
            period_end=now,
        ),
    ]

    session = _FakeAsyncSession([typologies, component_signals])
    signals = await T14CompoundFavoritismTypology().run(session)

    assert signals == []


@pytest.mark.asyncio
async def test_t16_ratio_exactly_at_boundary_no_signal():
    """Revenue ratio exactly 3.0 (not strictly > threshold) must NOT count as a flag."""
    now = datetime.now(timezone.utc)
    event_id = uuid.uuid4()

    events = [
        Event(
            id=event_id, type="emenda",
            occurred_at=now - timedelta(days=60),
            source_connector="transfere_gov", source_id="emenda:t16:boundary",
            value_brl=300_000.0,
            attrs={
                "plano_trabalho_registered": False,      # flag 1
                "municipality_revenue_brl": 100_000.0,   # ratio = 3.0 exactly — NOT > 3.0
            },
        )
    ]
    # n_flags=1 (only no-work-plan); ratio does NOT flag at exactly 3.0 (strict >)
    session = _FakeAsyncSession([events, []])
    signals = await T16BudgetClientelismTypology().run(session)

    assert signals == []  # n_flags=1 < 2
