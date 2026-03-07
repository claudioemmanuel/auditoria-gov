import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology

# Minimum overlap in days to flag simultaneous positions
_MIN_OVERLAP_DAYS = 90

# Maximum legally permitted simultaneous positions (CF/88 Art. 37, XVI exceptions)
_MAX_LEGAL_POSITIONS = 2


class T18IllegalPositionAccumulationTypology(BaseTypology):
    """T18 — Acúmulo Ilegal de Cargos / Vínculo Funcional Vedado.

    Algorithm:
    1. Query remuneracao events grouped by servant entity_id.
    2. For each servant with records at ≥ 2 distinct organs:
       a. Check if employment periods (occurred_at as proxy) overlap.
       b. If overlap ≥ 30 days → potential illegal accumulation.
    3. Also check: servants appearing in CEAF register who are listed
       as company shareholders (via attrs.ceaf_flag).
    4. Severity: CRITICAL if CEAF flag or 3+ organs; HIGH if 2 organs overlap.

    Legal basis:
    - CF/88, Arts. 37, XVI-XVII (prohibition of multiple simultaneous public positions)
    - Lei 8.112/1990, Arts. 118-120 (illegal accumulation and dismissal penalty)
    - TCU Acórdão 1947/2017 (algorithmic payroll audit trails)
    - CEAF — Federal Administration Expulsion Registry (CGU)

    Note: CPF identifiers from public government sources (LAI 12.527/2011) are stored raw alongside hashes for ER matching.
    """

    @property
    def id(self) -> str:
        return "T18"

    @property
    def name(self) -> str:
        return "Acúmulo Ilegal de Cargos"

    @property
    def required_domains(self) -> list[str]:
        return ["remuneracao", "empresa"]

    @property
    def required_fields(self) -> list[str]:
        return ["organ_id", "period_start", "period_end"]

    @property
    def corruption_types(self) -> list[str]:
        return ["peculato", "nepotismo_clientelismo"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query remuneration events
        stmt = select(Event).where(
            Event.type == "remuneracao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        event_ids = [e.id for e in events]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role == "servant",
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        # Group: servant_entity_id → list of (event, organ_id, period_start, period_end)
        servant_records: dict[str, list[dict]] = defaultdict(list)
        event_map = {str(e.id): e for e in events}

        for p in participants:
            ev = event_map.get(str(p.event_id))
            if not ev:
                continue
            attrs = ev.attrs or {}
            organ_id = attrs.get("organ_id", "unknown")

            # Get employment period from attrs or fall back to occurred_at
            period_start_raw = attrs.get("period_start") or attrs.get("competencia_inicio")
            period_end_raw = attrs.get("period_end") or attrs.get("competencia_fim")

            try:
                period_start = (
                    datetime.fromisoformat(period_start_raw).replace(tzinfo=timezone.utc)
                    if period_start_raw
                    else ev.occurred_at or window_start
                )
                period_end = (
                    datetime.fromisoformat(period_end_raw).replace(tzinfo=timezone.utc)
                    if period_end_raw
                    else (ev.occurred_at or window_start) + timedelta(days=30)
                )
            except (ValueError, TypeError):
                period_start = ev.occurred_at or window_start
                period_end = period_start + timedelta(days=30)

            servant_records[str(p.entity_id)].append({
                "event_id": str(ev.id),
                "organ_id": organ_id,
                "period_start": period_start,
                "period_end": period_end,
                "value_brl": ev.value_brl or 0,
                "ceaf_flag": attrs.get("ceaf_flag", False),
                "event": ev,
            })

        signals: list[RiskSignalOut] = []

        for servant_id, records in servant_records.items():
            # Group by organ
            organs: dict[str, list[dict]] = defaultdict(list)
            for rec in records:
                organs[rec["organ_id"]].append(rec)

            distinct_organs = list(organs.keys())
            if len(distinct_organs) < 2:
                continue

            # Check CEAF flag (any record marked)
            ceaf_match = any(rec.get("ceaf_flag") for rec in records)

            # Check for overlapping periods across different organs
            overlap_pairs: list[dict] = []
            for i, org_a in enumerate(distinct_organs):
                for org_b in distinct_organs[i + 1:]:
                    for rec_a in organs[org_a]:
                        for rec_b in organs[org_b]:
                            # Compute overlap
                            overlap_start = max(rec_a["period_start"], rec_b["period_start"])
                            overlap_end = min(rec_a["period_end"], rec_b["period_end"])
                            overlap_days = (overlap_end - overlap_start).days

                            if overlap_days >= _MIN_OVERLAP_DAYS:
                                overlap_pairs.append({
                                    "organ_a": org_a,
                                    "organ_b": org_b,
                                    "overlap_days": overlap_days,
                                    "period_start": overlap_start,
                                    "period_end": overlap_end,
                                })

            if not overlap_pairs and not ceaf_match:
                continue

            n_organs = len(distinct_organs)
            max_overlap = max(
                (p["overlap_days"] for p in overlap_pairs), default=0
            )

            # Determine severity
            if ceaf_match or n_organs >= 3:
                severity = SignalSeverity.CRITICAL
                confidence = 0.88 if ceaf_match else 0.78
            elif overlap_pairs:
                severity = SignalSeverity.HIGH
                confidence = min(0.82, 0.60 + max_overlap / 365 * 0.22)
            else:
                severity = SignalSeverity.MEDIUM
                confidence = 0.55

            total_value = sum(rec["value_brl"] for rec in records)
            all_period_starts = [p["period_start"] for p in overlap_pairs] + [r["period_start"] for r in records]
            all_period_ends = [p["period_end"] for p in overlap_pairs] + [r["period_end"] for r in records]

            signal_period_start = min(all_period_starts) if all_period_starts else window_start
            signal_period_end = max(all_period_ends) if all_period_ends else window_end

            try:
                servant_uuid = [uuid.UUID(servant_id)]
            except ValueError:
                servant_uuid = []

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Acúmulo ilegal de cargos — "
                    f"{n_organs} órgão(s) simultâneo(s)"
                    + (" [CEAF]" if ceaf_match else "")
                ),
                summary=(
                    f"Servidor identificado em {n_organs} órgão(s) distintos: "
                    f"{', '.join(distinct_organs[:3])}{'...' if n_organs > 3 else ''}. "
                    + (
                        f"Sobreposição máxima: {max_overlap} dias. "
                        if overlap_pairs else ""
                    )
                    + ("Servidor consta no CEAF. " if ceaf_match else "")
                    + f"Remuneração total: R$ {total_value:,.2f}."
                ),
                factors={
                    "overlap_days": max_overlap,
                    "n_organs": n_organs,
                    "ceaf_match": ceaf_match,
                    "contract_value_brl": round(total_value, 2),
                    "n_overlap_pairs": len(overlap_pairs),
                    "organs": distinct_organs[:5],
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.ENTITY,
                        ref_id=servant_id,
                        description=(
                            f"Servidor em {n_organs} órgão(s)"
                            + (" — consta no CEAF" if ceaf_match else "")
                        ),
                    ),
                ] + [
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=rec["event_id"],
                        description=(
                            f"Remuneração em {rec['organ_id']} "
                            f"R$ {rec['value_brl']:,.2f}"
                        ),
                    )
                    for rec in records[:5]
                ],
                entity_ids=servant_uuid,
                event_ids=[uuid.UUID(rec["event_id"]) for rec in records[:10] if rec.get("event_id")],
                period_start=signal_period_start,
                period_end=signal_period_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
