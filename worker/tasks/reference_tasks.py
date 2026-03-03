"""Celery task for populating the reference_data table."""

import os

from celery import shared_task

from shared.config import settings
from shared.db_sync import SyncSession
from shared.logging import log
from shared.utils.sync_async import run_async


@shared_task(name="worker.tasks.reference_tasks.seed_reference_data")
def seed_reference_data():
    """Populate reference_data table from external sources (one-time).

    Seeds: IBGE municipalities, IBGE UFs, SIAPE organs,
    and Receita Federal lookup tables (if CSVs are available).
    """
    from shared.services.reference_seed import (
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
        cnaes_path = os.path.join(data_dir, "CNAES.csv")
        if os.path.exists(cnaes_path):
            rf_results = seed_receita_reference(session, data_dir)
            results.update(rf_results)
        else:
            log.info(
                "reference_seed.rf_skipped",
                reason="CNAES.csv not found",
                data_dir=data_dir,
            )

    log.info("reference_seed.complete", results=results)
    return results
