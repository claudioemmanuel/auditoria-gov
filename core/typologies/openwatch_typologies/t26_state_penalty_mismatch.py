import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

from sqlalchemy import select

from openwatch_models.orm import Event, EventParticipant
from openwatch_utils.query import execute_chunked_in
from openwatch_models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from openwatch_typologies.base import BaseTypology


class T26StatePenaltyMismatchTypology(BaseTypology):
    """T26 — State Audit Court Penalty x Active Contract Mismatch.

    Extends T08 (federal sanctions) to state-level data from TCE courts
    (e.g. TCE-RJ, TCE-SP).  Detects entities that hold active procurement
    contracts while also carrying penalties issued by a state audit court.

    Algorithm:
    1. Fetch all ``penalidade_tce_rj`` events and their penalised participants.
    2. Fetch all ``contrato`` / ``licitacao`` events and their supplier
       participants, filtering to contracts whose occurred_at is within the
       last 2 years (considered "active").
    3. For each entity present in both sets, check temporal overlap:
       a. CRITICAL (0.95): penalty is currently active AND contract is active.
       b. HIGH (0.85): penalty expired recently (< 1 year) but contract
          is still active — residual risk.
    """

    @property
    def id(self) -> str:
        return "T26"

    @property
    def name(self) -> str:
        return "Penalidade TCE x Contrato Ativo"

    @property
    def required_domains(self) -> list[str]:
        return ["penalidade_tce_rj", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["penalty_start", "penalty_end", "contract_start", "contract_end"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        now = datetime.now(timezone.utc)
        active_cutoff = now - timedelta(days=730)  # 2 years

        # ── Step 1: Load penalty events from state audit courts ──────────
        penalty_stmt = select(Event).where(Event.type == "penalidade_tce_rj")
        penalty_result = await session.execute(penalty_stmt)
        penalties = penalty_result.scalars().all()

        if not penalties:
            return []

        penalty_event_ids = [p.id for p in penalties]
        penalty_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["sanctioned", "penalizado", "target"]),
            ),
            penalty_event_ids,
        )

        entity_penalties: dict[str, list[dict]] = defaultdict(list)
        penalty_map: dict[str, Event] = {str(p.id): p for p in penalties}

        for pp in penalty_participants:
            evt = penalty_map.get(str(pp.event_id))
            if evt is None:
                continue

            penalty_start = (
                evt.attrs.get("penalty_start")
                or evt.attrs.get("data_inicio")
                or (evt.occurred_at.isoformat() if evt.occurred_at else None)
            )
            penalty_end = evt.attrs.get("penalty_end") or evt.attrs.get("data_fim")
            penalty_type = evt.attrs.get("penalty_type") or evt.attrs.get("tipo_penalidade") or "penalidade_tce"

            if penalty_start:
                entity_penalties[str(pp.entity_id)].append({
                    "event_id": evt.id,
                    "penalty_start": penalty_start,
                    "penalty_end": penalty_end,
                    "penalty_type": penalty_type,
                    "description": evt.description,
                })

        if not entity_penalties:
            return []

        # ── Step 2: Load active contracts (within last 2 years) ──────────
        contract_stmt = (
            select(Event)
            .where(
                Event.type.in_(["contrato", "licitacao"]),
                Event.occurred_at >= active_cutoff,
            )
        )
        contract_result = await session.execute(contract_stmt)
        contracts = contract_result.scalars().all()

        if not contracts:
            return []

        contract_ids = [c.id for c in contracts]
        contract_map: dict[str, Event] = {str(c.id): c for c in contracts}

        contract_parts = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["supplier", "winner", "contractor"]),
            ),
            contract_ids,
        )

        # ── Step 3: Detect overlaps ──────────────────────────────────────
        signals: list[RiskSignalOut] = []

        for cp in contract_parts:
            entity_id_str = str(cp.entity_id)
            if entity_id_str not in entity_penalties:
                continue

            contract = contract_map.get(str(cp.event_id))
            if contract is None:
                continue

            contract_start_raw = (
                contract.attrs.get("contract_start")
                or contract.attrs.get("vigencia_inicio")
                or (contract.occurred_at.isoformat() if contract.occurred_at else None)
            )
            contract_end_raw = (
                contract.attrs.get("contract_end")
                or contract.attrs.get("vigencia_fim")
            )

            if not contract_start_raw:
                continue

            try:
                c_start = _parse_datetime(contract_start_raw)
            except (ValueError, TypeError):
                continue

            c_end: datetime | None = None
            if contract_end_raw:
                try:
                    c_end = _parse_datetime(contract_end_raw)
                except (ValueError, TypeError):
                    pass
            if c_end is None:
                c_end = c_start + timedelta(days=365)

            for penalty in entity_penalties[entity_id_str]:
                try:
                    p_start = _parse_datetime(penalty["penalty_start"])
                except (ValueError, TypeError):
                    continue

                p_end: datetime | None = None
                if penalty["penalty_end"]:
                    try:
                        p_end = _parse_datetime(penalty["penalty_end"])
                    except (ValueError, TypeError):
                        pass

                # Penalties without end date are treated as ongoing.
                if p_end is None:
                    p_end = now + timedelta(days=365 * 10)

                # Temporal overlap check
                if not (c_start <= p_end and c_end >= p_start):
                    continue

                penalty_active_now = p_start <= now <= p_end

                if penalty_active_now:
                    severity = SignalSeverity.CRITICAL
                    confidence = 0.95
                    situation = "Penalidade TCE ativa com contrato vigente"
                else:
                    severity = SignalSeverity.HIGH
                    confidence = 0.85
                    situation = "Penalidade TCE recente com contrato vigente"

                contract_value = contract.value_brl
                value_str = f"R$ {contract_value:,.2f}" if contract_value else "N/A"

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title="Entidade com penalidade TCE e contrato ativo",
                    summary=(
                        f"{situation}. "
                        f"Penalidade ({penalty['penalty_type']}): "
                        f"{p_start.strftime('%d/%m/%Y')} a {p_end.strftime('%d/%m/%Y')}. "
                        f"Contrato: {c_start.strftime('%d/%m/%Y')} a "
                        f"{c_end.strftime('%d/%m/%Y')}, valor {value_str}."
                    ),
                    factors={
                        "penalty_type": penalty["penalty_type"],
                        "penalty_details": penalty["description"],
                        "penalty_start": p_start.isoformat(),
                        "penalty_end": p_end.isoformat(),
                        "penalty_active_now": penalty_active_now,
                        "contract_start": c_start.isoformat(),
                        "contract_end": c_end.isoformat(),
                        "contract_value_brl": contract_value,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(penalty["event_id"]),
                            description=f"Penalidade TCE — {penalty['penalty_type']}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(contract.id),
                            description=f"Contrato {value_str}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.ENTITY,
                            ref_id=entity_id_str,
                            description="Entidade penalizada pelo TCE",
                        ),
                    ],
                    entity_ids=[cp.entity_id],
                    event_ids=[penalty["event_id"], contract.id],
                    period_start=max(p_start, c_start),
                    period_end=min(p_end, c_end),
                    created_at=now,
                )
                signals.append(signal)

        return signals


def _parse_datetime(value: object) -> datetime:
    """Parse a datetime from ISO-8601, YYYY-MM-DD, or DD/MM/YYYY strings."""
    raw = str(value).strip()
    if not raw:
        raise ValueError("empty datetime string")

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        else:
            raise

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
