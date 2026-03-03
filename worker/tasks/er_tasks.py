from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations

from celery import shared_task

from shared.logging import log

_PROBABILISTIC_THRESHOLD = 0.85
_PROBABILISTIC_MAX_BUCKET_SIZE = 300
_PROBABILISTIC_MAX_ENTITIES = 5000

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


@shared_task(name="worker.tasks.er_tasks.run_entity_resolution")
def run_entity_resolution():
    """Run incremental entity resolution pipeline.

    Uses watermark from previous run to only process new/changed entities.
    Falls back to full scan for entities without cluster_id.

    1. Load entities needing resolution (new since watermark OR no cluster_id).
    2. Phase 1 — Deterministic: match on CNPJ/CPF hash (exact).
    3. Phase 2 — Probabilistic: Jaro-Winkler on names + secondary signals.
    4. Phase 3 — Clustering: Union-Find to group matched entities.
    5. Phase 4 — Edges: Build structural graph edges from event-participant rels.
    6. Store cluster_id on entities (non-destructive).
    7. Update watermark for next run.
    """
    from sqlalchemy import or_, select, update

    from shared.db_sync import SyncSession
    from shared.er.clustering import cluster_entities
    from shared.er.edges import build_structural_edges
    from shared.models.orm import Entity, ERRunState, Event, EventParticipant, GraphEdge, GraphNode

    log.info("run_entity_resolution.start")

    with SyncSession() as session:
        # Load last successful ER watermark
        watermark_stmt = (
            select(ERRunState)
            .where(ERRunState.status == "completed")
            .order_by(ERRunState.created_at.desc())
            .limit(1)
        )
        last_run = session.execute(watermark_stmt).scalar_one_or_none()
        watermark = last_run.watermark_at if last_run else None

        # Create new ER run record
        er_run = ERRunState(status="running")
        session.add(er_run)
        session.flush()

        # Incremental: entities updated since watermark OR still without cluster_id
        if watermark:
            stmt = select(Entity).where(
                or_(
                    Entity.cluster_id.is_(None),
                    Entity.updated_at > watermark,
                    Entity.er_processed_at.is_(None),
                )
            )
        else:
            # First run: process all entities without cluster_id
            stmt = select(Entity).where(Entity.cluster_id.is_(None))

        entities_orm = session.execute(stmt).scalars().all()

        log.info("er.entities_loaded", count=len(entities_orm))

        if len(entities_orm) < 2:
            log.info("er.skip", reason="fewer than 2 unresolved entities")
            er_run.status = "skipped"
            er_run.watermark_at = datetime.now(timezone.utc)
            session.commit()
            return {"status": "skipped", "reason": "insufficient entities"}

        # Convert to dicts for matching functions
        entities = [
            {
                "id": e.id,
                "name": e.name,
                "type": e.type,
                "identifiers": e.identifiers,
                "attrs": e.attrs,
            }
            for e in entities_orm
        ]

        # 2. Deterministic matching (CNPJ/CPF)
        matches = _build_deterministic_matches(entities)

        det_count = len(matches)
        log.info("er.deterministic_done", matches=det_count)

        # 3. Probabilistic matching (Jaro-Winkler on names within same type)
        # Only run on entities NOT already matched deterministically
        matched_ids = set()
        for m in matches:
            matched_ids.add(m.entity_a_id)
            matched_ids.add(m.entity_b_id)

        if _should_run_probabilistic(len(entities)):
            matches.extend(_build_probabilistic_matches(entities, matched_ids))
        else:
            log.warning(
                "er.probabilistic_skipped_large_dataset",
                entity_count=len(entities),
                limit=_PROBABILISTIC_MAX_ENTITIES,
            )

        prob_count = len(matches) - det_count
        log.info("er.probabilistic_done", matches=prob_count)

        # 4. Clustering (Union-Find)
        clusters = cluster_entities(matches)
        log.info("er.clusters_formed", count=len(clusters))

        # 5. Update cluster_id on entities (bulk: one UPDATE per cluster)
        for cluster in clusters:
            if cluster.entity_ids:
                session.execute(
                    update(Entity)
                    .where(Entity.id.in_(cluster.entity_ids))
                    .values(cluster_id=cluster.cluster_id)
                )

        # Mark processed entities with timestamp
        now = datetime.now(timezone.utc)
        processed_ids = [e["id"] for e in entities]
        _STAMP_BATCH = 500
        for i in range(0, len(processed_ids), _STAMP_BATCH):
            batch_ids = processed_ids[i : i + _STAMP_BATCH]
            session.execute(
                update(Entity)
                .where(Entity.id.in_(batch_ids))
                .values(er_processed_at=now)
            )

        # 6. Build structural edges from event-participant relationships
        # Limit to participants of entities we just processed to avoid full scan.
        if processed_ids:
            part_stmt = select(EventParticipant).where(
                EventParticipant.entity_id.in_(processed_ids)
            )
        else:
            part_stmt = select(EventParticipant)
        participants_orm = session.execute(part_stmt).scalars().all()

        event_ids = sorted({p.event_id for p in participants_orm}, key=lambda eid: str(eid))
        event_occurred_map: dict = {}
        if event_ids:
            event_stmt = select(Event.id, Event.occurred_at).where(Event.id.in_(event_ids))
            for event_id, occurred_at in session.execute(event_stmt).all():
                event_occurred_map[event_id] = occurred_at

        participant_dicts = []
        for participant in participants_orm:
            participant_dicts.append(
                {
                    "event_id": participant.event_id,
                    "entity_id": participant.entity_id,
                    "role": participant.role,
                    "value_brl": (participant.attrs or {}).get("value_brl"),
                    "occurred_at": event_occurred_map.get(participant.event_id),
                }
            )

        structural_edges = build_structural_edges(participant_dicts)
        log.info("er.structural_edges", count=len(structural_edges))

        # 7. Upsert GraphNode + GraphEdge with explainable attrs
        entity_ids_in_edges = set()
        for edge in structural_edges:
            entity_ids_in_edges.add(edge.from_entity_id)
            entity_ids_in_edges.add(edge.to_entity_id)

        existing_nodes: dict = {}
        if entity_ids_in_edges:
            node_stmt = select(GraphNode).where(GraphNode.entity_id.in_(entity_ids_in_edges))
            for node in session.execute(node_stmt).scalars().all():
                existing_nodes[node.entity_id] = node

        if entity_ids_in_edges:
            entity_stmt = select(Entity).where(Entity.id.in_(entity_ids_in_edges))
            entity_map = {entity.id: entity for entity in session.execute(entity_stmt).scalars().all()}
        else:
            entity_map = {}

        node_by_entity_id: dict = {}
        for entity_id in entity_ids_in_edges:
            entity = entity_map.get(entity_id)
            if entity is None:
                continue
            snapshot = _node_attrs_snapshot(
                {
                    "identifiers": entity.identifiers or {},
                    "attrs": entity.attrs or {},
                }
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
            is_strong = (
                "fornecimento" in edge_type_lower
                or "favorecido" in edge_type_lower
                or edge.weight >= 2.0
            )
            if is_strong:
                payload["edge_strength"] = "strong"
                payload["verification_method"] = "documented_event"
            payload["verification_confidence"] = min(
                0.99,
                max(payload["verification_confidence"], max(0.2, float(edge.weight or 0.0) / 4)),
            )

            attrs = payload["attrs"]
            attrs["event_ids"].append(str(edge.event_id))
            role_pair_key = f"{edge.source_role}__{edge.target_role}"
            attrs["role_pairs_count"][role_pair_key] = attrs["role_pairs_count"].get(role_pair_key, 0) + 1

            if edge.occurred_at is not None:
                occurred_iso = edge.occurred_at.isoformat()
                first_seen = _parse_iso_dt(attrs.get("first_seen_at"))
                last_seen = _parse_iso_dt(attrs.get("last_seen_at"))
                if first_seen is None or edge.occurred_at < first_seen:
                    attrs["first_seen_at"] = occurred_iso
                if last_seen is None or edge.occurred_at > last_seen:
                    attrs["last_seen_at"] = occurred_iso

        existing_edges = {}
        if edge_payloads:
            from_ids = {key[0] for key in edge_payloads}
            to_ids = {key[1] for key in edge_payloads}
            edge_types = {key[2] for key in edge_payloads}
            existing_stmt = select(GraphEdge).where(
                GraphEdge.from_node_id.in_(from_ids),
                GraphEdge.to_node_id.in_(to_ids),
                GraphEdge.type.in_(edge_types),
            )
            for existing_edge in session.execute(existing_stmt).scalars().all():
                existing_edges[(existing_edge.from_node_id, existing_edge.to_node_id, existing_edge.type)] = existing_edge

        edges_created = 0
        for key, payload in edge_payloads.items():
            existing_edge = existing_edges.get(key)
            incoming_attrs = payload["attrs"]
            incoming_attrs["event_ids"] = list(dict.fromkeys(incoming_attrs["event_ids"]))
            if existing_edge is None:
                new_edge = GraphEdge(
                    from_node_id=key[0],
                    to_node_id=key[1],
                    type=key[2],
                    weight=payload["weight"],
                    edge_strength=payload["edge_strength"],
                    verification_method=payload["verification_method"],
                    verification_confidence=payload["verification_confidence"],
                    attrs=incoming_attrs,
                )
                session.add(new_edge)
                edges_created += 1
            else:
                existing_edge.weight = float(existing_edge.weight or 0.0) + payload["weight"]
                if payload["edge_strength"] == "strong":
                    existing_edge.edge_strength = "strong"
                existing_edge.verification_method = payload["verification_method"]
                existing_edge.verification_confidence = max(
                    float(existing_edge.verification_confidence or 0.0),
                    payload["verification_confidence"],
                )
                existing_edge.attrs = _merge_edge_attrs(existing_edge.attrs or {}, incoming_attrs)

        # Update ER run state with watermark
        er_run.status = "completed"
        er_run.entities_processed = len(entities)
        er_run.deterministic_matches = det_count
        er_run.probabilistic_matches = prob_count
        er_run.clusters_formed = len(clusters)
        er_run.edges_created = edges_created
        er_run.watermark_at = now

        session.commit()

    result = {
        "status": "completed",
        "entities_processed": len(entities),
        "deterministic_matches": det_count,
        "probabilistic_matches": prob_count,
        "clusters_formed": len(clusters),
        "edges_created": edges_created,
        "incremental": watermark is not None,
    }
    log.info("run_entity_resolution.done", **result)
    return result
