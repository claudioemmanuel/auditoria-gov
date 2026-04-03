import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

from sqlalchemy import select

from openwatch_models.orm import Entity, Event, EventParticipant
from openwatch_utils.query import execute_chunked_in
from openwatch_models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from openwatch_typologies.base import BaseTypology


class T08SanctionsMismatchTypology(BaseTypology):
    """T08 — Sanctions vs Active Contract Mismatch.

    Algorithm:
    1. For each sanctioned entity (CEIS/CNEP):
       a. Get sanction period (start_date → end_date).
    2. Find all contracts where the entity is a supplier:
       a. Check temporal overlap: contract_start <= sanction_end
          AND contract_end >= sanction_start.
    3. Flag overlapping contracts.
    4. Severity: CRITICAL if contract signed AFTER sanction start,
       HIGH if pre-existing contract overlaps sanction period.
    """

    @property
    def id(self) -> str:
        return "T08"

    @property
    def name(self) -> str:
        return "Sanção x Contrato"

    @property
    def required_domains(self) -> list[str]:
        return ["sancao", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["sanction_start", "sanction_end", "contract_start", "contract_end"]

    async def run(self, session) -> list[RiskSignalOut]:
        # 1. Get all sanction events (CEIS/CNEP)
        sanction_stmt = (
            select(Event)
            .where(
                Event.type == "sancao",
            )
        )
        sanction_result = await session.execute(sanction_stmt)
        sanctions = sanction_result.scalars().all()

        if not sanctions:
            return []

        # Get sanctioned entities via participants (chunked to avoid asyncpg param limit)
        sanction_event_ids = [s.id for s in sanctions]
        sanction_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(
                    ["sanctioned", "target", "supplier", "sancionado"]
                ),
            ),
            sanction_event_ids,
        )

        # Map entity_id -> sanction events
        entity_sanctions: dict[str, list[dict]] = defaultdict(list)
        sanction_map: dict[str, Event] = {str(s.id): s for s in sanctions}

        for p in sanction_participants:
            s = sanction_map.get(str(p.event_id))
            if s is None:
                continue

            sanction_start = (
                s.attrs.get("sanction_start")
                or s.attrs.get("data_inicio")
                or (s.occurred_at.isoformat() if s.occurred_at else None)
            )
            sanction_end = s.attrs.get("sanction_end") or s.attrs.get("data_fim")

            if sanction_start:
                entity_sanctions[str(p.entity_id)].append({
                    "event_id": s.id,
                    "sanction_start": sanction_start,
                    "sanction_end": sanction_end,
                    "sanction_type": s.attrs.get("sanction_type", "CEIS/CNEP"),
                    "description": s.description,
                })

        if not entity_sanctions:
            return []

        sanctioned_entity_ids = list(entity_sanctions.keys())

        # 2. Get contracts where sanctioned entities are suppliers/winners
        contract_stmt = (
            select(Event)
            .where(Event.type == "contrato")
        )
        contract_result = await session.execute(contract_stmt)
        contracts = contract_result.scalars().all()

        if not contracts:
            return []

        contract_ids = [c.id for c in contracts]
        contract_map: dict[str, Event] = {str(c.id): c for c in contracts}

        # Get participants of contracts (chunked to avoid asyncpg param limit)
        contract_parts = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["supplier", "winner", "contractor"]),
            ),
            contract_ids,
        )

        # Find overlaps
        signals: list[RiskSignalOut] = []

        for cp in contract_parts:
            entity_id_str = str(cp.entity_id)
            if entity_id_str not in entity_sanctions:
                continue

            contract = contract_map.get(str(cp.event_id))
            if contract is None:
                continue

            contract_start = (
                contract.attrs.get("contract_start")
                or contract.attrs.get("vigencia_inicio")
                or (contract.occurred_at.isoformat() if contract.occurred_at else None)
            )
            contract_end = contract.attrs.get("contract_end") or contract.attrs.get(
                "vigencia_fim"
            )

            if not contract_start:
                continue

            try:
                c_start = _parse_datetime(contract_start)
            except (ValueError, TypeError):
                continue

            c_end = None
            if contract_end:
                try:
                    c_end = _parse_datetime(contract_end)
                except (ValueError, TypeError):
                    pass

            # Default contract end to 1 year after start
            if c_end is None:
                c_end = c_start + timedelta(days=365)

            # Check temporal overlap with each sanction
            for sanction in entity_sanctions[entity_id_str]:
                try:
                    s_start = _parse_datetime(sanction["sanction_start"])
                except (ValueError, TypeError):
                    continue

                s_end = None
                if sanction["sanction_end"]:
                    try:
                        s_end = _parse_datetime(sanction["sanction_end"])
                    except (ValueError, TypeError):
                        pass

                # CEIS/CNEP sanctions without dataFimSancao are indefinite/ongoing.
                # Treat as still-active (far-future end) rather than skipping — skipping
                # would cause T08 to miss the most egregious cases where the sanction
                # was never lifted.
                if s_end is None:
                    s_end = datetime.now(timezone.utc) + timedelta(days=365 * 20)

                # Check overlap: contract_start <= sanction_end AND contract_end >= sanction_start
                if c_start <= s_end and c_end >= s_start:
                    # Contract signed after sanction → CRITICAL
                    if c_start >= s_start:
                        severity = SignalSeverity.CRITICAL
                        confidence = 0.95
                        situation = "Contrato assinado DURANTE período de sanção"
                    else:
                        severity = SignalSeverity.HIGH
                        confidence = 0.85
                        situation = "Contrato pré-existente sobrepõe período de sanção"

                    contract_value = contract.value_brl
                    value_str = f"R$ {contract_value:,.2f}" if contract_value else "N/A"

                    signal = RiskSignalOut(
                        id=uuid.uuid4(),
                        typology_code=self.id,
                        typology_name=self.name,
                        severity=severity,
                        confidence=confidence,
                        title=f"Entidade sancionada com contrato ativo",
                        summary=(
                            f"{situation}. "
                            f"Sanção: {sanction['sanction_type']} "
                            f"({s_start.strftime('%d/%m/%Y')} a {s_end.strftime('%d/%m/%Y')}). "
                            f"Contrato: {c_start.strftime('%d/%m/%Y')} a {c_end.strftime('%d/%m/%Y')}, "
                            f"valor {value_str}."
                        ),
                        factors={
                            "sanction_type": sanction["sanction_type"],
                            "sanction_start": s_start.isoformat(),
                            "sanction_end": s_end.isoformat(),
                            "contract_start": c_start.isoformat(),
                            "contract_end": c_end.isoformat(),
                            "contract_value_brl": contract_value,
                            "signed_during_sanction": c_start >= s_start,
                        },
                        evidence_refs=[
                            EvidenceRef(
                                ref_type=RefType.EVENT,
                                ref_id=str(sanction["event_id"]),
                                description=f"Sanção {sanction['sanction_type']}",
                            ),
                            EvidenceRef(
                                ref_type=RefType.EVENT,
                                ref_id=str(contract.id),
                                description=f"Contrato {value_str}",
                            ),
                            EvidenceRef(
                                ref_type=RefType.ENTITY,
                                ref_id=entity_id_str,
                                description="Entidade sancionada",
                            ),
                        ],
                        entity_ids=[cp.entity_id],
                        event_ids=[sanction["event_id"], contract.id],
                        period_start=max(s_start, c_start),
                        period_end=min(s_end, c_end),
                        created_at=datetime.now(timezone.utc),
                    )
                    signals.append(signal)

        return signals


def _parse_datetime(value: object) -> datetime:
    raw = str(value).strip()
    if not raw:
        raise ValueError("empty datetime")

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
