import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from openwatch_models.orm import RiskSignal, Typology
from openwatch_models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from openwatch_typologies.base import BaseTypology

# Typology codes that compose this compound signal.
# Includes all procurement-fraud typologies that can indicate systematic favoritism:
# T01 (concentration), T02 (low competition), T04 (amendments), T05 (overpricing),
# T06 (shell company), T07 (cartel), T11 (spreadsheet manipulation),
# T12 (directed tender), T15 (false sole-source).
_COMPONENT_TYPOLOGIES = {"T01", "T02", "T04", "T05", "T06", "T07", "T11", "T12", "T15"}

# Severity weights for meta-score
_SEVERITY_WEIGHTS = {
    "critical": 3,
    "high": 2,
    "medium": 1,
    "low": 0,
}

# Minimum meta-score to generate a compound signal
_MIN_META_SCORE = 4

# Minimum number of distinct component typologies triggered
_MIN_COMPONENT_COUNT = 2

# Minimum temporal span (days) to confirm persistence
_MIN_TEMPORAL_SPAN_DAYS = 180


class T14CompoundFavoritismTypology(BaseTypology):
    """T14 — Sequência de Favorecimento Contratual (Compound Favoritism).

    Meta-typology: composes signals from T01, T02, T04, T05.

    Algorithm:
    1. Load recent RiskSignal records for T01, T02, T04, T05 via Typology join.
    2. For each RiskSignal, extract its entity_ids (JSONB list).
    3. Group signals by entity_id:
       collect (typology_code, severity, signal_id, period) per entity.
    4. Flag entities where:
       - ≥ 2 distinct component typologies triggered
       - meta_score = sum(severity_weight * n_signals) > MIN_META_SCORE
       - temporal span between first/last signal ≥ 180 days
    5. Severity: CRITICAL if meta_score ≥ 9, HIGH if ≥ 6, MEDIUM otherwise.

    Legal basis:
    - CP Arts. 317/333 (passive/active corruption)
    - Lei 12.846/2013, Art. 5° (harmful acts against public administration)
    - Lei 8.429/92, Art. 10 (administrative improbity causing financial damage)
    """

    @property
    def id(self) -> str:
        return "T14"

    @property
    def name(self) -> str:
        return "Sequência de Favorecimento Contratual"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return []

    @property
    def corruption_types(self) -> list[str]:
        return ["corrupcao_ativa_passiva", "fraude_licitatoria"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "sistemica"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # Step 1: get Typology IDs for component codes
        typ_stmt = select(Typology).where(
            Typology.code.in_(_COMPONENT_TYPOLOGIES),
        )
        typ_result = await session.execute(typ_stmt)
        typologies = typ_result.scalars().all()

        if not typologies:
            return []

        typology_id_to_code = {str(t.id): t.code for t in typologies}
        typology_ids = [t.id for t in typologies]

        # Step 2: load recent component signals
        signals_stmt = select(RiskSignal).where(
            RiskSignal.typology_id.in_(typology_ids),
            RiskSignal.period_start >= window_start,
        )
        sig_result = await session.execute(signals_stmt)
        component_signals = sig_result.scalars().all()

        if not component_signals:
            return []

        # Step 3: group by entity_id
        # entity_ids in RiskSignal is JSONB list of UUID strings
        entity_signal_map: dict[str, list[dict]] = defaultdict(list)

        for sig in component_signals:
            typ_code = typology_id_to_code.get(str(sig.typology_id), "?")
            entity_ids_raw = sig.entity_ids or []
            for entity_id_str in entity_ids_raw:
                entity_signal_map[str(entity_id_str)].append({
                    "typology_code": typ_code,
                    "severity": sig.severity,
                    "signal_id": str(sig.id),
                    "period_start": sig.period_start,
                    "period_end": sig.period_end,
                    "event_ids": [str(eid) for eid in (sig.event_ids or [])],
                })

        output_signals: list[RiskSignalOut] = []

        for entity_id_str, entity_signals in entity_signal_map.items():
            # Count distinct typologies
            triggered_codes = {s["typology_code"] for s in entity_signals}
            if len(triggered_codes) < _MIN_COMPONENT_COUNT:
                continue

            # Compute meta-score (severity may be stored as enum name — normalise to lowercase)
            meta_score = sum(
                _SEVERITY_WEIGHTS.get(
                    s["severity"].lower() if isinstance(s["severity"], str) else s["severity"],
                    0,
                )
                for s in entity_signals
            )

            if meta_score < _MIN_META_SCORE:
                continue

            # Check temporal span
            dates = [
                s["period_start"] for s in entity_signals
                if s["period_start"] is not None
            ] + [
                s["period_end"] for s in entity_signals
                if s["period_end"] is not None
            ]

            if dates:
                first_date = min(dates)
                last_date = max(dates)
                span_days = (last_date - first_date).days
            else:
                span_days = 0

            if span_days < _MIN_TEMPORAL_SPAN_DAYS:
                continue

            # Determine severity
            if meta_score >= 9:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.88, 0.70 + meta_score * 0.02)
            elif meta_score >= 6:
                severity = SignalSeverity.HIGH
                confidence = 0.72
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.58

            sub_typologies = sorted(triggered_codes)

            entity_uuid: list[uuid.UUID] = []
            try:
                entity_uuid = [uuid.UUID(entity_id_str)]
            except ValueError:
                pass

            # Aggregate event_ids from all component signals for this entity
            all_event_ids: list[uuid.UUID] = []
            seen_eids: set[str] = set()
            for s in entity_signals:
                for eid_str in s.get("event_ids", []):
                    if eid_str not in seen_eids:
                        seen_eids.add(eid_str)
                        try:
                            all_event_ids.append(uuid.UUID(eid_str))
                        except ValueError:
                            pass

            output_signals.append(RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Favorecimento contratual composto — "
                    f"{len(triggered_codes)} tipologia(s): "
                    f"{', '.join(sub_typologies)}"
                ),
                summary=(
                    f"Entidade acumulou {len(entity_signals)} sinal(is) "
                    f"de {len(triggered_codes)} tipologia(s) distintas "
                    f"({', '.join(sub_typologies)}) ao longo de {span_days} dias. "
                    f"Score meta-composto: {meta_score}."
                ),
                factors={
                    "n_signals_triggered": len(entity_signals),
                    "meta_score": meta_score,
                    "temporal_span_days": span_days,
                    "sub_typologies": ", ".join(sub_typologies),
                    "n_component_typologies": len(triggered_codes),
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.ENTITY,
                        ref_id=entity_id_str,
                        description=(
                            f"Entidade com sinais persistentes de favorecimento: "
                            f"{', '.join(sub_typologies)}"
                        ),
                    ),
                ] + [
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=s["signal_id"],
                        description=f"Sinal {s['typology_code']} — severidade {s['severity']}",
                    )
                    for s in entity_signals[:5]
                ],
                entity_ids=entity_uuid,
                event_ids=all_event_ids[:50],
                period_start=first_date if dates else None,
                period_end=last_date if dates else None,
                created_at=datetime.now(timezone.utc),
            ))

        return output_signals
