import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

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
from shared.utils.query import execute_chunked_in

# Modalidades não-competitivas: 0 licitantes é esperado por lei (Lei 14.133/2021 Art. 72-74)
_NON_COMPETITIVE_MODALITIES: frozenset[str] = frozenset({
    "dispensa", "dispensa de licitação", "dispensa de licitacao",
    "dispensa eletrônica", "dispensa eletronica",
    "inexigibilidade", "inexigibilidade de licitação", "inexigibilidade de licitacao",
})

# Sem adjudicação → sem contrato → sem risco mensurável
_VOID_SITUATIONS: frozenset[str] = frozenset({
    "deserta", "fracassada", "revogada", "anulada", "cancelada",
})

# Adjudicada com 0 licitantes: juridicamente impossível em processo regular
_AWARDED_SITUATIONS: frozenset[str] = frozenset({
    "homologada", "adjudicada",
})


class T02LowCompetitionTypology(BaseTypology):
    """T02 — Low Competition.

    Algorithm:
    1. For each procurement in the analysis window:
       a. Skip non-competitive modalities (dispensa/inexigibilidade — 0 bidders expected by law).
       b. Skip void situations (deserta/fracassada/revogada — no award, no risk).
       c. Count distinct participants (bidders).
       d. Compare against BASELINE (PARTICIPANTS_PER_PROCUREMENT for same modality + CATMAT group).
    2. Flag if n_participants < baseline p10.
    3. Severity: CRITICAL if adjudicada with 0 bidders, HIGH if n_participants <= 1, MEDIUM if < p10.
    """

    @property
    def id(self) -> str:
        return "T02"

    @property
    def name(self) -> str:
        return "Baixa Competição"

    @property
    def required_domains(self) -> list[str]:
        return ["licitacao"]

    @property
    def required_fields(self) -> list[str]:
        return ["n_participants", "modality"]

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

        # Query licitacao events
        stmt = (
            select(Event)
            .where(
                Event.type == "licitacao",
                Event.occurred_at >= window_start,
                Event.occurred_at <= window_end,
            )
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        event_ids = [e.id for e in events]

        # Query all relevant participants (bidders for count + all roles for entity_ids)
        all_participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
                EventParticipant.role.in_(
                    ["procuring_entity", "buyer", "supplier", "winner", "bidder"]
                ),
            ),
            event_ids,
        )

        bidder_counts: dict[str, set[str]] = defaultdict(set)
        event_entity_ids: dict[str, list] = defaultdict(list)
        _seen: set[tuple[str, str]] = set()
        for p in all_participants:
            eid_str = str(p.event_id)
            entity_str = str(p.entity_id)
            if p.role == "bidder":
                bidder_counts[eid_str].add(entity_str)
            pair = (eid_str, entity_str)
            if pair not in _seen:
                _seen.add(pair)
                event_entity_ids[eid_str].append(p.entity_id)

        # Build event info map
        event_info: dict[str, dict] = {}
        for e in events:
            event_info[str(e.id)] = {
                "modality": e.attrs.get("modality", e.attrs.get("modalidade", "")).lower().strip(),
                "situacao": e.attrs.get("situacao", "").lower().strip(),
                "description": e.description,
                "value_brl": e.value_brl,
                "occurred_at": e.occurred_at,
            }

        # Get baseline
        baseline = await get_baseline(
            session,
            BaselineType.PARTICIPANTS_PER_PROCUREMENT.value,
            "national::all",
        )
        p10 = baseline.get("p10", 3.0) if baseline else 3.0

        signals: list[RiskSignalOut] = []

        for e in events:
            eid = str(e.id)
            n_bidders = len(bidder_counts.get(eid, set()))
            info = event_info[eid]
            modality = info["modality"]
            situacao = info["situacao"]

            # 1. Pular modalidades não-competitivas (dispensa/inexigibilidade)
            if any(modality.startswith(nc) for nc in _NON_COMPETITIVE_MODALITIES):
                continue

            # 2. Pular licitações sem adjudicação (deserta, fracassada, revogada...)
            if situacao in _VOID_SITUATIONS:
                continue

            if n_bidders >= p10:
                continue

            value_str = f"R$ {info['value_brl']:,.2f}" if info["value_brl"] else "N/A"

            # 3. Determinar severidade com contexto de adjudicação
            if n_bidders == 0 and situacao in _AWARDED_SITUATIONS:
                severity = SignalSeverity.CRITICAL
                confidence = 0.95
                title = "Licitação adjudicada sem participantes"
                summary = (
                    f"Licitação {situacao} com {n_bidders} participante(s). "
                    f"Adjudicação sem licitantes é juridicamente impossível em processo regular "
                    f"(Lei 14.133/2021 Art. 90). Modalidade: {modality or 'não informada'}. Valor: {value_str}."
                )
            elif n_bidders <= 1:
                severity = SignalSeverity.HIGH
                confidence = 0.90
                title = f"Baixa competição — {n_bidders} participante(s)"
                summary = (
                    f"Licitação com apenas {n_bidders} participante(s), "
                    f"abaixo do p10 do baseline ({p10:.1f}). "
                    f"Situação: {situacao or 'não informada'}. "
                    f"Modalidade: {modality or 'não informada'}. Valor: {value_str}."
                )
            else:
                severity = SignalSeverity.MEDIUM
                confidence = min(0.85, 0.5 + (p10 - n_bidders) / p10 * 0.4)
                title = f"Baixa competição — {n_bidders} participante(s)"
                summary = (
                    f"Licitação com {n_bidders} participante(s), "
                    f"abaixo do p10 do baseline ({p10:.1f}). "
                    f"Modalidade: {modality or 'não informada'}. Valor: {value_str}."
                )

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=title,
                summary=summary,
                factors={
                    "n_bidders": n_bidders,
                    "baseline_p10": round(p10, 2),
                    "modality": modality or "nao_informada",
                    "situacao": situacao or "nao_informada",
                    "value_brl": info["value_brl"],
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=eid,
                        description=f"Licitação com {n_bidders} participante(s)",
                    ),
                    EvidenceRef(
                        ref_type=RefType.BASELINE,
                        description=f"Baseline p10 = {p10:.1f} participantes",
                    ),
                ],
                entity_ids=event_entity_ids.get(eid, []),
                event_ids=[e.id],
                period_start=window_start,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
