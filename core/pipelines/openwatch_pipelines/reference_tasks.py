"""Celery task for populating the reference_data table."""

import os
import zipfile

import httpx

from celery import shared_task

from openwatch_config.settings import settings
from openwatch_db.db_sync import SyncSession
from openwatch_utils.logging import log
from openwatch_utils.sync_async import run_async

# Misc Receita Federal reference files (small, a few MB each).
# Large Empresas/Socios/Estabelecimentos ZIPs are NOT listed here.
_RF_MISC_FILES: list[tuple[str, str]] = [
    ("CNAEs.zip", "CNAES.csv"),
    ("Naturezas.zip", "Naturezas.csv"),
    ("Qualificacoes.zip", "Qualificacoes.csv"),
    ("Municipios.zip", "Municipios.csv"),
    ("Paises.zip", "Paises.csv"),
    ("Motivos.zip", "Motivos.csv"),
]

_RF_BASE_URL = "https://dados.rfb.gov.br/CNPJ/"


def _ensure_rf_reference_files(data_dir: str) -> int:
    """Download and extract Receita Federal misc reference ZIPs if not present.

    Returns the number of files successfully downloaded.
    """
    os.makedirs(data_dir, exist_ok=True)
    downloaded = 0

    for zip_name, csv_name in _RF_MISC_FILES:
        csv_path = os.path.join(data_dir, csv_name)
        if os.path.exists(csv_path):
            continue

        zip_path = os.path.join(data_dir, zip_name)
        url = _RF_BASE_URL + zip_name

        if not os.path.exists(zip_path):
            log.info("reference_seed.rf_download_start", zip=zip_name, url=url)
            try:
                with httpx.stream(
                    "GET", url, timeout=300, follow_redirects=True
                ) as response:
                    if response.status_code == 404:
                        log.warning(
                            "reference_seed.rf_download_404",
                            zip=zip_name,
                            url=url,
                        )
                        continue
                    response.raise_for_status()
                    with open(zip_path, "wb") as fh:
                        for chunk in response.iter_bytes():
                            fh.write(chunk)
            except httpx.HTTPStatusError as exc:
                log.warning(
                    "reference_seed.rf_download_error",
                    zip=zip_name,
                    status=exc.response.status_code,
                )
                continue
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "reference_seed.rf_download_error",
                    zip=zip_name,
                    error=str(exc),
                )
                continue

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(data_dir)
            os.remove(zip_path)
            downloaded += 1
            log.info("reference_seed.rf_extracted", csv=csv_name)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "reference_seed.rf_extract_error",
                zip=zip_name,
                error=str(exc),
            )

    return downloaded


@shared_task(name="openwatch_pipelines.reference_tasks.seed_reference_data")
def seed_reference_data():
    """Populate reference_data table from external sources (one-time).

    Seeds: IBGE municipalities, IBGE UFs, SIAPE organs,
    and Receita Federal lookup tables (if CSVs are available).
    """
    from openwatch_services.reference_seed import (
        seed_ibge_municipios,
        seed_ibge_ufs,
        seed_receita_reference,
        seed_siape_orgaos,
    )

    results: dict[str, object] = {}

    with SyncSession() as session:
        results["ibge_municipios"] = run_async(seed_ibge_municipios(session))
        results["ibge_ufs"] = run_async(seed_ibge_ufs(session))
        results["siape_orgaos"] = run_async(seed_siape_orgaos(session))

        data_dir = settings.RECEITA_CNPJ_DATA_DIR

        # Attempt to download misc RF reference files before checking for CSVs.
        rf_downloaded = 0
        try:
            rf_downloaded = _ensure_rf_reference_files(data_dir)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "reference_seed.rf_ensure_failed",
                error=str(exc),
            )

        cnaes_path = os.path.join(data_dir, "CNAES.csv")
        if os.path.exists(cnaes_path):
            rf_results = seed_receita_reference(session, data_dir)
            results.update(rf_results)
        else:
            log.info(
                "reference_seed.rf_skipped",
                reason="CNAES.csv not found",
                data_dir=data_dir,
                downloaded=rf_downloaded,
            )

    log.info("reference_seed.complete", results=results)
    return results
