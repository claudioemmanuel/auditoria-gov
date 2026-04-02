"""Receita Federal CNPJ Bulk CSV Connector.

Reads the publicly available CNPJ open data published by Receita Federal:
- Empresas (companies)
- Socios (partners/shareholders — QSA)
- Estabelecimentos (branch offices)

Data is published monthly via Nextcloud at: https://arquivos.receitafederal.gov.br
Format: ~10 CSV files per category, semicolon-delimited, ISO-8859-1 encoding.

Download strategy: lazy per-file — only ONE ZIP is downloaded and extracted at a time.
When fetch() exhausts a file, the CSV is deleted immediately before moving to the next.
Peak disk usage: ~600MB–1.5GB (one active CSV) instead of ~6-10GB (all files).

Data directory is configurable via RECEITA_CNPJ_DATA_DIR (default: /data/receita_cnpj).
"""

import csv
import os
import shutil
import zipfile
from typing import Optional

import httpx

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_utils.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem


_DATA_DIR = os.environ.get("RECEITA_CNPJ_DATA_DIR", "/data/receita_cnpj")
_RFB_NEXTCLOUD_BASE = os.environ.get(
    "RECEITA_CNPJ_NEXTCLOUD_BASE",
    "https://arquivos.receitafederal.gov.br",
)
_RFB_SHARE_TOKEN = os.environ.get("RECEITA_CNPJ_SHARE_TOKEN", "gn672Ad4CF8N6TK")
_RFB_CNPJ_WEBDAV_PATH = "/public.php/webdav/Dados/Cadastros/CNPJ"
_MIN_FREE_BYTES = 2 * 1024 ** 3  # 2 GB


class InsufficientDiskError(RuntimeError):
    """Raised when available disk space is below the minimum required to download a ZIP."""


async def _discover_latest_month() -> str:
    """Query Nextcloud WebDAV to find the latest available CNPJ month (YYYY-MM)."""
    webdav_url = f"{_RFB_NEXTCLOUD_BASE}{_RFB_CNPJ_WEBDAV_PATH}/"
    auth = (_RFB_SHARE_TOKEN, "")
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        resp = await client.request(
            "PROPFIND",
            webdav_url,
            headers={"Depth": "1"},
            auth=auth,
        )
        resp.raise_for_status()

    # Parse <d:href> values matching /YYYY-MM/ pattern
    import re
    months = re.findall(r"/(\d{4}-\d{2})/?(?:</|$)", resp.text)
    if not months:
        raise RuntimeError("receita_cnpj: no CNPJ month directories found via WebDAV")
    return sorted(set(months))[-1]  # Latest YYYY-MM


def _build_download_url(month: str, zip_name: str) -> str:
    """Build the Nextcloud direct-download URL for a given CNPJ ZIP."""
    path = f"/Dados/Cadastros/CNPJ/{month}"
    return (
        f"{_RFB_NEXTCLOUD_BASE}/index.php/s/{_RFB_SHARE_TOKEN}"
        f"/download?path={path}&files={zip_name}"
    )


def _safe_extractall(zip_path: str, dest_dir: str) -> None:
    """Extract ZIP with path traversal (Zip Slip) protection."""
    dest = os.path.realpath(dest_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            member_path = os.path.realpath(os.path.join(dest, member))
            if not member_path.startswith(dest + os.sep) and member_path != dest:
                raise ValueError(f"Zip Slip blocked: {member}")
        z.extractall(dest_dir)


# ZIP files published by Receita Federal
_RFB_ZIP_FILES: dict[str, list[str]] = {
    "Empresas": [f"Empresas{i}.zip" for i in range(10)],
    "Socios": [f"Socios{i}.zip" for i in range(10)],
    "Estabelecimentos": [f"Estabelecimentos{i}.zip" for i in range(10)],
    "misc": [
        "CNAEs.zip",
        "Naturezas.zip",
        "Qualificacoes.zip",
        "Municipios.zip",
        "Paises.zip",
        "Motivos.zip",
    ],
}


async def _ensure_single_file(data_dir: str, zip_name: str, url: str) -> None:
    """Download and extract ONE ZIP file if its CSV is not already present.

    Idempotent: returns immediately if the CSV already exists on disk.
    Raises InsufficientDiskError if free disk space is below 2 GB.
    """
    os.makedirs(data_dir, exist_ok=True)

    csv_name = zip_name.replace(".zip", ".csv")
    csv_path = os.path.join(data_dir, csv_name)
    if os.path.exists(csv_path):
        return  # Already extracted — nothing to do

    free = shutil.disk_usage(data_dir).free
    if free < _MIN_FREE_BYTES:
        raise InsufficientDiskError(
            f"Insufficient disk space to download {zip_name}: "
            f"need ≥2 GB, have {free / 1024**3:.1f} GB free in {data_dir}"
        )

    zip_path = os.path.join(data_dir, zip_name)
    if not os.path.exists(zip_path):
        log.info("receita_cnpj.downloading", file=zip_name)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(600.0),
            follow_redirects=True,
        ) as client:
            async with client.stream("GET", url) as response:
                if response.status_code == 404:
                    log.warning("receita_cnpj.file_not_found", file=zip_name)
                    return
                response.raise_for_status()
                with open(zip_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        log.info("receita_cnpj.downloaded", file=zip_name)

    try:
        _safe_extractall(zip_path, data_dir)
        log.info("receita_cnpj.extracted", file=zip_name)
        try:
            os.remove(zip_path)
            log.info("receita_cnpj.zip_deleted", file=zip_name)
        except OSError:
            pass
    except zipfile.BadZipFile:
        log.error("receita_cnpj.bad_zip", file=zip_name)
        try:
            os.remove(zip_path)
        except OSError:
            pass

    log.info("receita_cnpj.file_ready", file=csv_name)


def _delete_exhausted_file(data_dir: str, csv_name: str) -> None:
    """Delete a CSV that has been fully consumed by fetch() to reclaim disk space."""
    path = os.path.join(data_dir, csv_name)
    try:
        os.remove(path)
        log.info("receita_cnpj.file_exhausted_deleted", file=csv_name)
    except FileNotFoundError:
        pass


# Natureza jurídica codes for relevant entity types
_NATUREZA_PUBLICA = {
    "1015",  # Órgão Público do Poder Executivo Federal
    "1023",  # Órgão Público do Poder Executivo Estadual ou do DF
    "1031",  # Órgão Público do Poder Executivo Municipal
    "1040",  # Órgão Público do Poder Legislativo Federal
    "1058",  # Órgão Público do Poder Legislativo Estadual ou do DF
    "1066",  # Órgão Público do Poder Legislativo Municipal
    "1074",  # Órgão Público do Poder Judiciário Federal
    "1082",  # Órgão Público do Poder Judiciário Estadual
}

_JOB_PREFIX = {
    "rf_empresas":        "Empresas",
    "rf_socios":          "Socios",
    "rf_estabelecimentos":"Estabelecimentos",
}


class ReceitaCNPJConnector(BaseConnector):
    """Bulk CSV connector for Receita Federal CNPJ open data.

    All three jobs (rf_empresas, rf_socios, rf_estabelecimentos) are always enabled.
    Files are downloaded lazily — one ZIP at a time — and deleted immediately after
    being fully consumed, keeping peak disk usage under ~1.5 GB.
    """

    _cnpj_month: Optional[str] = None

    async def _get_month(self) -> str:
        if self._cnpj_month is None:
            self._cnpj_month = await _discover_latest_month()
            log.info("receita_cnpj.month_discovered", month=self._cnpj_month)
        return self._cnpj_month

    @property
    def name(self) -> str:
        return "receita_cnpj"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="rf_empresas",
                description="Companies from Receita Federal",
                domain="empresa",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="rf_socios",
                description="QSA — Company partners",
                domain="empresa",
                supports_incremental=False,
                enabled=True,
            ),
            JobSpec(
                name="rf_estabelecimentos",
                description="Branch offices",
                domain="empresa",
                supports_incremental=False,
                enabled=True,
            ),
        ]

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=1000, burst=1000)  # Local file read

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Read CSV rows in pages of 10,000, downloading each file lazily on demand.

        cursor = "file_idx:byte_offset"
        When a file is exhausted the CSV is deleted immediately before moving to next.
        """
        prefix = _JOB_PREFIX.get(job.name, job.name)
        zip_names: list[str] = _RFB_ZIP_FILES.get(prefix, [])
        csv_names = [z.replace(".zip", ".csv") for z in zip_names]
        total_files = len(csv_names)

        if not total_files:
            return [], None

        # Parse cursor
        file_idx = 0
        byte_offset = 0
        if cursor:
            parts = cursor.split(":")
            file_idx = int(parts[0])
            byte_offset = int(parts[1]) if len(parts) > 1 else 0

        if file_idx >= total_files:
            return [], None

        current_csv = csv_names[file_idx]
        month = await self._get_month()
        url = _build_download_url(month, zip_names[file_idx])

        # Lazily download only the file we need right now
        await _ensure_single_file(_DATA_DIR, zip_names[file_idx], url)

        filepath = os.path.join(_DATA_DIR, current_csv)
        page_size = 10_000
        items: list[RawItem] = []

        try:
            with open(filepath, "r", encoding="iso-8859-1") as f:
                f.seek(byte_offset)
                for _ in range(page_size):
                    line = f.readline()
                    if not line:
                        break
                    row = next(csv.reader([line], delimiter=";"))
                    raw_id = f"{job.name}:{file_idx}:{f.tell()}"
                    items.append(RawItem(raw_id=raw_id, data={"row": row, "file": current_csv}))
                new_offset = f.tell()
        except FileNotFoundError:
            return [], None

        # Determine next cursor and clean up exhausted files
        if len(items) < page_size:
            # This file is fully consumed — delete it immediately to reclaim disk
            _delete_exhausted_file(_DATA_DIR, current_csv)

            next_file_idx = file_idx + 1
            next_cursor: Optional[str] = (
                f"{next_file_idx}:0" if next_file_idx < total_files else None
            )
        else:
            next_cursor = f"{file_idx}:{new_offset}"

        return items, next_cursor

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "rf_empresas":
            return self._normalize_empresas(raw_items)
        elif job.name == "rf_socios":
            return self._normalize_socios(raw_items)
        elif job.name == "rf_estabelecimentos":
            return self._normalize_estabelecimentos(raw_items)
        return NormalizeResult()

    def _normalize_empresas(self, raw_items: list[RawItem]) -> NormalizeResult:
        """Normalize company records.

        CSV columns (typical): cnpj_basico, razao_social, natureza_juridica,
        qualificacao_responsavel, capital_social, porte, ente_federativo
        """
        entities: list[CanonicalEntity] = []

        for item in raw_items:
            row = item.data.get("row", [])
            if len(row) < 5:
                continue

            cnpj_basico = row[0].strip()
            razao_social = row[1].strip()
            natureza = row[2].strip() if len(row) > 2 else ""
            capital_social = row[4].strip().replace(",", ".") if len(row) > 4 else "0"

            try:
                capital = float(capital_social)
            except (ValueError, TypeError):
                capital = 0.0

            entity_type = "org" if natureza in _NATUREZA_PUBLICA else "company"

            entities.append(
                CanonicalEntity(
                    source_connector="receita_cnpj",
                    source_id=f"empresa:{cnpj_basico}",
                    type=entity_type,
                    name=razao_social,
                    identifiers={"cnpj_basico": cnpj_basico},
                    attrs={
                        "natureza_juridica": natureza,
                        "capital_social": capital,
                        "data_source": "receita_federal",
                    },
                )
            )

        return NormalizeResult(entities=entities)

    def _normalize_socios(self, raw_items: list[RawItem]) -> NormalizeResult:
        """Normalize partner/shareholder records.

        Creates person entities + events linking them to companies.
        """
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            row = item.data.get("row", [])
            if len(row) < 6:
                continue

            cnpj_basico = row[0].strip()
            tipo_socio = row[1].strip()  # 1=PJ, 2=PF, 3=Estrangeiro
            nome_socio = row[2].strip()
            doc_socio = row[3].strip() if len(row) > 3 else ""
            qualificacao = row[4].strip() if len(row) > 4 else ""
            data_entrada = row[5].strip() if len(row) > 5 else ""

            if not nome_socio:
                continue

            entity_type = "company" if tipo_socio == "1" else "person"
            identifiers: dict = {}
            if tipo_socio == "1" and doc_socio:
                identifiers["cnpj"] = doc_socio
            elif tipo_socio == "2" and doc_socio:
                doc_clean = "".join(c for c in doc_socio if c.isdigit())
                if len(doc_clean) == 11:
                    identifiers["cpf"] = doc_clean
                else:
                    # Receita masks CPF of partners (***NNNNNN**) — store as partial
                    identifiers["cpf_partial"] = doc_socio

            partner_entity = CanonicalEntity(
                source_connector="receita_cnpj",
                source_id=f"socio:{cnpj_basico}:{doc_socio or nome_socio}",
                type=entity_type,
                name=nome_socio,
                identifiers=identifiers,
                attrs={"qualificacao": qualificacao},
            )
            entities.append(partner_entity)

            # source_id matches _normalize_empresas so upsert merges them.
            company_entity = CanonicalEntity(
                source_connector="receita_cnpj",
                source_id=f"empresa:{cnpj_basico}",
                type="company",
                name=f"Empresa {cnpj_basico}",
                identifiers={"cnpj_basico": cnpj_basico},
            )
            entities.append(company_entity)

            events.append(
                CanonicalEvent(
                    source_connector="receita_cnpj",
                    source_id=f"qsa:{cnpj_basico}:{doc_socio or nome_socio}",
                    type="sociedade",
                    subtype="qsa",
                    description=f"Sócio {nome_socio} na empresa {cnpj_basico}",
                    attrs={
                        "cnpj_basico": cnpj_basico,
                        "qualificacao": qualificacao,
                        "data_entrada": data_entrada,
                        "tipo_socio": tipo_socio,
                    },
                    participants=[
                        CanonicalEventParticipant(entity_ref=company_entity, role="company"),
                        CanonicalEventParticipant(entity_ref=partner_entity, role="partner"),
                    ],
                )
            )

        return NormalizeResult(entities=entities, events=events)

    def _normalize_estabelecimentos(self, raw_items: list[RawItem]) -> NormalizeResult:
        """Normalize branch office records.

        Enriches company entities with address, CNAE, phone, email.
        """
        entities: list[CanonicalEntity] = []

        for item in raw_items:
            row = item.data.get("row", [])
            if len(row) < 20:
                continue

            cnpj_basico = row[0].strip()
            cnpj_ordem = row[1].strip() if len(row) > 1 else ""
            cnpj_dv = row[2].strip() if len(row) > 2 else ""
            situacao_cadastral = row[5].strip() if len(row) > 5 else ""
            data_situacao = row[6].strip() if len(row) > 6 else ""
            data_abertura = row[10].strip() if len(row) > 10 else ""
            cnae_principal = row[11].strip() if len(row) > 11 else ""

            cnpj_full = f"{cnpj_basico}{cnpj_ordem}{cnpj_dv}"

            logradouro = row[13].strip() if len(row) > 13 else ""
            numero = row[14].strip() if len(row) > 14 else ""
            municipio = row[18].strip() if len(row) > 18 else ""
            uf = row[19].strip() if len(row) > 19 else ""
            cep = row[17].strip() if len(row) > 17 else ""
            telefone = row[20].strip() if len(row) > 20 else ""
            email = row[27].strip() if len(row) > 27 else ""

            address = f"{logradouro}, {numero} - {municipio}/{uf}" if logradouro else ""

            entities.append(
                CanonicalEntity(
                    source_connector="receita_cnpj",
                    source_id=f"estab:{cnpj_full}",
                    type="company",
                    name=f"Estabelecimento {cnpj_full}",
                    identifiers={"cnpj": cnpj_full, "cnpj_basico": cnpj_basico},
                    attrs={
                        "cnae_principal": cnae_principal,
                        "situacao_cadastral": situacao_cadastral,
                        "data_situacao": data_situacao,
                        "data_abertura": data_abertura,
                        "address": address,
                        "cep": cep,
                        "telefone": telefone,
                        "email": email,
                        "uf": uf,
                        "municipio": municipio,
                    },
                )
            )

        return NormalizeResult(entities=entities)

    def cleanup_bulk_files(self, job: "JobSpec", raw_run: object) -> int:  # type: ignore[override]
        """Delete any remaining Receita Federal CSV/ZIP files after a run completes."""
        import glob as _glob

        deleted = 0
        for f in _glob.glob(os.path.join(_DATA_DIR, "*")):
            if os.path.isfile(f):
                try:
                    os.remove(f)
                    log.info("receita_cnpj.cleanup_on_complete", file=os.path.basename(f))
                    deleted += 1
                except OSError:
                    pass
        return deleted
