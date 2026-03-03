"""Seed functions for the reference_data table.

Each function populates a specific category of reference data
(IBGE municipalities, SIAPE organs, Receita Federal lookups, etc.).
Called via Celery task or API endpoint for one-time population.
"""

import csv
import os
from typing import Optional

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from shared.connectors.http_client import portal_transparencia_client
from shared.logging import log
from shared.models.orm import ReferenceData


def _upsert_ref(
    session,
    category: str,
    code: str,
    name: str,
    parent_code: Optional[str] = None,
    attrs: Optional[dict] = None,
) -> None:
    """Insert or update a single reference_data row."""
    stmt = (
        insert(ReferenceData)
        .values(
            category=category,
            code=code,
            name=name,
            parent_code=parent_code,
            attrs=attrs or {},
        )
        .on_conflict_do_update(
            constraint="uq_reference_data_category_code",
            set_={
                "name": name,
                "parent_code": parent_code,
                "attrs": attrs or {},
                "updated_at": func.now(),
            },
        )
    )
    session.execute(stmt)


async def seed_ibge_municipios(session) -> int:
    """Fetch all 5,570 IBGE municipalities (single call, no auth) and upsert."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    for m in data:
        microrregiao = m.get("microrregiao", {}) or {}
        mesorregiao = microrregiao.get("mesorregiao", {}) or {}
        uf = mesorregiao.get("UF", {}) or {}
        _upsert_ref(
            session,
            "ibge_municipio",
            code=str(m["id"]),
            name=m["nome"],
            parent_code=uf.get("sigla", ""),
            attrs={
                "uf_nome": uf.get("nome", ""),
                "regiao": (uf.get("regiao") or {}).get("nome", ""),
            },
        )

    session.commit()
    log.info("reference_seed.ibge_municipios", count=len(data))
    return len(data)


async def seed_ibge_ufs(session) -> int:
    """Fetch all 27 Brazilian states (single call, no auth) and upsert."""
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    for uf in data:
        regiao = uf.get("regiao", {}) or {}
        _upsert_ref(
            session,
            "ibge_uf",
            code=uf["sigla"],
            name=uf["nome"],
            parent_code=regiao.get("sigla", ""),
            attrs={"ibge_id": str(uf.get("id", "")), "regiao": regiao.get("nome", "")},
        )

    session.commit()
    log.info("reference_seed.ibge_ufs", count=len(data))
    return len(data)


async def seed_siape_orgaos(session) -> int:
    """Paginate PT API /orgaos-siape (same token), ~300-400 organs."""
    page = 1
    count = 0

    async with portal_transparencia_client() as client:
        while True:
            resp = await client.get("/orgaos-siape", params={"pagina": page})
            if resp.status_code in (405, 403):
                break
            resp.raise_for_status()
            items = resp.json()
            if not items:
                break

            for item in items:
                _upsert_ref(
                    session,
                    "siape_orgao",
                    code=str(item["codigo"]),
                    name=item["descricao"],
                )
                count += 1

            # PT API returns 15 items per page for this endpoint
            if len(items) < 15:
                break
            page += 1

    session.commit()
    log.info("reference_seed.siape_orgaos", count=count)
    return count


def _parse_rf_csv(
    session,
    data_dir: str,
    file_stem: str,
    category: str,
    code_col: int = 0,
    name_col: int = 1,
) -> int:
    """Parse a Receita Federal reference CSV and upsert rows."""
    # RFB CSVs may be named with varying case; try common patterns
    for ext in (".csv", ".CSV"):
        filepath = os.path.join(data_dir, f"{file_stem}{ext}")
        if os.path.exists(filepath):
            break
    else:
        log.warning("reference_seed.csv_not_found", file_stem=file_stem)
        return 0

    count = 0
    with open(filepath, "r", encoding="iso-8859-1") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) <= max(code_col, name_col):
                continue
            code = row[code_col].strip()
            name = row[name_col].strip()
            if not code or not name:
                continue
            _upsert_ref(session, category, code=code, name=name)
            count += 1

    log.info("reference_seed.rf_csv_parsed", category=category, count=count)
    return count


def seed_receita_reference(session, data_dir: str) -> dict[str, int]:
    """Parse reference CSVs from Receita Federal bulk data."""
    results: dict[str, int] = {}

    mapping = [
        ("CNAES", "cnae"),
        ("Naturezas", "natureza_juridica"),
        ("Qualificacoes", "qualificacao_socio"),
        ("Paises", "pais"),
        ("Motivos", "motivo_situacao"),
        ("Municipios", "rf_municipio"),
    ]

    for file_stem, category in mapping:
        results[category] = _parse_rf_csv(
            session, data_dir, file_stem, category=category, code_col=0, name_col=1
        )

    session.commit()
    return results


def get_reference_stats(session) -> dict[str, int]:
    """Return count of reference_data rows per category."""
    rows = session.execute(
        select(ReferenceData.category, func.count(ReferenceData.id))
        .group_by(ReferenceData.category)
        .order_by(ReferenceData.category)
    ).all()
    return {cat: cnt for cat, cnt in rows}
