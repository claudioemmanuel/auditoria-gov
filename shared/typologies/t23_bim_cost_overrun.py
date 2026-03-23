import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Event
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology

# Minimum deviation from BIM reference cost to emit signal (%)
_OVERRUN_THRESHOLD_PCT = 20.0
# SINAPI deviation thresholds by severity
_HIGH_OVERRUN_PCT = 40.0
_CRITICAL_OVERRUN_PCT = 80.0


class T23BimCostOverrunTypology(BaseTypology):
    """T23 — Superfaturamento via BIM (stub).

    Legal basis:
    - Lei 14.133/2021, Art. 122 §3° (orçamento BIM em obras acima de R$ 75M)
    - Decreto 9.983/2019 (estratégia nacional de disseminação do BIM)
    - SINAPI — Sistema Nacional de Pesquisa de Custos e Índices da Construção Civil
    - Lei 8.429/1992, Art. 9°, XI (dano ao erário por sobrepreço em obras)
    - Acórdão TCU 2.622/2013 (sobrepreço em obras públicas — metodologia)

    Status: STUB — requires BIM cost data connector (orcamento_bim event type).
    Returns [] until BIM ingestion pipeline is operational.

    Planned Algorithm (when data available):
    1. Query events with type == "orcamento_bim" in 5-year window.
       Attrs expected: {
         "sinapi_reference_brl": float,  # SINAPI unit price reference
         "contracted_unit_price_brl": float,  # actual contracted price
         "quantity": float,  # BIM quantity (m², m³, kg, etc.)
         "service_code": str,  # SINAPI service code
         "obra_id": str,  # contract/obra identifier
       }
    2. Early exit if no orcamento_bim events found (BIM data not loaded).
    3. For each BIM item: compute overrun_pct =
       (contracted_unit_price_brl - sinapi_reference_brl) / sinapi_reference_brl * 100
    4. Filter items where overrun_pct >= _OVERRUN_THRESHOLD_PCT.
    5. Group by obra_id; compute total_overrun_brl per obra.
    6. Emit signal per obra with >= 3 overrun items.
    7. Severity:
       - CRITICAL: median overrun_pct >= _CRITICAL_OVERRUN_PCT (80%)
       - HIGH:     median overrun_pct >= _HIGH_OVERRUN_PCT (40%)
       - MEDIUM:   otherwise
    """

    @property
    def id(self) -> str:
        return "T23"

    @property
    def name(self) -> str:
        return "Superfaturamento BIM"

    @property
    def required_domains(self) -> list[str]:
        return ["orcamento_bim"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "peculato"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)

        # Step 1: Query BIM cost events
        stmt = select(Event).where(
            Event.type == "orcamento_bim",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        bim_events = result.scalars().all()

        # Step 2: Early exit — BIM connector not yet operational
        if not bim_events:
            return []

        # ── Steps 3-7: active when BIM data is available ─────────────────────
        from collections import defaultdict

        obra_items: dict[str, list[tuple[Event, float]]] = defaultdict(list)

        for event in bim_events:
            attrs = event.attrs
            sinapi_ref = attrs.get("sinapi_reference_brl")
            contracted = attrs.get("contracted_unit_price_brl")
            obra_id = str(attrs.get("obra_id", str(event.id)))

            if sinapi_ref is None or contracted is None or float(sinapi_ref) <= 0:
                continue

            overrun_pct = (float(contracted) - float(sinapi_ref)) / float(sinapi_ref) * 100.0
            if overrun_pct >= _OVERRUN_THRESHOLD_PCT:
                obra_items[obra_id].append((event, overrun_pct))

        signals: list[RiskSignalOut] = []

        for obra_id, items in obra_items.items():
            if len(items) < 3:
                continue

            overrun_pcts = [pct for _, pct in items]
            median_overrun = sorted(overrun_pcts)[len(overrun_pcts) // 2]
            total_overrun_brl = sum(
                (e.value_brl or 0.0) * (pct / 100.0) for e, pct in items
            )

            if median_overrun >= _CRITICAL_OVERRUN_PCT:
                severity = SignalSeverity.CRITICAL
                confidence = 0.82
            elif median_overrun >= _HIGH_OVERRUN_PCT:
                severity = SignalSeverity.HIGH
                confidence = 0.70
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.55

            event_ids = [e.id for e, _ in items[:20]]
            evidence_refs = [
                EvidenceRef(
                    ref_type=RefType.EVENT,
                    ref_id=str(e.id),
                    description=(
                        f"Item com sobrepreço de {pct:.1f}% acima do SINAPI"
                    ),
                )
                for e, pct in items[:5]
            ]

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Possível superfaturamento BIM — {len(items)} itens "
                    f"acima de {_OVERRUN_THRESHOLD_PCT:.0f}% do SINAPI"
                ),
                summary=(
                    f"Obra {obra_id}: {len(items)} itens com preço contratado "
                    f"acima da referência SINAPI. Desvio mediano: "
                    f"{median_overrun:.1f}%. Sobrepreço estimado: "
                    f"R$ {total_overrun_brl:,.2f}."
                ),
                factors={
                    "obra_id": obra_id,
                    "n_overrun_items": len(items),
                    "median_overrun_pct": round(median_overrun, 2),
                    "total_overrun_brl": round(total_overrun_brl, 2),
                },
                evidence_refs=evidence_refs,
                entity_ids=[],
                event_ids=event_ids,
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
