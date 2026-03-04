import uuid as _uuid_mod
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

from celery import shared_task

from shared.logging import log

_PROBABILISTIC_THRESHOLD = 0.85
_PROBABILISTIC_MAX_BUCKET_SIZE = 300
_PROBABILISTIC_MAX_ENTITIES = 5000

# Semantic ER pass constants
_SEMANTIC_DISTANCE_THRESHOLD = 0.12   # cosine distance ≤ 0.12 ≡ similarity ≥ 0.88
_SEMANTIC_MAX_UNMATCHED = 10_000      # skip semantic pass for very large datasets

_PHOTO_KEYS = ("url_foto", "urlFoto", "photo_url", "UrlFotoParlamentar")


def _extract_photo_url(attrs: dict | None) -> str | None:
    source = attrs or {}
    for key in _PHOTO_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _node_attrs_snapshot(entity: dict) -> dict:
    identifiers = entity.get("identifiers") or {}
    attrs = entity.get("attrs") or {}
    snapshot = {
        "identifiers": identifiers,
        "attrs": attrs,
    }
    photo_url = _extract_photo_url(attrs)
    if photo_url:
        snapshot["url_foto"] = photo_url
    for key in ("cargo", "partido", "uf", "sigla_uf", "sigla_partido", "orgao"):
        value = attrs.get(key)
        if value not in (None, ""):
            snapshot[key] = value
    return snapshot


def _parse_iso_dt(value: object) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _merge_edge_attrs(existing: dict, incoming: dict, max_event_ids: int = 100) -> dict:
    attrs = dict(existing or {})
    old_event_ids = [str(v) for v in (attrs.get("event_ids") or [])]
    new_event_ids = [str(v) for v in (incoming.get("event_ids") or [])]
    merged_event_ids = list(dict.fromkeys(old_event_ids + new_event_ids))
    attrs["event_ids"] = merged_event_ids[:max_event_ids]

    old_pairs = attrs.get("role_pairs_count") or {}
    new_pairs = incoming.get("role_pairs_count") or {}
    merged_pairs: dict[str, int] = {}
    for key, value in old_pairs.items():
        merged_pairs[str(key)] = int(value)
    for key, value in new_pairs.items():
        merged_pairs[str(key)] = merged_pairs.get(str(key), 0) + int(value)
    attrs["role_pairs_count"] = merged_pairs

    incoming_first = _parse_iso_dt(incoming.get("first_seen_at"))
    incoming_last = _parse_iso_dt(incoming.get("last_seen_at"))
    existing_first = _parse_iso_dt(attrs.get("first_seen_at"))
    existing_last = _parse_iso_dt(attrs.get("last_seen_at"))

    if incoming_first is not None:
        if existing_first is None or incoming_first < existing_first:
            attrs["first_seen_at"] = incoming_first.isoformat()
        elif existing_first is not None:
            attrs["first_seen_at"] = existing_first.isoformat()
    elif existing_first is not None:
        attrs["first_seen_at"] = existing_first.isoformat()

    if incoming_last is not None:
        if existing_last is None or incoming_last > existing_last:
            attrs["last_seen_at"] = incoming_last.isoformat()
        elif existing_last is not None:
            attrs["last_seen_at"] = existing_last.isoformat()
    elif existing_last is not None:
        attrs["last_seen_at"] = existing_last.isoformat()

    if incoming.get("source_role"):
        attrs["source_role"] = incoming["source_role"]
    if incoming.get("target_role"):
        attrs["target_role"] = incoming["target_role"]
    if incoming.get("edge_label"):
        attrs["edge_label"] = incoming["edge_label"]
    return attrs


def _should_run_probabilistic(entity_count: int) -> bool:
    return entity_count <= _PROBABILISTIC_MAX_ENTITIES


def _build_deterministic_matches(entities: list[dict]):
    """Build deterministic matches with identifier indexing instead of O(n²) scans."""
    from shared.er.matching import deterministic_match
    from shared.er.normalize import normalize_entity_for_matching

    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for entity in entities:
        normalized = normalize_entity_for_matching(
            entity.get("name", ""),
            entity.get("identifiers") or {},
        )
        if normalized["cnpj"]:
            buckets[(entity["type"], "cnpj", normalized["cnpj"])].append(entity)
            continue
        if normalized["cpf_hash"]:
            buckets[(entity["type"], "cpf_hash", normalized["cpf_hash"])].append(entity)

    matches = []
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        for left, right in combinations(bucket, 2):
            match = deterministic_match(left, right)
            if match is not None:
                matches.append(match)
    return matches


def _build_probabilistic_matches(entities: list[dict], matched_ids: set):
    """Build probabilistic matches using blocking to avoid full pairwise comparisons."""
    from shared.er.matching import probabilistic_match
    from shared.er.normalize import normalize_entity_for_matching

    buckets: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for entity in entities:
        entity_id = entity["id"]
        if entity_id in matched_ids:
            continue

        normalized = normalize_entity_for_matching(
            entity.get("name", ""),
            entity.get("identifiers") or {},
        )
        name_norm = normalized["name_norm"]
        if not name_norm:
            continue

        tokens = sorted(normalized["tokens"])
        lead_token = tokens[0] if tokens else ""
        # Block by entity type + normalized prefix + first semantic token.
        block_key = (
            entity["type"],
            name_norm[:4],
            lead_token[:8],
        )
        buckets[block_key].append(entity)

    matches = []
    skipped_buckets = 0
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        if len(bucket) > _PROBABILISTIC_MAX_BUCKET_SIZE:
            skipped_buckets += 1
            continue
        for left, right in combinations(bucket, 2):
            match = probabilistic_match(
                left,
                right,
                threshold=_PROBABILISTIC_THRESHOLD,
            )
            if match is not None:
                matches.append(match)

    if skipped_buckets:
        log.warning(
            "er.probabilistic_skipped_large_buckets",
            buckets=skipped_buckets,
            max_bucket_size=_PROBABILISTIC_MAX_BUCKET_SIZE,
        )
    return matches


def _build_semantic_matches(session, entities: list[dict], matched_ids: set) -> list:
    """Semantic ER pass using pgvector cosine similarity on entity name embeddings.

    Runs after deterministic + probabilistic passes.
    Only iterates over entities NOT yet matched in prior passes.
    Threshold: cosine distance <= 0.12 (cosine similarity >= 0.88).
    Requires same entity.type for a match to avoid cross-type false positives.

    Args:
        session: Synchronous SQLAlchemy session (SyncSession).
        entities: All entity dicts being processed in this ER run.
        matched_ids: Set of entity UUIDs already matched in prior passes.

    Returns:
        List of MatchResult objects for semantic matches found.
    """
    from sqlalchemy import text as sa_text

    from shared.er.matching import MatchResult
    from shared.repo.queries import get_entity_embeddings_for_er

    unmatched = [e for e in entities if e["id"] not in matched_ids]

    if not unmatched:
        return []

    if len(unmatched) > _SEMANTIC_MAX_UNMATCHED:
        log.warning(
            "er.semantic_skipped_large_dataset",
            entity_count=len(unmatched),
            limit=_SEMANTIC_MAX_UNMATCHED,
        )
        return []

    embeddings_map = get_entity_embeddings_for_er(session, [e["id"] for e in unmatched])

    if not embeddings_map:
        log.info("er.semantic_no_embeddings")
        return []

    # Optimize pgvector HNSW search for ER batch (transaction-scoped).
    try:
        session.execute(sa_text("SET LOCAL hnsw.ef_search = 100"))
    except Exception:
        pass  # Non-critical; continue without the hint.

    entity_type_map = {str(e["id"]): e["type"] for e in entities}
    checked_pairs: set = set()
    matches: list = []

    for entity in unmatched:
        entity_id_str = str(entity["id"])
        emb = embeddings_map.get(entity_id_str)
        if emb is None:
            continue

        vec_str = "[" + ",".join(str(v) for v in emb) + "]"
        sql = sa_text("""
            SELECT tc.source_id, (te.embedding <=> :query_vec::vector) AS distance
            FROM text_embedding te
            JOIN text_corpus tc ON tc.id = te.corpus_id
            WHERE tc.source_type = 'entity'
              AND tc.source_id != :exclude_id
              AND (te.embedding <=> :query_vec::vector) <= :threshold
            ORDER BY te.embedding <=> :query_vec::vector
            LIMIT 5
        """)
        rows = session.execute(
            sql,
            {
                "query_vec": vec_str,
                "threshold": _SEMANTIC_DISTANCE_THRESHOLD,
                "exclude_id": entity_id_str,
            },
        ).fetchall()

        for row in rows:
            neighbor_id_str = row.source_id
            if entity_type_map.get(neighbor_id_str) != entity["type"]:
                continue
            pair = tuple(sorted([entity_id_str, neighbor_id_str]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            similarity = 1.0 - float(row.distance)
            matches.append(
                MatchResult(
                    entity_a_id=_uuid_mod.UUID(entity_id_str),
                    entity_b_id=_uuid_mod.UUID(neighbor_id_str),
                    match_type="semantic",
                    score=similarity,
                    reason=f"Embedding cosine similarity: {similarity:.3f}",
                )
            )

    return matches


_ER_BATCH_SIZE = 50_000      # entities per matching batch
_ER_EDGE_BATCH_SIZE = 10_000  # participants per edge-building batch (keep IN params < 65535)
_IN_CHUNK = 5_000             # max IDs per IN clause


@shared_task(name="worker.tasks.er_tasks.run_entity_resolution")
def run_entity_resolution():
    """Run batched entity resolution pipeline.

    Processes entities in batches of _ER_BATCH_SIZE to avoid OOM on large
    datasets. Each batch: load → match → cluster → commit → free memory → next.

    Cross-batch deterministic linking is handled by an in-memory identifier
    index (cnpj → cluster_id, cpf_hash → cluster_id) so entities sharing a
    unique identifier across batches still get merged.

    Phases:
    1. Batched entity matching + clustering (deterministic + probabilistic).
    2. Batched edge building from event-participant relationships.
    3. Watermark update for incremental re-runs.
    """
    from sqlalchemy import or_, select, text as sa_text, update

    from shared.db_sync import SyncSession
    from shared.er.clustering import cluster_entities
    from shared.er.edges import build_structural_edges
    from shared.er.normalize import normalize_entity_for_matching
    from shared.models.orm import Entity, ERRunState, Event, EventParticipant, GraphEdge, GraphNode

    # Unique integer key for the ER singleton advisory lock.
    _ER_LOCK_KEY = 7349812

    log.info("run_entity_resolution.start")

    with SyncSession() as session:
        # Prevent concurrent ER runs: only one worker may hold the advisory lock.
        # pg_try_advisory_lock is session-level — released automatically on disconnect.
        acquired = session.execute(
            sa_text("SELECT pg_try_advisory_lock(:key)"), {"key": _ER_LOCK_KEY}
        ).scalar()
        if not acquired:
            log.info("run_entity_resolution.skipped_concurrent")
            return {"status": "skipped", "reason": "concurrent run in progress"}

        # Load watermark from last successful run
        last_run = session.execute(
            select(ERRunState)
            .where(ERRunState.status == "completed")
            .order_by(ERRunState.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        watermark = last_run.watermark_at if last_run else None

        # Create run record and persist independently so progress is visible
        er_run = ERRunState(status="running")
        session.add(er_run)
        session.flush()
        er_run_id = er_run.id
        session.commit()

        now = datetime.now(timezone.utc)
        _er_cols = (Entity.id, Entity.name, Entity.type, Entity.identifiers, Entity.attrs)

        base_filter = (
            or_(
                Entity.cluster_id.is_(None),
                Entity.updated_at > watermark,
                Entity.er_processed_at.is_(None),
            )
            if watermark
            else Entity.cluster_id.is_(None)
        )

        # Cross-batch identifier index: maps unique identifier value → cluster_id
        # so entities in different batches that share a CNPJ/CPF still get merged.
        cnpj_cluster: dict[str, object] = {}
        cpf_hash_cluster: dict[str, object] = {}

        total_entities = 0
        total_det = 0
        total_prob = 0
        total_clusters = 0
        last_id = None  # keyset pagination cursor

        # ── Phase 1: Batched entity matching ─────────────────────────────────
        while True:
            batch_stmt = (
                select(*_er_cols)
                .where(base_filter)
                .order_by(Entity.id)
                .limit(_ER_BATCH_SIZE)
            )
            if last_id is not None:
                batch_stmt = batch_stmt.where(Entity.id > last_id)

            batch = [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "identifiers": row["identifiers"],
                    "attrs": row["attrs"],
                }
                for row in session.execute(batch_stmt).mappings()
            ]
            if not batch:
                break

            last_id = batch[-1]["id"]
            total_entities += len(batch)
            log.info("er.batch_start", batch_size=len(batch), total_so_far=total_entities)

            # Pre-assign cluster_id for entities whose identifier was already seen
            pre_clustered: dict = {}
            for entity in batch:
                norm = normalize_entity_for_matching(
                    entity.get("name", ""), entity.get("identifiers") or {}
                )
                cid = (
                    cnpj_cluster.get(norm["cnpj"]) if norm["cnpj"]
                    else cpf_hash_cluster.get(norm["cpf_hash"]) if norm["cpf_hash"]
                    else None
                )
                if cid is not None:
                    pre_clustered[entity["id"]] = cid

            # Deterministic matching within batch
            matches = _build_deterministic_matches(batch)
            det_count = len(matches)
            total_det += det_count

            # Probabilistic matching within batch
            matched_ids: set = (
                {m.entity_a_id for m in matches} | {m.entity_b_id for m in matches}
            )
            if _should_run_probabilistic(len(batch)):
                matches.extend(_build_probabilistic_matches(batch, matched_ids))
            prob_count = len(matches) - det_count
            total_prob += prob_count

            # Cluster this batch (Union-Find)
            clusters = cluster_entities(matches)
            total_clusters += len(clusters)

            # Write cluster_ids — respecting cross-batch pre-assignments
            clustered_ids: set = set()
            for cluster in clusters:
                if not cluster.entity_ids:
                    continue
                clustered_ids.update(cluster.entity_ids)
                # If any member was pre-assigned, use that existing cluster_id
                assigned = next(
                    (pre_clustered[eid] for eid in cluster.entity_ids if eid in pre_clustered),
                    cluster.cluster_id,
                )
                session.execute(
                    update(Entity)
                    .where(Entity.id.in_(cluster.entity_ids))
                    .values(cluster_id=assigned)
                )

            # Pre-assigned entities not in any cluster → assign directly
            for eid, cid in pre_clustered.items():
                if eid not in clustered_ids:
                    session.execute(
                        update(Entity).where(Entity.id == eid).values(cluster_id=cid)
                    )

            # Stamp all processed entities in this batch
            batch_ids = [e["id"] for e in batch]
            for i in range(0, len(batch_ids), 500):
                session.execute(
                    update(Entity)
                    .where(Entity.id.in_(batch_ids[i : i + 500]))
                    .values(er_processed_at=now)
                )

            session.commit()

            # Update cross-batch identifier index from committed cluster_ids
            for row in session.execute(
                select(Entity.id, Entity.identifiers, Entity.cluster_id)
                .where(Entity.id.in_(batch_ids))
            ).mappings():
                if not row["cluster_id"]:
                    continue
                norm = normalize_entity_for_matching("", row["identifiers"] or {})
                if norm["cnpj"]:
                    cnpj_cluster[norm["cnpj"]] = row["cluster_id"]
                if norm["cpf_hash"]:
                    cpf_hash_cluster[norm["cpf_hash"]] = row["cluster_id"]

            log.info(
                "er.batch_done",
                batch_size=len(batch),
                det=det_count,
                prob=prob_count,
                clusters=len(clusters),
            )
            del batch, matches, clusters, batch_ids  # free memory before next batch

        log.info(
            "er.matching_complete",
            total_entities=total_entities,
            total_det=total_det,
            total_prob=total_prob,
            total_clusters=total_clusters,
        )

        if total_entities < 2:
            session.execute(
                update(ERRunState)
                .where(ERRunState.id == er_run_id)
                .values(status="skipped", watermark_at=now)
            )
            session.commit()
            return {"status": "skipped", "reason": "insufficient entities"}

        # ── Phase 2: Batched edge building ────────────────────────────────────
        # Pre-build occurred_at map for all events (UUID-only pass is cheap).
        event_id_set: set = set()
        for eid in session.execute(
            select(EventParticipant.event_id).execution_options(yield_per=50_000)
        ).scalars():
            event_id_set.add(eid)

        event_occurred_map: dict = {}
        event_ids_list = list(event_id_set)
        for i in range(0, len(event_ids_list), 10_000):
            chunk = event_ids_list[i : i + 10_000]
            for event_id, occurred_at in session.execute(
                select(Event.id, Event.occurred_at).where(Event.id.in_(chunk))
            ).all():
                event_occurred_map[event_id] = occurred_at
        del event_ids_list

        edges_created = 0
        _part_cols = (
            EventParticipant.event_id,
            EventParticipant.entity_id,
            EventParticipant.role,
            EventParticipant.attrs,
        )
        part_batch: list = []

        def _flush_edges(part_batch: list) -> int:
            """Build and upsert graph edges from one participant batch."""
            if not part_batch:
                return 0
            structural_edges = build_structural_edges(part_batch)
            if not structural_edges:
                return 0

            entity_ids_in_edges: set = set()
            for edge in structural_edges:
                entity_ids_in_edges.add(edge.from_entity_id)
                entity_ids_in_edges.add(edge.to_entity_id)

            entity_ids_list = list(entity_ids_in_edges)
            existing_nodes: dict = {}
            for _i in range(0, len(entity_ids_list), _IN_CHUNK):
                _chunk = entity_ids_list[_i : _i + _IN_CHUNK]
                for node in session.execute(
                    select(GraphNode).where(GraphNode.entity_id.in_(_chunk))
                ).scalars().all():
                    existing_nodes[node.entity_id] = node
            entity_map: dict = {}
            for _i in range(0, len(entity_ids_list), _IN_CHUNK):
                _chunk = entity_ids_list[_i : _i + _IN_CHUNK]
                for e in session.execute(
                    select(Entity).where(Entity.id.in_(_chunk))
                ).scalars().all():
                    entity_map[e.id] = e

            node_by_entity_id: dict = {}
            for entity_id in entity_ids_in_edges:
                entity = entity_map.get(entity_id)
                if entity is None:
                    continue
                snapshot = _node_attrs_snapshot(
                    {"identifiers": entity.identifiers or {}, "attrs": entity.attrs or {}}
                )
                node = existing_nodes.get(entity_id)
                if node is None:
                    node = GraphNode(
                        entity_id=entity_id,
                        label=entity.name,
                        node_type=entity.type,
                        attrs=snapshot,
                    )
                    session.add(node)
                else:
                    node.label = entity.name
                    node.node_type = entity.type
                    node.attrs = snapshot
                node_by_entity_id[entity_id] = node
            session.flush()

            edge_payloads: dict[tuple, dict] = {}
            for edge in structural_edges:
                from_node = node_by_entity_id.get(edge.from_entity_id)
                to_node = node_by_entity_id.get(edge.to_entity_id)
                if from_node is None or to_node is None:
                    continue
                key = (from_node.id, to_node.id, edge.edge_type)
                payload = edge_payloads.setdefault(
                    key,
                    {
                        "weight": 0.0,
                        "edge_strength": "weak",
                        "verification_method": "co_occurrence",
                        "verification_confidence": 0.2,
                        "attrs": {
                            "event_ids": [],
                            "role_pairs_count": {},
                            "first_seen_at": None,
                            "last_seen_at": None,
                            "source_role": edge.source_role,
                            "target_role": edge.target_role,
                            "edge_label": edge.edge_label,
                        },
                    },
                )
                payload["weight"] += float(edge.weight or 0.0)
                edge_type_lower = (edge.edge_type or "").lower()
                if (
                    "fornecimento" in edge_type_lower
                    or "favorecido" in edge_type_lower
                    or edge.weight >= 2.0
                ):
                    payload["edge_strength"] = "strong"
                    payload["verification_method"] = "documented_event"
                payload["verification_confidence"] = min(
                    0.99,
                    max(
                        payload["verification_confidence"],
                        max(0.2, float(edge.weight or 0.0) / 4),
                    ),
                )
                attrs = payload["attrs"]
                attrs["event_ids"].append(str(edge.event_id))
                rk = f"{edge.source_role}__{edge.target_role}"
                attrs["role_pairs_count"][rk] = attrs["role_pairs_count"].get(rk, 0) + 1
                if edge.occurred_at is not None:
                    occ_iso = edge.occurred_at.isoformat()
                    first_seen = _parse_iso_dt(attrs.get("first_seen_at"))
                    last_seen = _parse_iso_dt(attrs.get("last_seen_at"))
                    if first_seen is None or edge.occurred_at < first_seen:
                        attrs["first_seen_at"] = occ_iso
                    if last_seen is None or edge.occurred_at > last_seen:
                        attrs["last_seen_at"] = occ_iso

            if not edge_payloads:
                return 0

            from_ids = list({k[0] for k in edge_payloads})
            to_ids = list({k[1] for k in edge_payloads})
            edge_types = list({k[2] for k in edge_payloads})
            existing_edges: dict = {}
            for _i in range(0, len(from_ids), _IN_CHUNK):
                _from_chunk = from_ids[_i : _i + _IN_CHUNK]
                for e in session.execute(
                    select(GraphEdge).where(
                        GraphEdge.from_node_id.in_(_from_chunk),
                        GraphEdge.to_node_id.in_(to_ids),
                        GraphEdge.type.in_(edge_types),
                    )
                ).scalars().all():
                    existing_edges[(e.from_node_id, e.to_node_id, e.type)] = e

            created = 0
            for key, payload in edge_payloads.items():
                existing_edge = existing_edges.get(key)
                incoming_attrs = payload["attrs"]
                incoming_attrs["event_ids"] = list(dict.fromkeys(incoming_attrs["event_ids"]))
                if existing_edge is None:
                    session.add(
                        GraphEdge(
                            from_node_id=key[0],
                            to_node_id=key[1],
                            type=key[2],
                            weight=payload["weight"],
                            edge_strength=payload["edge_strength"],
                            verification_method=payload["verification_method"],
                            verification_confidence=payload["verification_confidence"],
                            attrs=incoming_attrs,
                        )
                    )
                    created += 1
                else:
                    existing_edge.weight = float(existing_edge.weight or 0.0) + payload["weight"]
                    if payload["edge_strength"] == "strong":
                        existing_edge.edge_strength = "strong"
                    existing_edge.verification_method = payload["verification_method"]
                    existing_edge.verification_confidence = max(
                        float(existing_edge.verification_confidence or 0.0),
                        payload["verification_confidence"],
                    )
                    existing_edge.attrs = _merge_edge_attrs(
                        existing_edge.attrs or {}, incoming_attrs
                    )
            session.commit()
            return created

        for row in session.execute(
            select(*_part_cols).execution_options(yield_per=_ER_EDGE_BATCH_SIZE)
        ).mappings():
            part_batch.append(
                {
                    "event_id": row["event_id"],
                    "entity_id": row["entity_id"],
                    "role": row["role"],
                    "value_brl": (row["attrs"] or {}).get("value_brl"),
                    "occurred_at": event_occurred_map.get(row["event_id"]),
                }
            )
            if len(part_batch) >= _ER_EDGE_BATCH_SIZE:
                edges_created += _flush_edges(part_batch)
                log.info("er.edge_batch_done", total_edges=edges_created)
                part_batch = []

        if part_batch:
            edges_created += _flush_edges(part_batch)
        log.info("er.structural_edges", count=edges_created)

        # ── Phase 3: Finalize run record ──────────────────────────────────────
        session.execute(
            update(ERRunState)
            .where(ERRunState.id == er_run_id)
            .values(
                status="completed",
                entities_processed=total_entities,
                deterministic_matches=total_det,
                probabilistic_matches=total_prob,
                clusters_formed=total_clusters,
                edges_created=edges_created,
                watermark_at=now,
            )
        )
        session.commit()

    result = {
        "status": "completed",
        "entities_processed": total_entities,
        "deterministic_matches": total_det,
        "probabilistic_matches": total_prob,
        "semantic_matches": 0,
        "clusters_formed": total_clusters,
        "edges_created": edges_created,
        "incremental": watermark is not None,
    }
    log.info("run_entity_resolution.done", **result)
    return result
