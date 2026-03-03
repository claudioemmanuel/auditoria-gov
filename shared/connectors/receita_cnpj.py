"""Receita Federal CNPJ Bulk CSV Connector.

Reads the publicly available CNPJ open data published by Receita Federal:
- Empresas (companies)
- Socios (partners/shareholders — QSA)
- Estabelecimentos (branch offices)

Data is published monthly at: https://dados.rfb.gov.br/CNPJ/
Format: ~10 CSV files per category, semicolon-delimited, ISO-8859-1 encoding.

On first run, auto-downloads all ZIP files from dados.rfb.gov.br (total ~6GB).
Subsequent runs use already-extracted CSVs.
Configure data directory via RECEITA_CNPJ_DATA_DIR env var (default: /data/receita_cnpj).
"""

import csv
import os
import zipfile
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


_DATA_DIR = os.environ.get("RECEITA_CNPJ_DATA_DIR", "/data/receita_cnpj")
_RFB_BASE_URL = "https://dados.rfb.gov.br/CNPJ/"

# ZIP files to download from Receita Federal
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


async def _ensure_rfb_files(data_dir: str) -> None:
    """Download and extract Receita Federal CNPJ bulk files if not present.

    Files are large (~600MB each ZIP). Downloads are streamed and idempotent:
    if the extracted CSV already exists, the download is skipped.
    """
    os.makedirs(data_dir, exist_ok=True)

    for _category, zip_names in _RFB_ZIP_FILES.items():
        for zip_name in zip_names:
            csv_name = zip_name.replace(".zip", ".csv")
            csv_path = os.path.join(data_dir, csv_name)
            if os.path.exists(csv_path):
                continue  # Already extracted

            zip_path = os.path.join(data_dir, zip_name)
            if not os.path.exists(zip_path):
                url = f"{_RFB_BASE_URL}{zip_name}"
                log.info("receita_cnpj.downloading", file=zip_name)
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(600.0),
                    follow_redirects=True,
                ) as client:
                    async with client.stream("GET", url) as response:
                        if response.status_code == 404:
                            log.warning("receita_cnpj.file_not_found", file=zip_name)
                            continue
                        response.raise_for_status()
                        with open(zip_path, "wb") as f:
                            async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                                f.write(chunk)
                log.info("receita_cnpj.downloaded", file=zip_name)

            # Extract ZIP
            try:
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(data_dir)
                log.info("receita_cnpj.extracted", file=zip_name)
            except zipfile.BadZipFile:
                log.error("receita_cnpj.bad_zip", file=zip_name)
                os.remove(zip_path)


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


class ReceitaCNPJConnector(BaseConnector):
    """Bulk CSV connector for Receita Federal CNPJ open data."""

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
        return RateLimitPolicy(requests_per_second=1000, burst=1000)  # Local file

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Read CSV in chunks from local files.

        On first invocation, auto-downloads all bulk files from dados.rfb.gov.br.
        cursor = "file_idx:byte_offset" for resumption.
        """
        # Auto-download if files are not present
        await _ensure_rfb_files(_DATA_DIR)

        file_map = {
            "rf_empresas": "Empresas",
            "rf_socios": "Socios",
            "rf_estabelecimentos": "Estabelecimentos",
        }

        prefix = file_map.get(job.name, job.name)
        # Receita publishes multiple numbered files: Empresas0.csv, Empresas1.csv, ...
        csv_files = sorted(
            f for f in os.listdir(_DATA_DIR)
            if f.startswith(prefix) and f.endswith(".csv")
        ) if os.path.isdir(_DATA_DIR) else []

        if not csv_files:
            return [], None

        # Parse cursor: "file_idx:byte_offset"
        file_idx = 0
        byte_offset = 0
        if cursor:
            parts = cursor.split(":")
            file_idx = int(parts[0])
            byte_offset = int(parts[1]) if len(parts) > 1 else 0

        if file_idx >= len(csv_files):
            return [], None

        page_size = 10_000
        items: list[RawItem] = []
        current_file = csv_files[file_idx]
        filepath = os.path.join(_DATA_DIR, current_file)

        try:
            with open(filepath, "r", encoding="iso-8859-1") as f:
                f.seek(byte_offset)
                reader = csv.reader(f, delimiter=";")
                for i, row in enumerate(reader):
                    if i >= page_size:
                        break
                    raw_id = f"{job.name}:{file_idx}:{byte_offset + f.tell()}"
                    items.append(RawItem(raw_id=raw_id, data={"row": row, "file": current_file}))

                new_offset = f.tell()
        except FileNotFoundError:
            return [], None

        # Determine next cursor
        if len(items) < page_size:
            # Move to next file
            next_file_idx = file_idx + 1
            if next_file_idx < len(csv_files):
                next_cursor = f"{next_file_idx}:0"
            else:
                next_cursor = None
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

            # Create entity for the partner
            entity_type = "company" if tipo_socio == "1" else "person"
            identifiers: dict = {}
            if tipo_socio == "1" and doc_socio:
                identifiers["cnpj"] = doc_socio
            elif tipo_socio == "2" and doc_socio:
                identifiers["cpf_hash"] = doc_socio  # Already masked by Receita

            partner_entity = CanonicalEntity(
                source_connector="receita_cnpj",
                source_id=f"socio:{cnpj_basico}:{doc_socio or nome_socio}",
                type=entity_type,
                name=nome_socio,
                identifiers=identifiers,
                attrs={"qualificacao": qualificacao},
            )
            entities.append(partner_entity)

            # Create partnership event
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
                        CanonicalEventParticipant(
                            entity_ref=partner_entity,
                            role="partner",
                        ),
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

            # Build full CNPJ
            cnpj_full = f"{cnpj_basico}{cnpj_ordem}{cnpj_dv}"

            # Address fields
            logradouro = row[13].strip() if len(row) > 13 else ""
            numero = row[14].strip() if len(row) > 14 else ""
            municipio = row[18].strip() if len(row) > 18 else ""
            uf = row[19].strip() if len(row) > 19 else ""
            cep = row[17].strip() if len(row) > 17 else ""

            # Contact
            telefone = row[20].strip() if len(row) > 20 else ""
            email = row[27].strip() if len(row) > 27 else ""

            address = f"{logradouro}, {numero} - {municipio}/{uf}" if logradouro else ""

            entities.append(
                CanonicalEntity(
                    source_connector="receita_cnpj",
                    source_id=f"estab:{cnpj_full}",
                    type="company",
                    name=f"Estabelecimento {cnpj_full}",
                    identifiers={
                        "cnpj": cnpj_full,
                        "cnpj_basico": cnpj_basico,
                    },
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
