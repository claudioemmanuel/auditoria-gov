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

# Maximum ratio of amendment_value / municipality_revenue before flagging
_REVENUE_RATIO_THRESHOLD = 3.0

# HHI threshold for relator concentration (same as T01 logic)
_RELATOR_HHI_THRESHOLD = 0.70


class T16BudgetClientelismTypology(BaseTypology):
    """T16 — Clientelismo Orçamentário-Contratual (Emenda Pix).

    Algorithm:
    1. Query transferencia/emenda events (parliamentary amendments / special transfers).
    2. Flag transfers with no registered plano_de_trabalho
       (plano_trabalho_registered = False in attrs).
    3. Flag transfers where value > 3× municipality's annual own-revenue proxy
       (stored as municipality_revenue_brl in entity attrs).
    4. Flag relator concentration: same parliamentary relator directs >70% HHI
       of amendments to a restricted set of municipalities.
    5. Each flagged event gets n_flags computed; signal raised if n_flags ≥ 2.

    Legal basis:
    - CF/88, Art. 166-A (parliamentary budget amendments)
    - TCU Acórdão 518/2023 (amendments without registered work plan = red flag)
    - STF Min. Flávio Dino 2024 (R$ 694M in "Emendas Pix" suspended)
    - Decreto 11.878/2024 (regulation of special budget transfers)
    """

    @property
    def id(self) -> str:
        return "T16"

    @property
    def name(self) -> str:
        return "Clientelismo Orçamentário-Contratual"

    @property
    def required_domains(self) -> list[str]:
        return ["emenda", "transferencia"]

    @property
    def required_fields(self) -> list[str]:
        return ["plano_trabalho_registered", "value_brl", "relator_id"]

    @property
    def corruption_types(self) -> list[str]:
        return ["nepotismo_clientelismo", "peculato"]

    @property
    def spheres(self) -> list[str]:
        return ["politica", "administrativa"]

    @property
    def evidence_level(self) -> str:
        return "indirect"

    async def run(self, session) -> list[RiskSignalOut]:
        window_end = datetime.now(timezone.utc)
        window_start = window_end - timedelta(days=365 * 2)

        # Query transfer/amendment events
        stmt = select(Event).where(
            Event.type.in_(["transferencia", "emenda"]),
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
            Event.value_brl.isnot(None),
            Event.value_brl > 0,
        )
        result = await session.execute(stmt)
        events = result.scalars().all()

        if not events:
            return []

        event_ids = [e.id for e in events]
        parts_stmt = select(EventParticipant).where(
            EventParticipant.event_id.in_(event_ids),
        )
        parts_result = await session.execute(parts_stmt)
        participants = parts_result.scalars().all()

        event_roles: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for p in participants:
            event_roles[str(p.event_id)][p.role].append(str(p.entity_id))

        # Build relator → {beneficiary → total_value} for HHI
        relator_beneficiary_value: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        signals: list[RiskSignalOut] = []

        for event in events:
            attrs = event.attrs or {}
            n_flags = 0
            flag_reasons: list[str] = []

            # Flag 1: no plano_de_trabalho registered
            plano_registered = attrs.get("plano_trabalho_registered")
            if plano_registered is False or plano_registered == "false":
                n_flags += 1
                flag_reasons.append("sem_plano_trabalho")

            # Flag 2: value >> municipality revenue
            muni_revenue = attrs.get("municipality_revenue_brl") or 0
            if muni_revenue > 0 and event.value_brl:
                ratio = event.value_brl / muni_revenue
                if ratio > _REVENUE_RATIO_THRESHOLD:
                    n_flags += 1
                    flag_reasons.append(f"value_revenue_ratio_{ratio:.1f}x")

            # Track relator concentration
            relator_id = attrs.get("relator_id", "")
            if relator_id and event.value_brl:
                beneficiaries = event_roles.get(str(event.id), {}).get("beneficiary", [])
                beneficiary = beneficiaries[0] if beneficiaries else "unknown"
                relator_beneficiary_value[relator_id][beneficiary] += event.value_brl

            # Flag 3: recipient is sanctioned (marker in attrs)
            if attrs.get("recipient_sanctioned"):
                n_flags += 1
                flag_reasons.append("beneficiario_sancionado")

            if n_flags < 2:
                continue

            # Compute relator HHI for this relator if applicable
            relator_hhi = 0.0
            if relator_id:
                bmap = relator_beneficiary_value.get(relator_id, {})
                total = sum(bmap.values())
                if total > 0:
                    relator_hhi = sum((v / total) ** 2 for v in bmap.values())
                    if relator_hhi >= _RELATOR_HHI_THRESHOLD:
                        if "relator_concentration" not in flag_reasons:
                            n_flags += 1
                            flag_reasons.append("relator_concentration")

            if n_flags >= 3:
                severity = SignalSeverity.CRITICAL
                confidence = min(0.88, 0.70 + n_flags * 0.05)
            else:
                severity = SignalSeverity.HIGH
                confidence = 0.65

            muni_revenue_val = attrs.get("municipality_revenue_brl") or 0
            value_revenue_ratio = (
                round(event.value_brl / muni_revenue_val, 2)
                if muni_revenue_val and event.value_brl
                else None
            )

            entity_ids: list[uuid.UUID] = []
            for p in participants:
                if str(p.event_id) == str(event.id):
                    try:
                        entity_ids.append(uuid.UUID(str(p.entity_id)))
                    except ValueError:
                        pass

            signal = RiskSignalOut(
                id=uuid.uuid4(),
                typology_code=self.id,
                typology_name=self.name,
                severity=severity,
                confidence=confidence,
                title=(
                    f"Clientelismo orçamentário — {n_flags} indicador(es) de risco "
                    f"(R$ {event.value_brl:,.2f})"
                ),
                summary=(
                    f"Transferência/emenda de R$ {event.value_brl:,.2f} com {n_flags} "
                    f"indicador(es): {', '.join(flag_reasons)}. "
                    + (f"Razão valor/receita: {value_revenue_ratio}×. " if value_revenue_ratio else "")
                    + (f"HHI do relator: {relator_hhi:.2f}. " if relator_hhi > 0 else "")
                ),
                factors={
                    "plano_trabalho_registered": bool(plano_registered),
                    "value_vs_revenue_ratio": value_revenue_ratio,
                    "relator_hhi": round(relator_hhi, 3),
                    "recipient_sanctioned": bool(attrs.get("recipient_sanctioned")),
                    "n_flags": n_flags,
                    "flag_reasons": flag_reasons,
                },
                evidence_refs=[
                    EvidenceRef(
                        ref_type=RefType.EVENT,
                        ref_id=str(event.id),
                        description=(
                            f"Transferência R$ {event.value_brl:,.2f} "
                            f"em {event.occurred_at.strftime('%d/%m/%Y') if event.occurred_at else 'N/A'} "
                            f"— indicadores: {', '.join(flag_reasons)}"
                        ),
                    ),
                ],
                entity_ids=entity_ids[:5],
                event_ids=[event.id],
                period_start=event.occurred_at,
                period_end=window_end,
                created_at=datetime.now(timezone.utc),
            )
            signals.append(signal)

        return signals
