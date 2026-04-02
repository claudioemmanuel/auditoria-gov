"""Tests for T16 P2.2 additions:
- GROUP 1: RP-9 Unconstitutional Emendas (STF ADPF 850/851/854)
- GROUP 2: Emendas Pix missing transparency (STF Min. Dino 2024)
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_models.signals import SignalSeverity
from openwatch_typologies.t16_budget_clientelism import T16BudgetClientelismTypology


def _make_event(
    emenda_type="individual",
    occurred_at=None,
    value_brl=500_000.0,
    plano_trabalho_registered=None,
    beneficiario_final_identificado=None,
    conta_dedicada=None,
    relator_id="",
    recipient_sanctioned=False,
    municipality_revenue_brl=0,
):
    ev = MagicMock()
    ev.id = uuid.uuid4()
    ev.type = "transferencia"
    ev.value_brl = value_brl
    ev.occurred_at = occurred_at or datetime(2023, 3, 1, tzinfo=timezone.utc)
    attrs: dict = {"emenda_type": emenda_type}
    if plano_trabalho_registered is not None:
        attrs["plano_trabalho_registered"] = plano_trabalho_registered
    if beneficiario_final_identificado is not None:
        attrs["beneficiario_final_identificado"] = beneficiario_final_identificado
    if conta_dedicada is not None:
        attrs["conta_dedicada"] = conta_dedicada
    if relator_id:
        attrs["relator_id"] = relator_id
    if recipient_sanctioned:
        attrs["recipient_sanctioned"] = True
    if municipality_revenue_brl:
        attrs["municipality_revenue_brl"] = municipality_revenue_brl
    ev.attrs = attrs
    return ev


def _make_session(events):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = events
    session.execute.return_value = result
    return session


def _patch_chunked_in(participants=None):
    return patch(
        "shared.typologies.t16_budget_clientelism.execute_chunked_in",
        new_callable=AsyncMock,
        return_value=participants or [],
    )


class TestT16RP9Group:
    """GROUP 1: RP-9 post-cutoff always fires HIGH, pre-cutoff never fires RP-9 signal."""

    @pytest.mark.asyncio
    async def test_rp9_post_2022_generates_high_severity(self):
        """RP-9 after 2022-12-19 cutoff generates exactly one HIGH signal."""
        event = _make_event(
            emenda_type="relator_rp9",
            occurred_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
            value_brl=500_000.0,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        rp9_signals = [s for s in signals if s.factors.get("emenda_type") == "relator_rp9"]
        assert len(rp9_signals) == 1
        assert rp9_signals[0].severity == SignalSeverity.HIGH
        assert rp9_signals[0].confidence == 0.90
        assert "ADPF 850/851/854" in rp9_signals[0].factors["legal_ref"]

    @pytest.mark.asyncio
    async def test_rp9_pre_cutoff_no_rp9_signal(self):
        """RP-9 event on 2022-12-18 (before cutoff) must NOT produce a GROUP 1 signal."""
        event = _make_event(
            emenda_type="relator_rp9",
            occurred_at=datetime(2022, 12, 18, tzinfo=timezone.utc),
            value_brl=500_000.0,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        rp9_signals = [s for s in signals if s.factors.get("emenda_type") == "relator_rp9"]
        assert len(rp9_signals) == 0

    @pytest.mark.asyncio
    async def test_rp9_exactly_on_cutoff_no_rp9_signal(self):
        """RP-9 on exactly 2022-12-19 (the cutoff day) must NOT fire — rule is strictly after."""
        event = _make_event(
            emenda_type="relator_rp9",
            occurred_at=datetime(2022, 12, 19, 12, 0, 0, tzinfo=timezone.utc),
            value_brl=500_000.0,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        rp9_signals = [s for s in signals if s.factors.get("emenda_type") == "relator_rp9"]
        assert len(rp9_signals) == 0


class TestT16PixGroup:
    """GROUP 2: Emendas Pix missing any transparency flag fires HIGH signal."""

    @pytest.mark.asyncio
    async def test_pix_missing_plano_trabalho_generates_signal(self):
        """especial_pix with plano_trabalho_registered=False → signal with plano_trabalho_ausente."""
        event = _make_event(
            emenda_type="especial_pix",
            plano_trabalho_registered=False,
            beneficiario_final_identificado=True,
            conta_dedicada=True,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(pix_signals) >= 1
        assert pix_signals[0].severity == SignalSeverity.HIGH
        assert "plano_trabalho_ausente" in pix_signals[0].factors["pix_factors"]

    @pytest.mark.asyncio
    async def test_pix_missing_beneficiario_generates_signal(self):
        """especial_pix with beneficiario_final_identificado=False → signal with beneficiario_nao_identificado."""
        event = _make_event(
            emenda_type="especial_pix",
            plano_trabalho_registered=True,
            beneficiario_final_identificado=False,
            conta_dedicada=True,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(pix_signals) >= 1
        assert "beneficiario_nao_identificado" in pix_signals[0].factors["pix_factors"]

    @pytest.mark.asyncio
    async def test_pix_missing_conta_dedicada_generates_signal(self):
        """especial_pix with conta_dedicada=False → signal with conta_dedicada_ausente."""
        event = _make_event(
            emenda_type="especial_pix",
            plano_trabalho_registered=True,
            beneficiario_final_identificado=True,
            conta_dedicada=False,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(pix_signals) >= 1
        assert "conta_dedicada_ausente" in pix_signals[0].factors["pix_factors"]

    @pytest.mark.asyncio
    async def test_pix_all_transparency_met_no_pix_signal(self):
        """especial_pix with all three transparency flags present → no GROUP 2 signal."""
        event = _make_event(
            emenda_type="especial_pix",
            plano_trabalho_registered=True,
            beneficiario_final_identificado=True,
            conta_dedicada=True,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(pix_signals) == 0

    @pytest.mark.asyncio
    async def test_pix_all_three_factors_present(self):
        """especial_pix missing all three transparency flags → signal lists all three factors."""
        event = _make_event(
            emenda_type="especial_pix",
            plano_trabalho_registered=False,
            beneficiario_final_identificado=False,
            conta_dedicada=False,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(pix_signals) == 1
        factors = pix_signals[0].factors["pix_factors"]
        assert "plano_trabalho_ausente" in factors
        assert "beneficiario_nao_identificado" in factors
        assert "conta_dedicada_ausente" in factors
        assert "STF Min. Dino 2024" in pix_signals[0].factors["legal_ref"]


class TestT16IndividualEmenda:
    """Individual/bancada/comissao emendas do NOT trigger GROUP 1 or GROUP 2."""

    @pytest.mark.asyncio
    async def test_individual_emenda_no_rp9_pix_signal(self):
        """emenda_type='individual' must never produce a GROUP 1 or GROUP 2 signal."""
        event = _make_event(
            emenda_type="individual",
            occurred_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
            value_brl=300_000.0,
        )
        session = _make_session([event])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        rp9_signals = [s for s in signals if s.factors.get("emenda_type") == "relator_rp9"]
        pix_signals = [s for s in signals if s.factors.get("emenda_type") == "especial_pix"]
        assert len(rp9_signals) == 0
        assert len(pix_signals) == 0

    @pytest.mark.asyncio
    async def test_no_events_returns_empty(self):
        """Zero events → empty signal list."""
        session = _make_session([])

        with _patch_chunked_in():
            typology = T16BudgetClientelismTypology()
            signals = await typology.run(session)

        assert signals == []
