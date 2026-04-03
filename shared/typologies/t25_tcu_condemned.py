import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

from sqlalchemy import select

from shared.models.orm import Event, EventParticipant
from shared.utils.query import execute_chunked_in
from shared.models.signals import (
    EvidenceRef,
    RefType,
    RiskSignalOut,
    SignalSeverity,
)
from shared.typologies.base import BaseTypology


class T25TCUCondemnedTypology(BaseTypology):
    """T25 — TCU Condemned Entity x Active Contract.

    Detects companies or individuals declared inidôneo (ineligible) or
    inabilitado by the TCU that continue to hold or sign active public
    contracts — the most severe form of government audit violation.

    Algorithm:
    1. Fetch all ``sancao_tcu`` events and their sanctioned participants.
    2. Fetch all ``contrato`` events and their supplier participants.
    3. For each entity present in both sets, check temporal overlap:
       a. CRITICAL (0.97): contract signed on or after TCU sanction start
          AND the sanction subtype is "inidoneo" (company-level bar).
       b. HIGH (0.90): pre-existing contract whose active period overlaps
          the TCU sanction period (any subtype).
       c. MEDIUM (0.80): contract signed on or after TCU sanction start
          when the subtype is "inabilitado" (individual barred from public
          function — company may still contract, but warrants review).
    """

    @property
    def id(self) -> str:
        return "T25"

    @property
    def name(self) -> str:
        return "Condenação TCU x Contrato Ativo"

    @property
    def required_domains(self) -> list[str]:
        return ["sancao_tcu", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["sanction_start", "sanction_end", "contract_start", "contract_end"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "corrupcao_ativa"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "privada"]

    @property
    def evidence_level(self) -> str:
        return "direct"

    async def run(self, session) -> list[RiskSignalOut]:
        # ------------------------------------------------------------------ #
        # Step 1: Load all TCU sanction events                                #
        # ------------------------------------------------------------------ #
        sanction_stmt = select(Event).where(Event.type == "sancao_tcu")
        sanction_result = await session.execute(sanction_stmt)
        sanctions = sanction_result.scalars().all()

        if not sanctions:
            return []

        # Resolve sanctioned entities via event participants (chunked to
        # stay well under the asyncpg 32 767-parameter limit).
        sanction_event_ids = [s.id for s in sanctions]
        sanction_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["sanctioned"]),
            ),
            sanction_event_ids,
        )

        # Build entity_id → list[sanction_info] mapping.
        entity_sanctions: dict[str, list[dict]] = defaultdict(list)
        sanction_map: dict[str, Event] = {str(s.id): s for s in sanctions}

        for p in sanction_participants:
            s = sanction_map.get(str(p.event_id))
            if s is None:
                continue

            # TCU uses data_transito_julgado (date judgment became final) or
            # data_acordao (date of ruling) as the effective sanction start.
            sanction_start = (
                s.attrs.get("sanction_start")
                or s.attrs.get("data_transito_julgado")
                or s.attrs.get("data_acordao")
                or (s.occurred_at.isoformat() if s.occurred_at else None)
            )
            # data_final = None means the sanction is indefinite (most severe).
            sanction_end = s.attrs.get("sanction_end") or s.attrs.get("data_final")
            # TCU connector stores type (inidoneo/inabilitado) in event.subtype field
            subtype = s.subtype or "inidoneo"  # default: company-level bar

            if sanction_start:
                entity_sanctions[str(p.entity_id)].append({
                    "event_id": s.id,
                    "sanction_start": sanction_start,
                    "sanction_end": sanction_end,
                    "subtype": subtype,
                    "description": s.description,
                })

        if not entity_sanctions:
            return []

        # ------------------------------------------------------------------ #
        # Step 2: Load all active contracts                                   #
        # ------------------------------------------------------------------ #
        contract_stmt = select(Event).where(Event.type == "contrato")
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

        # ------------------------------------------------------------------ #
        # Step 3: Detect temporal overlaps                                    #
        # ------------------------------------------------------------------ #
        signals: list[RiskSignalOut] = []

        for cp in contract_parts:
            entity_id_str = str(cp.entity_id)
            if entity_id_str not in entity_sanctions:
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

            # Fall back to 1-year duration when end date is missing.
            if c_end is None:
                c_end = c_start + timedelta(days=365)

            for sanction in entity_sanctions[entity_id_str]:
                try:
                    s_start = _parse_datetime(sanction["sanction_start"])
                except (ValueError, TypeError):
                    continue

                s_end: datetime | None = None
                if sanction["sanction_end"]:
                    try:
                        s_end = _parse_datetime(sanction["sanction_end"])
                    except (ValueError, TypeError):
                        pass

                # TCU inidoneo declarations without a termination date are
                # treated as perpetual — use a 20-year far-future sentinel so
                # we never miss the most egregious violations.
                if s_end is None:
                    s_end = datetime.now(timezone.utc) + timedelta(days=365 * 20)

                # Temporal overlap condition:
                # contract_start <= sanction_end AND contract_end >= sanction_start
                if not (c_start <= s_end and c_end >= s_start):
                    continue

                subtype = sanction["subtype"]
                signed_during = c_start >= s_start

                if signed_during and subtype == "inidoneo":
                    # Company-level bar; contract signed while sanctioned.
                    severity = SignalSeverity.CRITICAL
                    confidence = 0.97
                    situation = "Contrato assinado APÓS declaração de inidoneidade pelo TCU"
                elif not signed_during:
                    # Pre-existing contract that extends into the sanction window.
                    severity = SignalSeverity.HIGH
                    confidence = 0.90
                    situation = "Contrato pré-existente com vigência durante condenação TCU"
                else:
                    # signed_during=True but subtype is "inabilitado" (individual).
                    severity = SignalSeverity.MEDIUM
                    confidence = 0.80
                    situation = (
                        "Contrato assinado APÓS inabilitação TCU de responsável "
                        "(indivíduo inabilitado para função pública)"
                    )

                contract_value = contract.value_brl
                value_str = f"R$ {contract_value:,.2f}" if contract_value else "N/A"
                subtype_label = (
                    "Inidoneidade" if subtype == "inidoneo" else "Inabilitação"
                )

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title="Entidade com condenação TCU e contrato ativo",
                    summary=(
                        f"{situation}. "
                        f"Condenação TCU ({subtype_label}): "
                        f"{s_start.strftime('%d/%m/%Y')} a {s_end.strftime('%d/%m/%Y')}. "
                        f"Contrato: {c_start.strftime('%d/%m/%Y')} a "
                        f"{c_end.strftime('%d/%m/%Y')}, valor {value_str}."
                    ),
                    factors={
                        "subtype": subtype,
                        "subtype_label": subtype_label,
                        "sanction_start": s_start.isoformat(),
                        "sanction_end": s_end.isoformat(),
                        "contract_start": c_start.isoformat(),
                        "contract_end": c_end.isoformat(),
                        "contract_value_brl": contract_value,
                        "signed_during_sanction": signed_during,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(sanction["event_id"]),
                            description=f"Condenação TCU — {subtype_label}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(contract.id),
                            description=f"Contrato {value_str}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.ENTITY,
                            ref_id=entity_id_str,
                            description="Entidade condenada pelo TCU",
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
    """Parse a datetime from ISO-8601, YYYY-MM-DD, or DD/MM/YYYY strings.

    Always returns a timezone-aware datetime in UTC.
    """
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
