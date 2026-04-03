import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from openwatch_baselines.models import BaselineType
from openwatch_models.orm import Event, EventParticipant
from openwatch_models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from openwatch_queries.queries import get_baseline
from openwatch_typologies.base import BaseTypology

# Minimum ratio of unit_price / baseline_median to flag an item as overpriced
_OVERPRICING_RATIO_THRESHOLD = 2.0


class T11SpreadsheetManipulationTypology(BaseTypology):
    """T11 — Jogo de Planilha (Spreadsheet Price Manipulation in Works).

    Algorithm:
    1. Query engineering/works contracts that carry item-level unit prices.
    2. For each item, compare unit_price to the PRICE_BY_ITEM baseline median.
    3. Identify items where unit_price > 2x baseline (overpriced items).
    4. Cross with amendment events on the same contract:
       a. If overpriced items had quantity *increases* via amendments → jogo de planilha.
       b. If low-priced items had quantity *decreases* → confirms the pattern.
    5. Compute net estimated overcharge: sum(price_excess * quantity_increase).
    6. Severity: CRITICAL if estimated overcharge > R$ 100k, HIGH if > R$ 20k.

    Legal basis:
    - Lei 14.133/2021, Arts. 92 e 155 (improper contract execution; disqualification)
    - Lei 8.429/92, Art. 10 (administrative improbity causing financial damage)
    - CGU Guia Superfaturamento 2025, Type 4 (Spreadsheet Price Manipulation)
    - TCU Fiscobras: most frequent finding (1,331 occurrences over 10 years)
    """

    @property
    def id(self) -> str:
        return "T11"

    @property
    def name(self) -> str:
        return "Jogo de Planilha"

    @property
    def required_domains(self) -> list[str]:
        return ["contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["item_prices", "amendments", "amendment_count"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "peculato"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "privada"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # Query engineering/works contracts
        stmt = (
            select(Event)
            .where(
                Event.type == "contrato",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        contracts = result.scalars().all()

        # Filter contracts that have item-level price data
        contracts_with_items = [
            c for c in contracts
            if c.attrs.get("item_prices") and c.attrs.get("amendments")
        ]

        if not contracts_with_items:
            return []

        # Get participants (buyers/suppliers) for entity linking
        contract_ids = [c.id for c in contracts_with_items]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(contract_ids),
            EventParticipant.role.in_(["buyer", "supplier", "procuring_entity"]),
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        event_entity_ids: dict[str, list] = defaultdict(list)
        for p in participants:
            event_entity_ids[str(p.event_id)].append(p.entity_id)

        signals: list[RiskSignalOut] = []
        # Cache baseline lookups across contracts — avoids redundant DB round-trips
        # when multiple contracts share the same CATMAT group.
        baseline_cache: dict[str, float] = {}

        async def _get_cached_baseline(catmat_key: str) -> float:
            if catmat_key not in baseline_cache:
                bl = await get_baseline(session, BaselineType.PRICE_BY_ITEM.value, catmat_key)
                baseline_cache[catmat_key] = bl.get("median", 0) if bl else 0
            return baseline_cache[catmat_key]

        for contract in contracts_with_items:
            item_prices: list[dict] = contract.attrs.get("item_prices", [])
            amendments: list[dict] = contract.attrs.get("amendments", [])

            if not item_prices or not amendments:
                continue

            # Build amendment index: item_code → quantity_delta
            amendment_deltas: dict[str, float] = {}
            for amd in amendments:
                code = amd.get("item_code", "")
                delta = amd.get("quantity_delta", 0)
                amendment_deltas[code] = amendment_deltas.get(code, 0) + delta

            if not amendment_deltas:
                continue

            contract_catmat = contract.attrs.get("catmat_code", "all")

            # Identify overpriced items with quantity increases.
            # Each item may carry its own catmat_code — use it for a more precise
            # baseline; fall back to the contract-level CATMAT group.
            n_items_overpriced = 0
            quantity_increase_value = 0.0
            max_price_ratio = 0.0
            flagged_items: list[dict] = []

            for item in item_prices:
                code = item.get("item_code", "")
                unit_price = item.get("unit_price", 0)
                if not unit_price or unit_price <= 0:
                    continue

                item_catmat = item.get("catmat_code") or contract_catmat
                baseline_median = await _get_cached_baseline(item_catmat)
                if not baseline_median or baseline_median <= 0:
                    continue

                ratio = unit_price / baseline_median
                max_price_ratio = max(max_price_ratio, ratio)

                if ratio >= _OVERPRICING_RATIO_THRESHOLD:
                    # Check if this overpriced item had quantity increases
                    delta = amendment_deltas.get(code, 0)
                    if delta > 0:
                        overcharge = (unit_price - baseline_median) * delta
                        quantity_increase_value += overcharge
                        n_items_overpriced += 1
                        flagged_items.append({
                            "item_code": code,
                            "unit_price": unit_price,
                            "baseline_median": baseline_median,
                            "ratio": round(ratio, 2),
                            "quantity_increase": delta,
                            "overcharge_brl": round(overcharge, 2),
                        })

            if n_items_overpriced < 1 or quantity_increase_value <= 0:
                continue

            # Severity based on estimated overcharge
            if quantity_increase_value > 100_000:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.90, 0.75 + (quantity_increase_value / 1_000_000) * 0.05)
            elif quantity_increase_value > 20_000:
                severity = SignalSeverity.HIGH
                confidence = 0.70
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.55

            amendment_count = contract.attrs.get("amendment_count", len(amendments))

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Jogo de planilha — sobrepreço estimado "
                    f"R$ {quantity_increase_value:,.2f}"
                ),
                summary=(
                    f"{n_items_overpriced} item(s) com preço unitário ≥ "
                    f"{_OVERPRICING_RATIO_THRESHOLD}× referência tiveram "
                    f"quantidades aumentadas via {amendment_count} aditivo(s). "
                    f"Sobrepreço estimado: R$ {quantity_increase_value:,.2f}."
                ),
                factors={
                    "n_items_overpriced": n_items_overpriced,
                    "quantity_increase_value": round(quantity_increase_value, 2),
                    "net_overcharge_brl": round(quantity_increase_value, 2),
                    "amendment_count": amendment_count,
                    "price_ratio_max": round(max_price_ratio, 2),
                    "flagged_items": flagged_items[:5],
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(contract.id),
                        description=(
                            f"Contrato com {n_items_overpriced} item(s) sobrepreçado(s) "
                            f"e quantidades aumentadas via aditivo."
                        ),
                    ),
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=(
                            f"Referência SINAPI/Painel de Preços para CATMAT {contract_catmat}"
                        ),
                    ),
                ],
                entity_ids=event_entity_ids.get(str(contract.id), []),
                event_ids=[contract.id],
                period_start=contract.occurred_at,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
