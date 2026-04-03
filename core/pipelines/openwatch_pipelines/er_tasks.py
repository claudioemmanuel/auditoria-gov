import uuid as _uuid_mod
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

from celery import shared_task

from openwatch_utils.logging import log

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
    from openwatch_er.matching import deterministic_match
    from openwatch_er.normalize import normalize_entity_for_matching

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
    from openwatch_er.matching import probabilistic_match
    from openwatch_er.normalize import normalize_entity_for_matching

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


def _collect_cluster_evidence(
    matches: list,
    clusters: list,
    entity_lookup: dict,
) -> tuple[list[dict], dict]:
    """Compute pairwise ER confidence for every cluster; pure function — no DB access.

    Args:
        matches: list[MatchResult] from deterministic + probabilistic passes.
        clusters: list[Cluster] from cluster_entities().
        entity_lookup: dict mapping entity_id → entity dict (with identifiers/attrs).

    Returns:
        pair_evidence: list of dicts suitable for ERMergeEvidence(**ev) insertion.
        entity_confidence: maps entity_id → cluster_confidence (int 0-100).
            All entities in the same cluster share the same value (weakest-link min).
            Entity not in any evidenced cluster → absent from the dict.

    Precondition: identifiers in entity dicts must be digits-only (post-normalization).
    """
    from openwatch_er.confidence import compute_cluster_confidence, compute_pair_confidence

    match_by_pair: dict = {
        frozenset((m.entity_a_id, m.entity_b_id)): m for m in matches
    }

    pair_evidence: list[dict] = []
    entity_confidence: dict = {}

    for cluster in clusters:
        if len(cluster.entity_ids) < 2:
            continue

        pair_scores: list[int] = []
        for pair, match in match_by_pair.items():
            if not pair.issubset(cluster.entity_ids):
                continue
            ea = entity_lookup.get(match.entity_a_id)
            eb = entity_lookup.get(match.entity_b_id)
            if not ea or not eb:
                continue

            attrs_a = ea.get("attrs") or {}
            attrs_b = eb.get("attrs") or {}
            mun_a = attrs_a.get("municipio")
            mun_b = attrs_b.get("municipio")
            same_municipality = bool(mun_a and mun_a == mun_b)

            score, ev_type = compute_pair_confidence(
                identifiers_a=ea.get("identifiers") or {},
                identifiers_b=eb.get("identifiers") or {},
                name_similarity=match.score,
                same_municipality=same_municipality,
                co_participation_count=0,
            )
            if score is not None:
                pair_scores.append(score)
                pair_evidence.append({
                    "entity_a_id": match.entity_a_id,
                    "entity_b_id": match.entity_b_id,
                    "confidence_score": score,
                    "evidence_type": ev_type.value,
                    "evidence_detail": {
                        "match_type": match.match_type,
                        "match_score": round(match.score, 4),
                    },
                })

        if pair_scores:
            cluster_conf = compute_cluster_confidence(pair_scores)
            for eid in cluster.entity_ids:
                entity_confidence[eid] = cluster_conf

    return pair_evidence, entity_confidence


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

    from openwatch_er.matching import MatchResult
    from openwatch_queries.queries import get_entity_embeddings_for_er

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


@shared_task(
    name="openwatch_pipelines.er_tasks.run_entity_resolution",
    soft_time_limit=7200,   # 2h soft (large entity sets + edge building)
    time_limit=7500,        # 2h 5min hard kill
)
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

    from openwatch_db.db_sync import SyncSession
    from openwatch_er.clustering import cluster_entities
    from openwatch_er.edges import build_structural_edges
    from openwatch_er.normalize import normalize_entity_for_matching
    from openwatch_models.orm import Entity, ERMergeEvidence, ERRunState, Event, EventParticipant, GraphEdge, GraphNode

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

        # Incremental filter: only process entities not yet handled by ER.
        # New entities from ingest/normalize have er_processed_at=NULL.
        # After ER processes them, it stamps er_processed_at=now, so
        # subsequent runs skip them unless they are re-created.
        # NOTE: Do NOT use updated_at — it has onupdate=func.now(), so the
        # ER batch UPDATE itself bumps updated_at, causing full re-scans.
        # NOTE: Do NOT use cluster_id IS NULL — most entities have no
        # matches and will never get a cluster_id.
        base_filter = Entity.er_processed_at.is_(None)

        # Cross-batch identifier index: maps unique identifier value → cluster_id
        # so entities in different batches that share a CNPJ/CPF still get merged.
        cnpj_cluster: dict[str, object] = {}
        cpf_hash_cluster: dict[str, object] = {}

        total_entities = 0
        total_det = 0
        total_prob = 0
        total_clusters = 0
        last_id = None  # keyset pagination cursor
        all_entities_for_semantic: list[dict] = []
        all_matched_ids_for_semantic: set = set()

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

            # Accumulate entities/matched_ids for semantic pass (capped at limit)
            if len(all_entities_for_semantic) < _SEMANTIC_MAX_UNMATCHED:
                all_entities_for_semantic.extend(batch)
            all_matched_ids_for_semantic |= (
                {m.entity_a_id for m in matches} | {m.entity_b_id for m in matches}
            )

            # Cluster this batch (Union-Find)
            clusters = cluster_entities(matches)
            total_clusters += len(clusters)

            # Compute pairwise confidence evidence for all clusters (pure, no DB)
            entity_lookup = {e["id"]: e for e in batch}
            pair_evidence, entity_confidence = _collect_cluster_evidence(
                matches, clusters, entity_lookup
            )

            # Persist ERMergeEvidence records
            for ev in pair_evidence:
                session.add(ERMergeEvidence(**ev))

            # Write cluster_ids + cluster_confidence — respecting cross-batch pre-assignments
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
                # cluster_confidence: min pairwise score for this cluster (None if no evidence)
                conf = entity_confidence.get(next(iter(cluster.entity_ids)))
                session.execute(
                    update(Entity)
                    .where(Entity.id.in_(cluster.entity_ids))
                    .values(cluster_id=assigned, cluster_confidence=conf)
                )

            # Pre-assigned entities not in any cluster → deterministic cross-batch match
            # (CNPJ/CPF exact via identifier index) → confidence = 100
            for eid, cid in pre_clustered.items():
                if eid not in clustered_ids:
                    session.execute(
                        update(Entity)
                        .where(Entity.id == eid)
                        .values(cluster_id=cid, cluster_confidence=100)
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
                cnpj_index_size=len(cnpj_cluster),
                cpf_index_size=len(cpf_hash_cluster),
                semantic_candidates=len(all_entities_for_semantic),
                semantic_matched=len(all_matched_ids_for_semantic),
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

        # ── Semantic ER pass (requires embeddings + active LLM provider) ──────
        from openwatch_config.settings import settings

        total_sem = 0
        if getattr(settings, "LLM_PROVIDER", "none") not in ("none", "", None):
            sem_matches = _build_semantic_matches(
                session, all_entities_for_semantic, all_matched_ids_for_semantic
            )
            total_sem = len(sem_matches)
            log.info("er.semantic_matches", count=total_sem)

            # Apply semantic clusters: write cluster_id for entities not yet merged
            # by the deterministic/probabilistic passes (those take precedence).
            if total_sem > 0:
                sem_clusters = cluster_entities(sem_matches)
                sem_applied = 0
                for cluster in sem_clusters:
                    if not cluster.entity_ids:
                        continue
                    session.execute(
                        update(Entity)
                        .where(
                            Entity.id.in_(cluster.entity_ids),
                            Entity.cluster_id.is_(None),
                        )
                        .values(cluster_id=cluster.cluster_id)
                    )
                    sem_applied += 1
                if sem_applied:
                    session.commit()
                    total_clusters += sem_applied
                    log.info("er.semantic_clusters_applied", count=sem_applied)

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
            # Chunk BOTH from_ids and to_ids to avoid O(from × to) DB planner explosion
            for _i in range(0, len(from_ids), _IN_CHUNK):
                _from_chunk = from_ids[_i : _i + _IN_CHUNK]
                for _j in range(0, len(to_ids), _IN_CHUNK):
                    _to_chunk = to_ids[_j : _j + _IN_CHUNK]
                    for e in session.execute(
                        select(GraphEdge).where(
                            GraphEdge.from_node_id.in_(_from_chunk),
                            GraphEdge.to_node_id.in_(_to_chunk),
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

        # Use a dedicated read session for participant streaming so that
        # session.commit() calls inside _flush_edges don't invalidate the
        # server-side cursor created by yield_per on the write session.
        with SyncSession() as read_session:
            for row in read_session.execute(
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
                    _batch_edges = _flush_edges(part_batch)
                    edges_created += _batch_edges
                    if _batch_edges > 0:
                        log.info("er.edge_batch_done", batch_edges=_batch_edges, total_edges=edges_created)
                    part_batch = []

        if part_batch:
            edges_created += _flush_edges(part_batch)
        log.info("er.structural_edges", count=edges_created)

        # ── Phase 2b: Corporate relationship edges (Receita CNPJ) ─────────────
        # Builds SAME_ADDRESS, SHARES_PHONE, SAME_SOCIO, SAME_ACCOUNTANT,
        # SUBSIDIARY, and HOLDING edges from entity attrs populated by the
        # receita_cnpj connector.  These edge types are required by T13 and T17.
        from openwatch_er.corporate_edges import build_corporate_edges

        corp_edges = build_corporate_edges(session)
        corp_edges_created = 0

        if corp_edges:
            # Collect all entity IDs referenced by corporate edges
            corp_entity_ids: set = set()
            for ce in corp_edges:
                corp_entity_ids.add(ce.from_entity_id)
                corp_entity_ids.add(ce.to_entity_id)

            corp_entity_list = list(corp_entity_ids)

            # Load / create GraphNodes for all referenced entities
            corp_existing_nodes: dict = {}
            for _ci in range(0, len(corp_entity_list), _IN_CHUNK):
                _cc = corp_entity_list[_ci : _ci + _IN_CHUNK]
                for n in session.execute(
                    select(GraphNode).where(GraphNode.entity_id.in_(_cc))
                ).scalars().all():
                    corp_existing_nodes[n.entity_id] = n

            corp_entity_map: dict = {}
            for _ci in range(0, len(corp_entity_list), _IN_CHUNK):
                _cc = corp_entity_list[_ci : _ci + _IN_CHUNK]
                for e in session.execute(
                    select(Entity).where(Entity.id.in_(_cc))
                ).scalars().all():
                    corp_entity_map[e.id] = e

            corp_node_by_entity: dict = {}
            for eid in corp_entity_ids:
                entity = corp_entity_map.get(eid)
                if entity is None:
                    continue
                node = corp_existing_nodes.get(eid)
                if node is None:
                    snapshot = _node_attrs_snapshot(
                        {"identifiers": entity.identifiers or {}, "attrs": entity.attrs or {}}
                    )
                    node = GraphNode(
                        entity_id=eid,
                        label=entity.name,
                        node_type=entity.type,
                        attrs=snapshot,
                    )
                    session.add(node)
                corp_node_by_entity[eid] = node
            session.flush()

            # Upsert corporate edges
            corp_from_ids = list({corp_node_by_entity[ce.from_entity_id].id for ce in corp_edges if ce.from_entity_id in corp_node_by_entity})
            corp_to_ids = list({corp_node_by_entity[ce.to_entity_id].id for ce in corp_edges if ce.to_entity_id in corp_node_by_entity})
            corp_edge_types = list({ce.edge_type for ce in corp_edges})

            corp_existing_edges: dict = {}
            # Chunk both dimensions to avoid O(from × to) planner explosion
            for _ci in range(0, len(corp_from_ids), _IN_CHUNK):
                _cf = corp_from_ids[_ci : _ci + _IN_CHUNK]
                for _cj in range(0, len(corp_to_ids), _IN_CHUNK):
                    _ct = corp_to_ids[_cj : _cj + _IN_CHUNK]
                    for ge in session.execute(
                        select(GraphEdge).where(
                            GraphEdge.from_node_id.in_(_cf),
                            GraphEdge.to_node_id.in_(_ct),
                            GraphEdge.type.in_(corp_edge_types),
                        )
                    ).scalars().all():
                        corp_existing_edges[(ge.from_node_id, ge.to_node_id, ge.type)] = ge

            for ce in corp_edges:
                from_node = corp_node_by_entity.get(ce.from_entity_id)
                to_node = corp_node_by_entity.get(ce.to_entity_id)
                if from_node is None or to_node is None:
                    continue
                key = (from_node.id, to_node.id, ce.edge_type)
                existing = corp_existing_edges.get(key)
                if existing is None:
                    session.add(GraphEdge(
                        from_node_id=from_node.id,
                        to_node_id=to_node.id,
                        type=ce.edge_type,
                        weight=ce.weight,
                        edge_strength="strong" if ce.verification_confidence >= 0.80 else "weak",
                        verification_method=ce.verification_method,
                        verification_confidence=ce.verification_confidence,
                        attrs=ce.attrs,
                    ))
                    corp_edges_created += 1
                else:
                    existing.weight = max(float(existing.weight or 0.0), ce.weight)
                    existing.verification_confidence = max(
                        float(existing.verification_confidence or 0.0),
                        ce.verification_confidence,
                    )
            session.commit()

        edges_created += corp_edges_created
        log.info("er.corporate_edges", count=corp_edges_created)

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
        "semantic_matches": total_sem,
        "clusters_formed": total_clusters,
        "edges_created": edges_created,
        "incremental": watermark is not None,
    }
    log.info("run_entity_resolution.done", **result)

    # ── Reactive pipeline: trigger baselines after ER completes ────
    try:
        from openwatch_pipelines.baseline_tasks import compute_all_baselines

        compute_all_baselines.apply_async(queue="default", countdown=10)
        log.info("run_entity_resolution.triggered_baselines", countdown=10)
    except Exception as exc:
        log.warning("run_entity_resolution.trigger_baselines_error", error=str(exc))

    return result
