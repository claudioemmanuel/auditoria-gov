"""Tests for orcamento_bim connector."""

import json

import pytest

from shared.connectors import get_connector
from shared.connectors.base import JobSpec


@pytest.mark.asyncio
async def test_fetch_missing_file_returns_empty(tmp_path):
    connector = get_connector("orcamento_bim")
    job = connector.list_jobs()[0]

    items, cursor = await connector.fetch(
        job,
        params={"data_file": str(tmp_path / "missing.jsonl")},
    )

    assert items == []
    assert cursor is None


@pytest.mark.asyncio
async def test_fetch_paginates_jsonl(tmp_path):
    connector = get_connector("orcamento_bim")
    job = connector.list_jobs()[0]
    data_file = tmp_path / "bim.jsonl"

    rows = [
        {"obra_id": "obra-1", "sinapi_reference_brl": 100, "contracted_unit_price_brl": 120},
        {"obra_id": "obra-1", "sinapi_reference_brl": 100, "contracted_unit_price_brl": 130},
        {"obra_id": "obra-2", "sinapi_reference_brl": 50, "contracted_unit_price_brl": 80},
    ]
    data_file.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    page1, cursor1 = await connector.fetch(job, params={"data_file": str(data_file), "page_size": 2})
    page2, cursor2 = await connector.fetch(
        job,
        cursor=cursor1,
        params={"data_file": str(data_file), "page_size": 2},
    )

    assert len(page1) == 2
    assert cursor1 is not None
    assert len(page2) == 1
    assert page2[0].data["obra_id"] == "obra-2"
    assert cursor2 is None


def test_normalize_maps_event_and_participants():
    connector = get_connector("orcamento_bim")
    job = JobSpec(name="orcamento_bim_items", description="", domain="orcamento_bim")

    from shared.models.raw import RawItem

    items = [
        RawItem(
            raw_id="orcamento_bim_items:0",
            data={
                "orgao_cnpj": "00394445000166",
                "orgao_nome": "UFMG",
                "fornecedor_cnpj": "12345678000199",
                "fornecedor_nome": "Fornecedor Teste",
                "sinapi_reference_brl": 100.0,
                "contracted_unit_price_brl": 150.0,
                "quantity": 10,
                "service_code": "SINAPI-001",
                "obra_id": "obra-xyz",
                "occurred_at": "2025-01-01",
            },
        ),
    ]

    result = connector.normalize(job, items)
    assert len(result.events) == 1
    ev = result.events[0]
    assert ev.type == "orcamento_bim"
    assert ev.attrs["obra_id"] == "obra-xyz"
    roles = sorted(p.role for p in ev.participants)
    assert "buyer" in roles
    assert "procuring_entity" in roles
    assert "supplier" in roles
