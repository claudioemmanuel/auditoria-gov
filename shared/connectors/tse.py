"""Connector for TSE — Tribunal Superior Eleitoral (dados abertos).

Data source: https://dadosabertos.tse.jus.br/
Auth: None (public data, CSV/ZIP downloads).
Download URL: https://cdn.tse.jus.br/estatistica/sead/odsele/{zip_dir}/{zip_prefix}_{year}.zip
Encoding: ISO-8859-1, semicolon-delimited CSV.

Cursor format: "{year_idx}:{byte_offset}"
- year_idx: index into the election years list (0=2024, 1=2022, 2=2020)
- byte_offset: file position after the header row (0 = start of data)
"""

import csv
import io
import os
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.logging import log
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_TSE_CDN_BASE = "https://cdn.tse.jus.br/estatistica/sead/odsele"


def _safe_extractall(zip_path: str, dest_dir: str) -> None:
    """Extract ZIP with path traversal (Zip Slip) protection."""
    dest = os.path.realpath(dest_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            member_path = os.path.realpath(os.path.join(dest, member))
            if not member_path.startswith(dest + os.sep) and member_path != dest:
                raise ValueError(f"Zip Slip blocked: {member}")
        z.extractall(dest_dir)
_ELECTION_YEARS = [2024, 2022, 2020]  # Cover 5-year window (federal: 2022/2024; municipal: 2020/2024)
_CHUNK_SIZE = 10_000


@dataclass
class _TSEJobCfg:
    zip_dir: str        # CDN subdirectory
    zip_prefix: str     # ZIP filename prefix (before _{year}.zip)
    csv_prefix: str     # CSV filename prefix to look for after extraction
    years: list[int] = field(default_factory=lambda: list(_ELECTION_YEARS))


_JOB_CONFIG: dict[str, _TSEJobCfg] = {
    "tse_candidatos": _TSEJobCfg("consulta_cand", "consulta_cand", "consulta_cand"),
    "tse_bens_candidatos": _TSEJobCfg("bem_candidato", "bem_candidato", "bem_candidato"),
    "tse_receitas_candidatos": _TSEJobCfg(
        "prestacao_contas", "prestacao_de_contas_eleitorais_candidatos", "receitas_candidatos",
    ),
    "tse_despesas_candidatos": _TSEJobCfg(
        "prestacao_contas", "prestacao_de_contas_eleitorais_candidatos", "despesas_contratadas_candidatos",
    ),
}


async def _download_tse_dataset(cfg: _TSEJobCfg, year: int, data_dir: str) -> str:
    """Download and extract TSE dataset ZIP. Returns path to target CSV.

    Idempotent: skips download/extraction if CSV already present.
    Uses cfg.csv_prefix to locate the correct CSV inside the ZIP.
    Prefers the _BRASIL.csv (national aggregate) when available.

    Raises FileNotFoundError if the CDN returns 404 for this year.
    """
    os.makedirs(data_dir, exist_ok=True)

    zip_filename = f"{cfg.zip_prefix}_{year}.zip"
    zip_path = os.path.join(data_dir, zip_filename)

    def _find_csv() -> Optional[str]:
        """Find target CSV in data_dir matching csv_prefix + year."""
        matches = sorted(
            f for f in os.listdir(data_dir)
            if f.startswith(f"{cfg.csv_prefix}_{year}") and f.endswith(".csv")
        )
        if not matches:
            return None
        # Prefer _BRASIL.csv (national aggregate) over per-state files
        for m in matches:
            if "_BRASIL" in m or "_BR" in m:
                return os.path.join(data_dir, m)
        return os.path.join(data_dir, matches[0])

    # Check if already extracted
    existing = _find_csv()
    if existing:
        return existing

    # Download ZIP if not present
    if not os.path.exists(zip_path):
        url = f"{_TSE_CDN_BASE}/{cfg.zip_dir}/{zip_filename}"
        log.info("tse.downloading", file=zip_filename, url=url)
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(zip_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
            log.info("tse.downloaded", file=zip_filename)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise FileNotFoundError(
                    f"TSE CDN returned 404 for {url}"
                ) from exc
            raise

    # Validate and extract ZIP
    if not zipfile.is_zipfile(zip_path):
        os.remove(zip_path)
        raise FileNotFoundError(
            f"TSE: downloaded file is not a valid ZIP (deleted, will retry): {zip_filename}"
        )
    log.info("tse.extracting", file=zip_filename)
    _safe_extractall(zip_path, data_dir)
    log.info("tse.extracted", file=zip_filename)

    # Delete ZIP immediately after extraction — CSVs are all we need.
    try:
        os.remove(zip_path)
        log.info("tse.zip_deleted", file=zip_filename)
    except OSError:
        pass

    extracted = _find_csv()
    if not extracted:
        raise FileNotFoundError(
            f"No CSV matching {cfg.csv_prefix}_{year} after extracting {zip_filename} in {data_dir}"
        )
    return extracted


def _read_csv_chunk(
    csv_path: str,
    byte_offset: int,
    chunk_size: int = _CHUNK_SIZE,
    encoding: str = "iso-8859-1",
) -> tuple[list[dict], int, bool]:
    """Read a chunk of CSV rows from byte_offset.

    Returns (rows_as_dicts, new_byte_offset, finished).
    byte_offset=0 means start of data (after header row).
    """
    rows: list[dict] = []
    header: list[str] = []

    with open(csv_path, "r", encoding=encoding, errors="replace") as f:
        # Read header from start of file
        f.seek(0)
        raw_header = f.readline()
        header = [col.strip().strip('"') for col in raw_header.split(";")]
        header_end = f.tell()

        # Seek to read position: 0 means "from after header"
        read_from = byte_offset if byte_offset > 0 else header_end
        f.seek(read_from)

        for _ in range(chunk_size):
            line = f.readline()
            if not line:
                break
            values = [v.strip().strip('"') for v in line.split(";")]
            row: dict = {}
            for i, col in enumerate(header):
                row[col] = values[i] if i < len(values) else ""
            rows.append(row)

        new_offset = f.tell()

    file_size = os.path.getsize(csv_path)
    finished = new_offset >= file_size

    return rows, new_offset, finished


def _col(row: dict, *names: str, default: str = "") -> str:
    """Return first matching column value from row, case-insensitive."""
    row_lower = {k.upper(): v for k, v in row.items()}
    for name in names:
        val = row_lower.get(name.upper())
        if val is not None:
            return val
    return default


def _safe_float(value: object) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip().replace(",", ".")
    if not raw:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class TSEConnector(BaseConnector):
    """Connector for TSE — Tribunal Superior Eleitoral (dados abertos)."""

    @property
    def name(self) -> str:
        return "tse"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tse_candidatos",
                description="Candidates (2020/2022/2024 elections)",
                domain="candidato",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="tse_bens_candidatos",
                description="Candidate declared assets",
                domain="patrimonio",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="tse_receitas_candidatos",
                description="Candidate campaign fundraising",
                domain="doacao",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="tse_despesas_candidatos",
                description="Candidate campaign spending",
                domain="despesa_eleitoral",
                supports_incremental=False,
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        if job.name not in _JOB_CONFIG:
            raise ValueError(f"Unknown TSE job: {job.name}")

        cfg = _JOB_CONFIG[job.name]

        # Parse cursor: "year_idx:byte_offset"
        year_idx = 0
        byte_offset = 0
        if cursor and ":" in cursor:
            parts = cursor.split(":", 1)
            year_idx = int(parts[0])
            byte_offset = int(parts[1])

        if year_idx >= len(cfg.years):
            return [], None

        year = cfg.years[year_idx]
        data_dir = os.environ.get("TSE_DATA_DIR", "/data/tse")

        try:
            csv_path = await _download_tse_dataset(cfg, year, data_dir)
        except FileNotFoundError:
            # File not available for this year — skip to next
            log.warning("tse.year_not_available", job=job.name, year=year)
            next_cursor = f"{year_idx + 1}:0" if year_idx + 1 < len(cfg.years) else None
            return [], next_cursor

        rows, new_offset, finished = _read_csv_chunk(csv_path, byte_offset)

        raw_items = [
            RawItem(
                raw_id=f"{job.name}:{year}:{byte_offset}:{i}",
                data=row,
            )
            for i, row in enumerate(rows)
        ]

        if finished:
            # All rows consumed for this year — delete CSV to reclaim disk space.
            try:
                os.remove(csv_path)
                log.info("tse.csv_deleted", file=os.path.basename(csv_path), year=year)
            except OSError:
                pass
            next_cursor = f"{year_idx + 1}:0" if year_idx + 1 < len(cfg.years) else None
        else:
            next_cursor = f"{year_idx}:{new_offset}"

        return raw_items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "tse_candidatos":
            return self._normalize_candidatos(raw_items)
        if job.name == "tse_bens_candidatos":
            return self._normalize_bens_candidatos(raw_items)
        if job.name == "tse_receitas_candidatos":
            return self._normalize_receitas(raw_items)
        if job.name == "tse_despesas_candidatos":
            return self._normalize_despesas(raw_items)
        return NormalizeResult()

    # ── Normalizers ──────────────────────────────────────────────────

    def _normalize_candidatos(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            sq = _col(d, "SQ_CANDIDATO", "NR_SEQUENCIAL_CANDIDATO")
            nome = _col(d, "NM_CANDIDATO", "NM_CANDIDATURA")
            cpf = _col(d, "NR_CPF_CANDIDATO", "NR_CPF")
            cargo = _col(d, "DS_CARGO")
            partido = _col(d, "SG_PARTIDO")
            uf = _col(d, "SG_UF")
            ano = _col(d, "ANO_ELEICAO")
            sit_final = _col(d, "DS_SIT_TOT_TURNO", "DS_SITUACAO_CANDIDATURA")

            if not nome:
                continue

            entity = CanonicalEntity(
                source_connector="tse",
                source_id=sq or item.raw_id,
                type="person",
                name=nome,
                identifiers={"cpf": cpf} if cpf else {},
                attrs={
                    "cargo": cargo,
                    "partido": partido,
                    "uf": uf,
                    "ano_eleicao": ano,
                    "sit_final": sit_final,
                },
            )
            entities.append(entity)

            events.append(
                CanonicalEvent(
                    source_connector="tse",
                    source_id=item.raw_id,
                    type="candidatura",
                    subtype=cargo,
                    description=f"{nome} — {cargo}/{partido}/{uf}",
                    occurred_at=_parse_any_datetime(f"{ano}-01-01") if ano else None,
                    attrs={
                        "sq_candidato": sq,
                        "cargo": cargo,
                        "partido": partido,
                        "uf": uf,
                        "ano": ano,
                        "nr_candidato": _col(d, "NR_CANDIDATO"),
                        "sit_final": sit_final,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=entity, role="candidato"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def _normalize_bens_candidatos(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            sq = _col(d, "SQ_CANDIDATO", "NR_SEQUENCIAL_CANDIDATO")
            nome = _col(d, "NM_CANDIDATO", "NM_CANDIDATURA")
            cpf = _col(d, "NR_CPF_CANDIDATO", "NR_CPF")
            ds_bem = _col(d, "DS_BEM_CANDIDATO", "DS_TIPO_BEM_CANDIDATO")
            vr_bem = _safe_float(_col(d, "VR_BEM_CANDIDATO"))
            uf = _col(d, "SG_UF")
            ano = _col(d, "ANO_ELEICAO")

            if not sq and not nome:
                continue

            entity = CanonicalEntity(
                source_connector="tse",
                source_id=sq or item.raw_id,
                type="person",
                name=nome,
                identifiers={"cpf": cpf} if cpf else {},
                attrs={"uf": uf, "ano_eleicao": ano},
            )
            entities.append(entity)

            events.append(
                CanonicalEvent(
                    source_connector="tse",
                    source_id=item.raw_id,
                    type="patrimonio",
                    subtype="bem_candidato",
                    description=ds_bem,
                    occurred_at=_parse_any_datetime(f"{ano}-01-01") if ano else None,
                    value_brl=vr_bem,
                    attrs={
                        "sq_candidato": sq,
                        "descricao_bem": ds_bem,
                        "uf": uf,
                        "ano": ano,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=entity, role="candidato"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def _normalize_receitas(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            sq = _col(d, "SQ_CANDIDATO", "NR_SEQUENCIAL_CANDIDATO")
            nm_candidato = _col(d, "NM_CANDIDATO")
            nm_doador = _col(d, "NM_DOADOR", "NM_DOADOR_RFB")
            cpf_cnpj_doador = _col(d, "NR_CPF_CNPJ_DOADOR", "CPF_CNPJ_DOADOR")
            vr_receita = _safe_float(_col(d, "VR_RECEITA"))
            ds_origem = _col(d, "DS_ORIGEM_RECEITA", "DS_FONTE_RECEITA")
            uf = _col(d, "SG_UF")
            ano = _col(d, "ANO_ELEICAO")
            dt_receita = _col(d, "DT_RECEITA", "DATA_RECEITA")

            # Doador entity
            cpf_cnpj_clean = "".join(c for c in cpf_cnpj_doador if c.isdigit())
            if len(cpf_cnpj_clean) == 14:
                doador_type = "company"
                doador_identifiers: dict = {"cnpj": cpf_cnpj_clean}
            elif len(cpf_cnpj_clean) == 11:
                doador_type = "person"
                doador_identifiers = {"cpf": cpf_cnpj_clean}
            else:
                doador_type = "person"
                doador_identifiers = {}

            doador = CanonicalEntity(
                source_connector="tse",
                source_id=cpf_cnpj_clean or f"{item.raw_id}:doador",
                type=doador_type,
                name=nm_doador,
                identifiers=doador_identifiers,
                attrs={"uf": uf},
            )
            entities.append(doador)

            # Candidato entity (recipient)
            candidato = CanonicalEntity(
                source_connector="tse",
                source_id=sq or f"{item.raw_id}:candidato",
                type="person",
                name=nm_candidato,
                attrs={"uf": uf, "ano_eleicao": ano},
            )
            entities.append(candidato)

            events.append(
                CanonicalEvent(
                    source_connector="tse",
                    source_id=item.raw_id,
                    type="doacao_eleitoral",
                    subtype=ds_origem,
                    description=ds_origem,
                    occurred_at=_parse_any_datetime(dt_receita),
                    value_brl=vr_receita,
                    attrs={
                        "sq_candidato": sq,
                        "nm_doador": nm_doador,
                        "cpf_cnpj_doador": cpf_cnpj_doador,
                        "ds_origem": ds_origem,
                        "uf": uf,
                        "ano": ano,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=doador, role="doador"),
                        CanonicalEventParticipant(entity_ref=candidato, role="candidato"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def _normalize_despesas(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            sq = _col(d, "SQ_CANDIDATO", "NR_SEQUENCIAL_CANDIDATO")
            nm_candidato = _col(d, "NM_CANDIDATO")
            nm_fornecedor = _col(d, "NM_FORNECEDOR", "NM_FORNECEDOR_RFB")
            cpf_cnpj_fornecedor = _col(d, "NR_CPF_CNPJ_FORNECEDOR", "CPF_CNPJ_FORNECEDOR")
            vr_despesa = _safe_float(_col(d, "VR_DESPESA_CONTRATADA", "VR_DESPESA"))
            ds_origem = _col(d, "DS_ORIGEM_DESPESA", "DS_TIPO_DESPESA")
            uf = _col(d, "SG_UF")
            ano = _col(d, "ANO_ELEICAO")
            dt_despesa = _col(d, "DT_DESPESA", "DATA_DESPESA")

            # Supplier entity
            cpf_cnpj_clean = "".join(c for c in cpf_cnpj_fornecedor if c.isdigit())
            if len(cpf_cnpj_clean) == 14:
                forn_type = "company"
                forn_identifiers: dict = {"cnpj": cpf_cnpj_clean}
            elif len(cpf_cnpj_clean) == 11:
                forn_type = "person"
                forn_identifiers = {"cpf": cpf_cnpj_clean}
            else:
                forn_type = "company"
                forn_identifiers = {}

            fornecedor = CanonicalEntity(
                source_connector="tse",
                source_id=cpf_cnpj_clean or f"{item.raw_id}:fornecedor",
                type=forn_type,
                name=nm_fornecedor,
                identifiers=forn_identifiers,
                attrs={"uf": uf},
            )
            entities.append(fornecedor)

            # Candidato entity (spender)
            candidato = CanonicalEntity(
                source_connector="tse",
                source_id=sq or f"{item.raw_id}:candidato",
                type="person",
                name=nm_candidato,
                attrs={"uf": uf, "ano_eleicao": ano},
            )
            entities.append(candidato)

            events.append(
                CanonicalEvent(
                    source_connector="tse",
                    source_id=item.raw_id,
                    type="despesa_eleitoral",
                    subtype=ds_origem,
                    description=ds_origem,
                    occurred_at=_parse_any_datetime(dt_despesa),
                    value_brl=vr_despesa,
                    attrs={
                        "sq_candidato": sq,
                        "nm_fornecedor": nm_fornecedor,
                        "cpf_cnpj_fornecedor": cpf_cnpj_fornecedor,
                        "ds_origem": ds_origem,
                        "uf": uf,
                        "ano": ano,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=candidato, role="candidato"),
                        CanonicalEventParticipant(entity_ref=fornecedor, role="fornecedor"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=2, burst=4)

    def cleanup_bulk_files(self, job: "JobSpec", raw_run: object) -> int:  # type: ignore[override]
        """Delete all TSE CSV files once a run completes successfully."""
        import glob as _glob

        data_dir = os.environ.get("TSE_DATA_DIR", "/data/tse")
        deleted = 0
        for f in _glob.glob(os.path.join(data_dir, "*.csv")):
            try:
                os.remove(f)
                log.info("tse.cleanup_on_complete", file=os.path.basename(f))
                deleted += 1
            except OSError:
                pass
        return deleted
