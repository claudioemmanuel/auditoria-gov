import logging
import re
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

# Matches Brazilian CNPJ (XX.XXX.XXX/XXXX-XX) and CPF (XXX.XXX.XXX-XX)
_CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")


class T28JudicialPrecedentWarningTypology(BaseTypology):
    """T28 — Judicial Precedent Warning (STF / Jurisprudência).

    Early-warning typology that cross-references STF rulings on
    procurement fraud or administrative improbity with entities that hold
    active contracts.

    Unlike most typologies, jurisprudência events do not carry structured
    entity references.  This detector therefore extracts CNPJ/CPF
    patterns from the ruling text (description / ementa) and matches
    them against entities that have active procurement contracts.

    Algorithm:
    1. Fetch all ``jurisprudencia`` events.
    2. Extract CNPJ/CPF identifiers from each ruling's description text.
    3. Build a map: document_id → set[cnpj/cpf].
    4. Fetch all active ``contrato`` events (within last 2 years) and
       their supplier participants.
    5. For each supplier entity whose tax_id (CNPJ/CPF) appears in any
       ruling text, emit an informational signal.
    6. Signal: MEDIUM (0.65) — requires human review.
    """

    @property
    def id(self) -> str:
        return "T28"

    @property
    def name(self) -> str:
        return "Alerta Jurisprudência x Contrato"

    @property
    def required_domains(self) -> list[str]:
        return ["jurisprudencia", "contrato"]

    @property
    def required_fields(self) -> list[str]:
        return ["description", "tax_id"]

    @property
    def corruption_types(self) -> list[str]:
        return ["fraude_licitatoria", "corrupcao_ativa", "corrupcao_passiva"]

    @property
    def spheres(self) -> list[str]:
        return ["administrativa", "politica"]

    @property
    def evidence_level(self) -> str:
        return "proxy"

    async def run(self, session) -> list[RiskSignalOut]:
        now = datetime.now(timezone.utc)
        active_cutoff = now - timedelta(days=730)  # 2 years

        # ── Step 1: Load jurisprudência events ───────────────────────────
        juris_stmt = select(Event).where(Event.type == "jurisprudencia")
        juris_result = await session.execute(juris_stmt)
        rulings = juris_result.scalars().all()

        if not rulings:
            return []

        # ── Step 2–3: Extract CNPJ/CPF from ruling text ─────────────────
        # Map: normalised tax_id → list of ruling info
        taxid_rulings: dict[str, list[dict]] = defaultdict(list)

        for r in rulings:
            text = (r.description or "") + " " + (r.attrs.get("ementa") or "")
            cnpjs = _CNPJ_RE.findall(text)
            cpfs = _CPF_RE.findall(text)
            all_ids = set(cnpjs) | set(cpfs)

            for tid in all_ids:
                normalised = _normalise_tax_id(tid)
                taxid_rulings[normalised].append({
                    "event_id": r.id,
                    "tribunal": r.attrs.get("tribunal") or "STF",
                    "description": (r.description or "")[:300],
                    "ruling_date": r.occurred_at,
                })

        if not taxid_rulings:
            return []

        # ── Step 4: Load active contracts ────────────────────────────────
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

        # Build entity_id → (tax_id, contract_count, contract_events)
        entity_contracts: dict[str, list] = defaultdict(list)
        for cp in contract_parts:
            contract = contract_map.get(str(cp.event_id))
            if contract:
                entity_contracts[str(cp.entity_id)].append(contract)

        if not entity_contracts:
            return []

        # ── Step 5: Load entity tax_ids via a second query ───────────────
        # We need to read participant.entity_id → Entity.tax_id.  Rather than
        # loading the full Entity table, we look at participant attrs or
        # re-query.  For efficiency we load entities referenced in contracts.
        from openwatch_models.orm import Entity

        entity_id_list = list(entity_contracts.keys())
        entities = await execute_chunked_in(
            session,
            lambda batch: select(Entity).where(Entity.id.in_(batch)),
            [uuid.UUID(eid) for eid in entity_id_list],
        )

        entity_taxid_map: dict[str, str] = {}
        entity_name_map: dict[str, str] = {}
        for ent in entities:
            tid = getattr(ent, "tax_id", None) or (ent.attrs or {}).get("tax_id")
            if tid:
                entity_taxid_map[str(ent.id)] = _normalise_tax_id(tid)
                entity_name_map[str(ent.id)] = getattr(ent, "name", None) or str(ent.id)

        # ── Step 6: Cross-reference ──────────────────────────────────────
        signals: list[RiskSignalOut] = []

        for entity_id_str, contract_list in entity_contracts.items():
            normalised_tid = entity_taxid_map.get(entity_id_str)
            if not normalised_tid:
                continue
            if normalised_tid not in taxid_rulings:
                continue

            matching_rulings = taxid_rulings[normalised_tid]
            entity_name = entity_name_map.get(entity_id_str, entity_id_str)
            contract_count = len(contract_list)

            for ruling in matching_rulings:
                signal = RiskSignalOut(
                    id=uuid.uuid4(),
                    typology_code=self.id,
                    typology_name=self.name,
                    severity=SignalSeverity.MEDIUM,
                    confidence=0.65,
                    title="Entidade referenciada em jurisprudência com contrato ativo",
                    summary=(
                        f"CNPJ/CPF de '{entity_name}' identificado em decisão do "
                        f"{ruling['tribunal']} sobre fraude/improbidade. "
                        f"Entidade possui {contract_count} contrato(s) ativo(s). "
                        f"Requer análise humana."
                    ),
                    factors={
                        "ruling_description": ruling["description"],
                        "tribunal": ruling["tribunal"],
                        "entity_name": entity_name,
                        "entity_tax_id": normalised_tid,
                        "contract_count": contract_count,
                        "ruling_date": ruling["ruling_date"].isoformat() if ruling["ruling_date"] else None,
                    },
                    evidence_refs=[
                        EvidenceRef(
                            ref_type=RefType.EVENT,
                            ref_id=str(ruling["event_id"]),
                            description=f"Decisão {ruling['tribunal']}",
                        ),
                        EvidenceRef(
                            ref_type=RefType.ENTITY,
                            ref_id=entity_id_str,
                            description=f"Entidade: {entity_name}",
                        ),
                    ],
                    entity_ids=[uuid.UUID(entity_id_str)],
                    event_ids=[ruling["event_id"]] + [c.id for c in contract_list],
                    period_start=ruling["ruling_date"] if ruling["ruling_date"] else now,
                    period_end=now,
                    created_at=now,
                )
                signals.append(signal)

        return signals


def _normalise_tax_id(raw: str) -> str:
    """Strip formatting from CNPJ/CPF, keeping only digits."""
    return re.sub(r"[^0-9]", "", raw)


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
