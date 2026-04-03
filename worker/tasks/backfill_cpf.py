"""Backfill raw CPF from raw_source.raw_data into entity.identifiers.

One-time maintenance task to recover CPF values that were previously
destroyed by _normalize_identifiers() (which used to pop the raw CPF
and only keep cpf_hash + cpf_masked).
"""
from celery import shared_task
from sqlalchemy import select, text

from shared.logging import log


_CPF_EXTRACTORS: dict[str, list[str]] = {
    "portal_transparencia": ["cpf", "cpfFormatado"],
    "tse": ["NR_CPF_CANDIDATO", "NR_CPF"],
    "compras_gov": ["cpf", "cnpjCpf"],
    "pncp": ["niFornecedor"],
}


def _extract_cpf_from_raw(raw_data: dict, connector: str) -> str | None:
    """Try to extract a valid 11-digit CPF from raw_data based on connector."""
    keys = _CPF_EXTRACTORS.get(connector, [])
    for key in keys:
        value = raw_data.get(key)
        if not value:
            continue
        digits = "".join(c for c in str(value) if c.isdigit())
        if len(digits) == 11:
            return digits
    return None


@shared_task(
    name="worker.tasks.backfill_cpf.backfill_cpf_from_raw_sources",
    soft_time_limit=1800,
    time_limit=1900,
    max_retries=1,
)
def backfill_cpf_from_raw_sources(batch_size: int = 500) -> dict:
    """Recover raw CPF from raw_source.raw_data for person entities missing it."""
    from shared.config import settings
    from shared.db_sync import SyncSession
    from shared.models.orm import Entity
    from shared.utils.hashing import hash_cpf

    log.info("backfill_cpf.start")

    updated = 0
    not_found = 0
    cleaned_partial = 0

    with SyncSession() as session:
        # Find person entities that have cpf_hash but no raw cpf
        candidates = session.execute(
            text("""
                SELECT e.id
                FROM entity e
                WHERE e.type = 'person'
                  AND e.identifiers->>'cpf_hash' IS NOT NULL
                  AND e.identifiers->>'cpf' IS NULL
            """)
        ).fetchall()

        entity_ids = [row[0] for row in candidates]
        log.info("backfill_cpf.candidates", count=len(entity_ids))

        for i in range(0, len(entity_ids), batch_size):
            batch_ids = entity_ids[i : i + batch_size]

            # Fetch entities with their raw sources
            rows = session.execute(
                text("""
                    SELECT e.id, rs.connector, rs.raw_data
                    FROM entity e
                    JOIN entity_raw_source ers ON ers.entity_id = e.id
                    JOIN raw_source rs ON rs.id = ers.raw_source_id
                    WHERE e.id = ANY(:ids)
                      AND rs.raw_data IS NOT NULL
                """),
                {"ids": batch_ids},
            ).fetchall()

            # Group raw sources by entity
            entity_raws: dict[str, list[tuple[str, dict]]] = {}
            for eid, connector, raw_data in rows:
                entity_raws.setdefault(str(eid), []).append((connector, raw_data or {}))

            for eid_str in [str(eid) for eid in batch_ids]:
                raws = entity_raws.get(eid_str, [])
                cpf = None
                for connector, raw_data in raws:
                    cpf = _extract_cpf_from_raw(raw_data, connector)
                    if cpf:
                        break

                if not cpf:
                    not_found += 1
                    continue

                # Load and update entity
                entity = session.get(Entity, eid_str)
                if entity is None:
                    continue

                identifiers = dict(entity.identifiers or {})
                identifiers["cpf"] = cpf
                identifiers["cpf_hash"] = hash_cpf(cpf, settings.CPF_HASH_SALT)
                if "cpf_masked" in identifiers:
                    del identifiers["cpf_masked"]
                    cleaned_partial += 1
                entity.identifiers = identifiers
                updated += 1

            session.commit()

    result = {
        "status": "ok",
        "candidates": len(entity_ids),
        "updated": updated,
        "not_found": not_found,
        "cleaned_cpf_masked": cleaned_partial,
    }
    log.info("backfill_cpf.done", **result)
    return result
