import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

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
        window_start = window_end - timedelta(days=365 * 5)  # 5-year window to cover historical ingest

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
        participants = await execute_chunked_in(
            session,
            lambda batch: select(EventParticipant).where(
                EventParticipant.event_id.in_(batch),
            ),
            event_ids,
        )

        event_roles: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        event_entity_ids: dict[str, list[uuid.UUID]] = defaultdict(list)
        for p in participants:
            eid_str = str(p.event_id)
            event_roles[eid_str][p.role].append(str(p.entity_id))
            try:
                event_entity_ids[eid_str].append(uuid.UUID(str(p.entity_id)))
            except ValueError:
                pass

        # First pass: build relator → {beneficiary → total_value} for HHI.
        # This must be a separate pass so HHI is complete before the signal loop.
        relator_beneficiary_value: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for event in events:
            attrs = event.attrs or {}
            relator_id = attrs.get("relator_id", "")
            if relator_id and event.value_brl:
                beneficiaries = event_roles.get(str(event.id), {}).get("beneficiary", [])
                beneficiary = beneficiaries[0] if beneficiaries else "unknown"
                relator_beneficiary_value[relator_id][beneficiary] += event.value_brl

        # Pre-compute HHI per relator once (O(relators)) instead of per-event (O(events × beneficiaries))
        relator_hhi_cache: dict[str, float] = {}
        for relator_id, bmap in relator_beneficiary_value.items():
            total = sum(bmap.values())
            if total > 0:
                relator_hhi_cache[relator_id] = sum((v / total) ** 2 for v in bmap.values())
            else:
                relator_hhi_cache[relator_id] = 0.0

        signals: list[RiskSignalOut] = []

        # GROUP 1 — RP-9 Unconstitutional Emendas
        # STF ADPF 850/851/854 declared Emenda Relator unconstitutional on 2022-12-19.
        # Any RP-9 transfer AFTER that date is always a HIGH signal with no flag threshold.
        rp9_cutoff = date(2022, 12, 19)
        for event in events:
            emenda_type = (event.attrs or {}).get("emenda_type", "")
            if (
                emenda_type == "relator_rp9"
                and event.occurred_at
                and event.occurred_at.date() > rp9_cutoff
            ):
                signals.append(
                    RiskSignalOut(
                        id=uuid.uuid4(),
                        typology_code=self.id,
                        typology_name=self.name,
                        severity=SignalSeverity.HIGH,
                        confidence=0.90,
                        title=f"Emenda Relator (RP-9) inconstitucional — R$ {event.value_brl:,.2f}",
                        summary=(
                            f"Emenda de Relator de R$ {event.value_brl:,.2f} em "
                            f"{event.occurred_at.strftime('%d/%m/%Y')} — declarada inconstitucional "
                            f"pelo STF em 19/12/2022 (ADPF 850/851/854)."
                        ),
                        factors={
                            "emenda_type": "relator_rp9",
                            "legal_ref": "STF ADPF 850/851/854 — Emenda de Relator declarada inconstitucional em 19/12/2022",
                            "occurred_at": event.occurred_at.isoformat(),
                        },
                        evidence_refs=[
                            EvidenceRef(
                                ref_type=RefType.EVENT,
                                ref_id=str(event.id),
                                description=f"RP-9 R$ {event.value_brl:,.2f}",
                            )
                        ],
                        entity_ids=event_entity_ids.get(str(event.id), [])[:5],
                        event_ids=[event.id],
                        period_start=event.occurred_at,
                        period_end=window_end,
                        created_at=datetime.now(timezone.utc),
                    )
                )

        # GROUP 2 — Emendas Pix missing transparency
        # STF Min. Dino 2024 suspended R$ 694M in Emendas Especiais / Pix for failing
        # transparency requirements. Any missing condition fires a HIGH signal.
        for event in events:
            attrs = event.attrs or {}
            if attrs.get("emenda_type") != "especial_pix":
                continue
            pix_factors: list[str] = []
            if attrs.get("plano_trabalho_registered") is False:
                pix_factors.append("plano_trabalho_ausente")
            if attrs.get("beneficiario_final_identificado") is not True:
                pix_factors.append("beneficiario_nao_identificado")
            if attrs.get("conta_dedicada") is not True:
                pix_factors.append("conta_dedicada_ausente")
            if pix_factors:
                signals.append(
                    RiskSignalOut(
                        id=uuid.uuid4(),
                        typology_code=self.id,
                        typology_name=self.name,
                        severity=SignalSeverity.HIGH,
                        confidence=0.75,
                        title=f"Emenda Pix sem transparência — {', '.join(pix_factors)}",
                        summary=(
                            f"Transferência Especial (Emenda Pix) de R$ {event.value_brl:,.2f} "
                            f"com requisitos de transparência ausentes: {', '.join(pix_factors)}."
                        ),
                        factors={
                            "emenda_type": "especial_pix",
                            "pix_factors": pix_factors,
                            "legal_ref": "STF Min. Dino 2024 — condicionantes Emendas Pix (R$ 694M suspensos)",
                        },
                        evidence_refs=[
                            EvidenceRef(
                                ref_type=RefType.EVENT,
                                ref_id=str(event.id),
                                description=f"Emenda Pix R$ {event.value_brl:,.2f}",
                            )
                        ],
                        entity_ids=event_entity_ids.get(str(event.id), [])[:5],
                        event_ids=[event.id],
                        period_start=event.occurred_at,
                        period_end=window_end,
                        created_at=datetime.now(timezone.utc),
                    )
                )

        # GROUP 3 — HHI concentration / multi-flag logic (unchanged)
        for event in events:
            attrs = event.attrs or {}
            n_flags = 0
            flag_reasons: list[str] = []

            # Flag 1: no plano_de_trabalho registered
            # Only flag when explicitly False (boolean identity); None/null/absent/empty = not a flag
            plano_registered = attrs.get("plano_trabalho_registered")
            if plano_registered is False:
                n_flags += 1
                flag_reasons.append("sem_plano_trabalho")

            # Flag 2: value >> municipality revenue
            muni_revenue = attrs.get("municipality_revenue_brl") or 0
            if muni_revenue > 0 and event.value_brl:
                ratio = event.value_brl / muni_revenue
                if ratio > _REVENUE_RATIO_THRESHOLD:
                    n_flags += 1
                    flag_reasons.append(f"value_revenue_ratio_{ratio:.1f}x")

            relator_id = attrs.get("relator_id", "")

            # Flag 3: recipient is sanctioned (marker in attrs)
            if attrs.get("recipient_sanctioned"):
                n_flags += 1
                flag_reasons.append("beneficiario_sancionado")

            if n_flags < 2:
                continue

            # Lookup pre-computed relator HHI (O(1) instead of O(beneficiaries))
            relator_hhi = 0.0
            if relator_id:
                relator_hhi = relator_hhi_cache.get(relator_id, 0.0)
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

            entity_ids = event_entity_ids.get(str(event.id), [])

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
