import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from shared.baselines.compute import _CATMAT_MISSING
from shared.baselines.models import BaselineType
from shared.models.orm import Event, EventParticipant
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.repo.queries import get_baseline
from shared.typologies.base import BaseTypology


class T01ConcentrationTypology(BaseTypology):
    """T01 — Supplier Concentration.

    Algorithm:
    1. For each procuring entity + CATMAT/CATSER group in the analysis window:
       a. Compute HHI (Herfindahl-Hirschman Index) across awarded suppliers.
       b. Compute top-1% and top-3% supplier share by value.
    2. Compare against BASELINE (HHI_DISTRIBUTION for same scope).
    3. Flag if HHI > baseline p90, or top1% share > baseline p95.
    4. Severity: HIGH if HHI > p95, MEDIUM if > p90.
    """

    @property
    def id(self) -> str:
        return "T01"

    @property
    def name(self) -> str:
        return "Concentração em Fornecedor"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["value_brl", "winner_entity_id", "catmat_group"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_start, window_end = await self.resolve_window(session, self.required_domains)

        # 1. Query licitacao events in window
        stmt = (
            select(Event)
            .where(
                Event.type == "licitacao",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
                Event.value_brl.isnot(None),
                Event.value_brl > 0,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        event_ids = [e.id for e in events]

        # Get winners
        winner_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role == "winner",
        )
        winner_result = await session.execute(winner_stmt)
        winners = winner_result.scalars().all()

        # Get procuring entities
        procurer_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
            EventParticipant.role.in_(["procuring_entity", "buyer"]),
        )
        procurer_result = await session.execute(procurer_stmt)
        procurers = procurer_result.scalars().all()

        # Licitações sem adjudicação não têm vencedor real e distorcem o HHI
        _VOID = frozenset({"deserta", "fracassada", "revogada", "anulada", "cancelada"})

        # Map event -> info; skip events with sentinel/null CATMAT (same guard as baselines)
        # and skip void situations (no award → no real winner)
        event_info: dict[str, dict] = {}
        for e in events:
            catmat_raw = e.attrs.get("catmat_group", "") or ""
            if str(catmat_raw).strip().lower() in _CATMAT_MISSING:
                continue
            if e.attrs.get("situacao", "").lower().strip() in _VOID:
                continue
            event_info[str(e.id)] = {
                "catmat_group": catmat_raw,
                "value_brl": e.value_brl or 0,
                "occurred_at": e.occurred_at,
                "description": e.description,
                "source_id": e.source_id,
            }

        # Map event -> procurer
        event_procurer: dict[str, uuid.UUID] = {}
        for p in procurers:
            event_procurer[str(p.event_id)] = p.entity_id

        # 2. Group by (procuring_entity, catmat_group)
        # key = (procurer_id, catmat_group) -> {winner_id: total_value}
        groups: dict[tuple, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        group_events: dict[tuple, list[str]] = defaultdict(list)

        for w in winners:
            info = event_info.get(str(w.event_id))
            if not info:
                continue
            procurer_id = event_procurer.get(str(w.event_id))
            if procurer_id is None:
                procurer_id = uuid.UUID(int=0)  # fallback

            key = (str(procurer_id), info["catmat_group"])
            groups[key][str(w.entity_id)] += info["value_brl"]
            group_events[key].append(str(w.event_id))

        # 3. Compute HHI per group and compare with baseline
        baseline = await get_baseline(
            session,
            BaselineType.HHI_DISTRIBUTION.value,
            "national::all",
        )

        p90 = baseline.get("p90", 0.25) if baseline else 0.25
        p95 = baseline.get("p95", 0.40) if baseline else 0.40

        signals: list[RiskSignalOut] = []

        for key, winner_totals in groups.items():
            procurer_id_str, catmat_group = key
            # Skip groups with no identifiable procurer — cannot attribute to an organ
            if procurer_id_str == str(uuid.UUID(int=0)):
                continue
            total_value = sum(winner_totals.values())
            if total_value <= 0:
                continue

            # Compute HHI
            shares = [v / total_value for v in winner_totals.values()]
            hhi = sum(s ** 2 for s in shares)

            # Top-1 share
            top1_share = max(shares) if shares else 0

            # Determine severity
            if hhi <= p90:
                continue

            if hhi > p95 or top1_share > 0.80:
                severity = SignalSeverity.HIGH
                confidence = max(0.60, min(0.95, 0.7 + (hhi - p95) * 2))
            else:
                severity = SignalSeverity.MEDIUM
                confidence = min(0.85, 0.5 + (hhi - p90) * 3)

            n_winners = len(winner_totals)
            event_id_list = group_events.get(key, [])

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=f"Alta concentração em fornecedor — {catmat_group}",
                summary=(
                    f"HHI de {hhi:.4f} detectado para o grupo CATMAT {catmat_group}. "
                    f"Top fornecedor detém {top1_share:.1%} do valor total. "
                    f"{n_winners} fornecedor(es) para R$ {total_value:,.2f} em contratos."
                ),
                factors={
                    "hhi": round(hhi, 4),
                    "top1_share": round(top1_share, 4),
                    "n_winners": n_winners,
                    "total_value_brl": round(total_value, 2),
                    "baseline_p90": round(p90, 4),
                    "baseline_p95": round(p95, 4),
                    "catmat_group": catmat_group,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=f"HHI baseline p90={p90:.4f}, p95={p95:.4f}",
                    ),
                ],
                entity_ids=(
                    ([uuid.UUID(procurer_id_str)] if procurer_id_str != str(uuid.UUID(int=0)) else [])
                    + [uuid.UUID(wid) for wid in winner_totals if wid != procurer_id_str]
                ),
                event_ids=[uuid.UUID(eid) for eid in event_id_list[:20]],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
