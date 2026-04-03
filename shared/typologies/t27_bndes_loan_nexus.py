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


class T27BndesLoanNexusTypology(BaseTypology):
    """T27 — BNDES Loan-Contract Nexus (Potential Favoritism).

    Detects companies that received BNDES financing AND won procurement
    contracts where the same entity appears as borrower and supplier,
    especially when there is temporal correlation (loan and contract
    within 12 months).  Indicates potential favouritism or conflict of
    interest in the public financing + procurement pipeline.

    Algorithm:
    1. Fetch all ``financiamento_bndes`` events and their borrower
       participants.
    2. Fetch all ``contrato`` / ``licitacao`` events and their supplier
       participants.
    3. For each entity present in both sets, compute temporal distance
       between the loan disbursement and the contract award.
    4. Signal:
       a. HIGH (0.88): loan and contract within 12 months of each other.
       b. MEDIUM (0.70): loan and contract within 24 months.
    5. Factors include loan_value, contract_value, time gap, and whether
       both events share the same UF (state).
    """

    CLOSE_WINDOW_DAYS = 365       # 12 months — HIGH
    EXTENDED_WINDOW_DAYS = 730    # 24 months — MEDIUM

    @property
    def id(self) -> str:
        return "T27"

    @property
    def name(self) -> str:
        return "Nexo BNDES x Contrato"

    @property
    def required_domains(self) -> list[str]:
        return ["financiamento_bndes", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["loan_date", "contract_date"]

    @property
    def corruption_types(self) -> list[str]:
        return ["corrupcao_ativa", "fraude_licitatoria"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "privada"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        # ── Step 1: Load BNDES financing events ─────────────────────────
        loan_stmt = select(Event).where(Event.type == "financiamento_bndes")
        loan_result = await session.execute(loan_stmt)
        loans = loan_result.scalars().all()

        if not loans:
            return []

        loan_event_ids = [l.id for l in loans]
        loan_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(["borrower", "beneficiario", "mutuario"]),
            ),
            loan_event_ids,
        )

        entity_loans: dict[str, list[dict]] = defaultdict(list)
        loan_map: dict[str, Event] = {str(l.id): l for l in loans}

        for lp in loan_participants:
            evt = loan_map.get(str(lp.event_id))
            if evt is None:
                continue

            loan_date = (
                evt.attrs.get("loan_date")
                or evt.attrs.get("data_contratacao")
                or (evt.occurred_at.isoformat() if evt.occurred_at else None)
            )
            if not loan_date:
                continue

            loan_uf = evt.attrs.get("uf") or evt.attrs.get("estado")

            entity_loans[str(lp.entity_id)].append({
                "event_id": evt.id,
                "loan_date": loan_date,
                "loan_value": evt.value_brl,
                "loan_uf": loan_uf,
                "description": evt.description,
            })

        if not entity_loans:
            return []

        # ── Step 2: Load procurement contracts ───────────────────────────
        contract_stmt = select(Event).where(Event.type.in_(["contrato", "licitacao"]))
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

        # ── Step 3: Detect temporal correlation ──────────────────────────
        signals: list[RiskSignalOut] = []
        now = datetime.now(timezone.utc)

        for cp in contract_parts:
            entity_id_str = str(cp.entity_id)
            if entity_id_str not in entity_loans:
                continue

            contract = contract_map.get(str(cp.event_id))
            if contract is None:
                continue

            contract_date_raw = (
                contract.attrs.get("contract_date")
                or contract.attrs.get("data_assinatura")
                or (contract.occurred_at.isoformat() if contract.occurred_at else None)
            )
            if not contract_date_raw:
                continue

            try:
                c_date = _parse_datetime(contract_date_raw)
            except (ValueError, TypeError):
                continue

            contract_uf = contract.attrs.get("uf") or contract.attrs.get("estado")

            for loan in entity_loans[entity_id_str]:
                try:
                    l_date = _parse_datetime(loan["loan_date"])
                except (ValueError, TypeError):
                    continue

                days_between = abs((c_date - l_date).days)

                if days_between > self.EXTENDED_WINDOW_DAYS:
                    continue

                same_uf = (
                    bool(loan["loan_uf"] and contract_uf)
                    and loan["loan_uf"].upper() == contract_uf.upper()
                )

                if days_between <= self.CLOSE_WINDOW_DAYS:
                    severity = SignalSeverity.HIGH
                    confidence = 0.88
                    window_label = "12 meses"
                else:
                    severity = SignalSeverity.MEDIUM
                    confidence = 0.70
                    window_label = "24 meses"

                loan_value = loan["loan_value"]
                contract_value = contract.value_brl
                loan_str = f"R$ {loan_value:,.2f}" if loan_value else "N/A"
                contract_str = f"R$ {contract_value:,.2f}" if contract_value else "N/A"

                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=severity,
                    confidence=confidence,
                    title="Nexo entre financiamento BNDES e contrato público",
                    summary=(
                        f"Empresa recebeu financiamento BNDES ({loan_str}) e venceu "
                        f"licitação/contrato ({contract_str}) em intervalo de {window_label} "
                        f"({days_between} dias). "
                        f"{'Mesmo estado (UF).' if same_uf else 'Estados distintos.'}"
                    ),
                    factors={
                        "loan_value_brl": loan_value,
                        "contract_value_brl": contract_value,
                        "loan_date": l_date.isoformat(),
                        "contract_date": c_date.isoformat(),
                        "time_between_events_days": days_between,
                        "same_uf": same_uf,
                        "loan_uf": loan.get("loan_uf"),
                        "contract_uf": contract_uf,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(loan["event_id"]),
                            description=f"Financiamento BNDES {loan_str}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(contract.id),
                            description=f"Contrato {contract_str}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.ENTITY,
                            ref_id=entity_id_str,
                            description="Empresa com financiamento e contrato",
                        ),
                    ],
                    entity_ids=[cp.entity_id],
                    event_ids=[loan["event_id"], contract.id],
                    period_start=min(l_date, c_date),
                    period_end=max(l_date, c_date),
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
