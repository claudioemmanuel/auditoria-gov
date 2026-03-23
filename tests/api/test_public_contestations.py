"""Tests for POST /public/contestations and extended Contestation fields (P4.1)."""
import uuid
from types import SimpleNamespace

import pytest

from api.app.routers import public
from shared.models.signals import ContestationCreate


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_db_contestation(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id=uuid.uuid4(),
        signal_id=uuid.uuid4(),
        entity_id=None,
        report_type="signal_error",
        evidence_url=None,
        status="open",
        requester_name="João Auditor",
        requester_email="joao@example.com",
        reason="O sinal está duplicado e incorreto",
        details={},
        resolution=None,
        resolved_at=None,
        created_at="2026-03-23T12:00:00Z",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class _FakeSession:
    def __init__(self, obj):
        self._obj = obj

    def add(self, _):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        # copy all fields from _obj into obj
        for k, v in vars(self._obj).items():
            setattr(obj, k, v)

    async def get(self, _model, _id):
        return self._obj


# ── POST /contestations — happy path ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_contestation_v2_signal():
    signal_id = uuid.uuid4()
    payload = ContestationCreate(
        signal_id=signal_id,
        report_type="signal_error",
        requester_name="João Auditor",
        reason="O sinal está incorreto por ausência de dados",
    )
    db_obj = _make_db_contestation(signal_id=signal_id)
    result = await public.create_contestation_v2(payload, _FakeSession(db_obj))
    assert result.signal_id == signal_id
    assert result.report_type == "signal_error"
    assert result.entity_id is None
    assert result.evidence_url is None
    assert result.status == "open"


@pytest.mark.asyncio
async def test_create_contestation_v2_entity():
    entity_id = uuid.uuid4()
    payload = ContestationCreate(
        entity_id=entity_id,
        report_type="entity_error",
        evidence_url="https://www.gov.br/evidencia/doc123",
        requester_name="Maria Cidadã",
        reason="Entidade cadastrada com CNPJ errado",
    )
    db_obj = _make_db_contestation(
        signal_id=None,
        entity_id=entity_id,
        report_type="entity_error",
        evidence_url="https://www.gov.br/evidencia/doc123",
    )
    result = await public.create_contestation_v2(payload, _FakeSession(db_obj))
    assert result.entity_id == entity_id
    assert result.signal_id is None
    assert result.report_type == "entity_error"
    assert result.evidence_url == "https://www.gov.br/evidencia/doc123"


@pytest.mark.asyncio
async def test_create_contestation_v2_duplicate_type():
    signal_id = uuid.uuid4()
    payload = ContestationCreate(
        signal_id=signal_id,
        report_type="duplicate",
        requester_name="Pedro Fiscal",
        reason="Já existe sinal idêntico para este contrato",
    )
    db_obj = _make_db_contestation(signal_id=signal_id, report_type="duplicate")
    result = await public.create_contestation_v2(payload, _FakeSession(db_obj))
    assert result.report_type == "duplicate"


# ── POST /contestations — validation error ────────────────────────────────────

@pytest.mark.asyncio
async def test_create_contestation_v2_no_target_raises():
    """Both signal_id and entity_id absent → 422."""
    from fastapi import HTTPException
    payload = ContestationCreate(
        requester_name="Anônimo",
        reason="Sem identificação de alvo",
    )
    with pytest.raises(HTTPException) as exc_info:
        await public.create_contestation_v2(payload, _FakeSession(None))
    assert exc_info.value.status_code == 422


# ── GET /contestation/{id} — returns new fields ───────────────────────────────

@pytest.mark.asyncio
async def test_get_contestation_returns_new_fields():
    entity_id = uuid.uuid4()
    db_obj = _make_db_contestation(
        signal_id=None,
        entity_id=entity_id,
        report_type="other",
        evidence_url="https://www.tcu.gov.br/doc/1",
    )
    result = await public.get_contestation(db_obj.id, _FakeSession(db_obj))
    assert result.entity_id == entity_id
    assert result.report_type == "other"
    assert result.evidence_url == "https://www.tcu.gov.br/doc/1"


# ── _contestation_out helper ──────────────────────────────────────────────────

def test_contestation_out_helper_maps_all_fields():
    db_obj = _make_db_contestation(
        report_type="entity_error",
        evidence_url="https://gov.br/doc",
    )
    out = public._contestation_out(db_obj)
    assert out.report_type == "entity_error"
    assert out.evidence_url == "https://gov.br/doc"
    assert out.status == "open"
    assert out.requester_name == "João Auditor"
