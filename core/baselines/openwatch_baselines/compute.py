import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from openwatch_baselines.models import BaselineMetrics, BaselineType, MIN_SAMPLE_SIZE
from openwatch_utils.logging import log
from openwatch_models.orm import BaselineSnapshot, Event, EventParticipant
from openwatch_utils.query import execute_chunked_in

# Sentinel values indicating missing/unknown CATMAT group — excluded from baselines.
# Includes both ASCII-normalised and accented Portuguese variants so all callers
# (T01, T07, T12, baselines) reject the same set without local divergence.
_CATMAT_MISSING = {
    "",
    "nao_informado",
    "não informado",
    "nao informado",
    "sem classificacao",
    "sem classificação",
    "null",
    "none",
    "unknown",
    "nao_classificado",
    "não classificado",
}


def _percentile(sorted_data: list[float], pct: float) -> float:
    """Compute percentile from sorted data."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (pct / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])


def compute_metrics(
    values: list[float], baseline_type: BaselineType, scope_key: str
) -> BaselineMetrics | None:
    """Compute percentile metrics from a list of values.

    Returns None if sample size < MIN_SAMPLE_SIZE.
    """
    if len(values) < MIN_SAMPLE_SIZE:
        return None

    sorted_vals = sorted(values)
    return BaselineMetrics(
        baseline_type=baseline_type,
        scope_key=scope_key,
        sample_size=len(sorted_vals),
        mean=statistics.mean(sorted_vals),
        median=statistics.median(sorted_vals),
        std=statistics.stdev(sorted_vals) if len(sorted_vals) > 1 else 0.0,
        p5=_percentile(sorted_vals, 5),
        p10=_percentile(sorted_vals, 10),
        p25=_percentile(sorted_vals, 25),
        p75=_percentile(sorted_vals, 75),
        p90=_percentile(sorted_vals, 90),
        p95=_percentile(sorted_vals, 95),
        p99=_percentile(sorted_vals, 99),
        min=sorted_vals[0],
        max=sorted_vals[-1],
    )


# Scope broadening hierarchy for CATMAT-based grouping.
_SCOPE_HIERARCHY = ["catmat_group", "catmat_class", "modality", "national"]


def _broaden_scope(scope_key: str) -> str | None:
    """Return the next broader scope key, or None if already at national."""
    parts = scope_key.split("::")
    if len(parts) < 2:
        return None
    current_level = parts[0]
    try:
        idx = _SCOPE_HIERARCHY.index(current_level)
    except ValueError:
        return None
    if idx + 1 >= len(_SCOPE_HIERARCHY):
        return None
    return f"{_SCOPE_HIERARCHY[idx + 1]}::all"


async def _compute_price_baselines(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[BaselineMetrics]:
    """Compute PRICE_BY_ITEM baselines grouped by catmat_group."""
    stmt = (
        select(Event)
        .where(
            Event.type.in_(["licitacao", "contrato"]),
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
            Event.value_brl.isnot(None),
            Event.value_brl > 0,
        )
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    # Group by catmat_group
    groups: dict[str, list[float]] = defaultdict(list)
    for e in events:
        catmat = e.attrs.get("catmat_group") or e.attrs.get("catmat_code")
        if not catmat or str(catmat).strip().lower() in _CATMAT_MISSING:
            continue  # No meaningful group — exclude from baselines
        groups[f"catmat_group::{catmat}"].append(e.value_brl)

    results: list[BaselineMetrics] = []
    all_values: list[float] = []
    for scope_key, values in groups.items():
        all_values.extend(values)
        metrics = compute_metrics(values, BaselineType.PRICE_BY_ITEM, scope_key)
        if metrics is not None:
            results.append(metrics)

    # National fallback for groups that didn't meet MIN_SAMPLE_SIZE
    if all_values:
        national = compute_metrics(
            all_values, BaselineType.PRICE_BY_ITEM, "national::all"
        )
        if national is not None:
            results.append(national)

    return results


async def _compute_participants_baselines(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[BaselineMetrics]:
    """Compute PARTICIPANTS_PER_PROCUREMENT baselines."""
    stmt = (
        select(Event)
        .where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    event_ids = [e.id for e in events]
    if not event_ids:
        return []

    # Count participants per event (chunked to avoid asyncpg 32K param limit)
    participants = await execute_chunked_in(
        session,
        lambda batch: select(EventParticipant).where(
            EventParticipant.event_id.in_(batch),
            EventParticipant.role == "bidder",
        ),
        event_ids,
    )

    counts: dict[str, int] = defaultdict(int)
    event_modality: dict[str, str] = {}
    for e in events:
        counts[str(e.id)] = 0
        event_modality[str(e.id)] = e.attrs.get("modality", "nao_informado")
    for p in participants:
        counts[str(p.event_id)] += 1

    # Group by modality
    modality_groups: dict[str, list[float]] = defaultdict(list)
    for eid, count in counts.items():
        mod = event_modality.get(eid, "nao_informado")
        modality_groups[f"modality::{mod}"].append(float(count))

    results: list[BaselineMetrics] = []
    all_counts: list[float] = []
    for scope_key, values in modality_groups.items():
        all_counts.extend(values)
        metrics = compute_metrics(
            values, BaselineType.PARTICIPANTS_PER_PROCUREMENT, scope_key
        )
        if metrics is not None:
            results.append(metrics)

    # National fallback
    if all_counts:
        national = compute_metrics(
            all_counts, BaselineType.PARTICIPANTS_PER_PROCUREMENT, "national::all"
        )
        if national is not None:
            results.append(national)

    return results


async def _compute_hhi_baselines(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[BaselineMetrics]:
    """Compute HHI_DISTRIBUTION baselines."""
    stmt = (
        select(Event)
        .where(
            Event.type == "licitacao",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
            Event.value_brl.isnot(None),
            Event.value_brl > 0,
        )
    )
    result = await session.execute(stmt)
    events = result.scalars().all()

    event_ids = [e.id for e in events]
    if not event_ids:
        return []

    # Get winners (chunked to avoid asyncpg 32K param limit)
    winners = await execute_chunked_in(
        session,
        lambda batch: select(EventParticipant).where(
            EventParticipant.event_id.in_(batch),
            EventParticipant.role == "winner",
        ),
        event_ids,
    )

    # Map event -> (catmat_group, procuring_entity, value)
    event_info: dict[str, dict] = {}
    for e in events:
        catmat_raw = e.attrs.get("catmat_group") or ""
        event_info[str(e.id)] = {
            "catmat_group": catmat_raw if catmat_raw.strip().lower() not in _CATMAT_MISSING else None,
            "value_brl": e.value_brl or 0,
        }

    # Group winning values by (catmat_group, winner_entity)
    # Then compute HHI per catmat_group
    group_winners: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for w in winners:
        info = event_info.get(str(w.event_id))
        if not info:
            continue
        catmat = info["catmat_group"]
        if catmat is None:
            continue  # sentinel/missing catmat — exclude from HHI distribution
        group_winners[catmat][str(w.entity_id)] += info["value_brl"]

    hhi_values: list[float] = []
    for catmat, winner_totals in group_winners.items():
        total = sum(winner_totals.values())
        if total <= 0:
            continue
        hhi = sum((v / total) ** 2 for v in winner_totals.values())
        hhi_values.append(hhi)

    results: list[BaselineMetrics] = []
    if hhi_values:
        metrics = compute_metrics(
            hhi_values, BaselineType.HHI_DISTRIBUTION, "national::all"
        )
        if metrics is not None:
            results.append(metrics)

    return results


async def _compute_amendment_baselines(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[BaselineMetrics]:
    """Compute AMENDMENT_DISTRIBUTION baselines."""
    stmt = (
        select(Event)
        .where(
            Event.type == "contrato",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
    )
    result = await session.execute(stmt)
    contracts = result.scalars().all()

    amendment_pcts: list[float] = []
    for c in contracts:
        original = c.attrs.get("original_value") or c.value_brl
        amendments_total = c.attrs.get("amendments_total_value", 0)
        if original and original > 0 and amendments_total is not None:
            amendment_pcts.append(amendments_total / original)

    results: list[BaselineMetrics] = []
    if amendment_pcts:
        metrics = compute_metrics(
            amendment_pcts, BaselineType.AMENDMENT_DISTRIBUTION, "national::all"
        )
        if metrics is not None:
            results.append(metrics)

    return results


async def _compute_duration_baselines(
    session: AsyncSession,
    window_start: datetime,
    window_end: datetime,
) -> list[BaselineMetrics]:
    """Compute CONTRACT_DURATION baselines."""
    stmt = (
        select(Event)
        .where(
            Event.type == "contrato",
            Event.occurred_at >= window_start,
            Event.occurred_at <= window_end,
        )
    )
    result = await session.execute(stmt)
    contracts = result.scalars().all()

    durations: list[float] = []
    for c in contracts:
        start = c.attrs.get("contract_start")
        end = c.attrs.get("contract_end")
        if start and end:
            try:
                s = datetime.fromisoformat(str(start))
                e = datetime.fromisoformat(str(end))
                days = (e - s).days
                if days > 0:
                    durations.append(float(days))
            except (ValueError, TypeError):
                pass

    results: list[BaselineMetrics] = []
    if durations:
        metrics = compute_metrics(
            durations, BaselineType.CONTRACT_DURATION, "national::all"
        )
        if metrics is not None:
            results.append(metrics)

    return results


async def _upsert_baseline_snapshot(
    session: AsyncSession,
    metrics: BaselineMetrics,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Upsert a BaselineSnapshot row from computed metrics."""
    stmt = (
        select(BaselineSnapshot)
        .where(
            BaselineSnapshot.baseline_type == metrics.baseline_type.value,
            BaselineSnapshot.scope_key == metrics.scope_key,
            BaselineSnapshot.window_start == window_start,
            BaselineSnapshot.window_end == window_end,
        )
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    metrics_dict = metrics.model_dump(by_alias=True)
    # Remove non-metric fields
    for key in ("baseline_type", "scope_key", "sample_size"):
        metrics_dict.pop(key, None)

    if existing:
        existing.sample_size = metrics.sample_size
        existing.metrics = metrics_dict
    else:
        snapshot = BaselineSnapshot(
            baseline_type=metrics.baseline_type.value,
            scope_key=metrics.scope_key,
            window_start=window_start,
            window_end=window_end,
            sample_size=metrics.sample_size,
            metrics=metrics_dict,
        )
        session.add(snapshot)


async def _has_new_events_since(
    session: AsyncSession,
    event_types: list[str],
    baseline_type_value: str,
) -> bool:
    """Check if new events exist since the last baseline computation for this type.

    Compares MAX(event.created_at) for the given event types against
    MAX(baseline_snapshot.updated_at) for this baseline type.
    Returns True if baselines should be recomputed (new data exists).
    """
    from openwatch_models.orm import BaselineSnapshot

    last_baseline_at = (
        await session.execute(
            select(func.max(BaselineSnapshot.updated_at)).where(
                BaselineSnapshot.baseline_type == baseline_type_value
            )
        )
    ).scalar_one()

    if last_baseline_at is None:
        # Baselines never computed — must run
        return True

    last_event_at = (
        await session.execute(
            select(func.max(Event.created_at)).where(
                Event.type.in_(event_types)
            )
        )
    ).scalar_one()

    if last_event_at is None:
        # No events at all — nothing to compute
        return False

    # Ensure both timestamps are timezone-aware before comparing.
    # asyncpg may return naive datetimes from aggregate functions.
    if last_event_at.tzinfo is None:
        last_event_at = last_event_at.replace(tzinfo=timezone.utc)
    if last_baseline_at.tzinfo is None:
        last_baseline_at = last_baseline_at.replace(tzinfo=timezone.utc)

    return last_event_at > last_baseline_at


async def compute_all_baselines(
    session: AsyncSession, force: bool = False,
) -> list[BaselineMetrics]:
    """Compute all baseline types over a 24-month window.

    Incremental: skips baseline types when no new events have been created
    since the last computation. Pass force=True to recompute everything.

    For each baseline type, queries events within the window,
    aggregates values, computes percentiles, and stores snapshots.
    Broadens scope when n < MIN_SAMPLE_SIZE (e.g., CATMAT group → CATMAT class).
    """
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=730)  # 24 months

    results: list[BaselineMetrics] = []
    skipped = 0

    # Each baseline type is checked independently — only recompute if new
    # events of the relevant type have been created since last run.

    # ── PRICE_BY_ITEM: depends on licitacao + contrato events ──
    if force or await _has_new_events_since(
        session, ["licitacao", "contrato"], BaselineType.PRICE_BY_ITEM.value
    ):
        price_baselines = await _compute_price_baselines(session, window_start, window_end)
        results.extend(price_baselines)
        for m in price_baselines:
            await _upsert_baseline_snapshot(session, m, window_start, window_end)
        await session.commit()
        log.info("compute_all_baselines.price_done", count=len(price_baselines))
    else:
        skipped += 1
        log.info("compute_all_baselines.price_skipped", reason="no_new_events")

    # ── PARTICIPANTS_PER_PROCUREMENT: depends on licitacao events ──
    if force or await _has_new_events_since(
        session, ["licitacao"], BaselineType.PARTICIPANTS_PER_PROCUREMENT.value
    ):
        participants_baselines = await _compute_participants_baselines(
            session, window_start, window_end
        )
        results.extend(participants_baselines)
        for m in participants_baselines:
            await _upsert_baseline_snapshot(session, m, window_start, window_end)
        await session.commit()
        log.info("compute_all_baselines.participants_done", count=len(participants_baselines))
    else:
        skipped += 1
        log.info("compute_all_baselines.participants_skipped", reason="no_new_events")

    # ── HHI_DISTRIBUTION: depends on licitacao events ──
    if force or await _has_new_events_since(
        session, ["licitacao"], BaselineType.HHI_DISTRIBUTION.value
    ):
        hhi_baselines = await _compute_hhi_baselines(session, window_start, window_end)
        results.extend(hhi_baselines)
        for m in hhi_baselines:
            await _upsert_baseline_snapshot(session, m, window_start, window_end)
        await session.commit()
        log.info("compute_all_baselines.hhi_done", count=len(hhi_baselines))
    else:
        skipped += 1
        log.info("compute_all_baselines.hhi_skipped", reason="no_new_events")

    # ── AMENDMENT_DISTRIBUTION: depends on contrato events ──
    if force or await _has_new_events_since(
        session, ["contrato"], BaselineType.AMENDMENT_DISTRIBUTION.value
    ):
        amendment_baselines = await _compute_amendment_baselines(
            session, window_start, window_end
        )
        results.extend(amendment_baselines)
        for m in amendment_baselines:
            await _upsert_baseline_snapshot(session, m, window_start, window_end)
        await session.commit()
        log.info("compute_all_baselines.amendment_done", count=len(amendment_baselines))
    else:
        skipped += 1
        log.info("compute_all_baselines.amendment_skipped", reason="no_new_events")

    # ── CONTRACT_DURATION: depends on contrato events ──
    if force or await _has_new_events_since(
        session, ["contrato"], BaselineType.CONTRACT_DURATION.value
    ):
        duration_baselines = await _compute_duration_baselines(
            session, window_start, window_end
        )
        results.extend(duration_baselines)
        for m in duration_baselines:
            await _upsert_baseline_snapshot(session, m, window_start, window_end)
        await session.commit()
        log.info("compute_all_baselines.duration_done", count=len(duration_baselines))
    else:
        skipped += 1
        log.info("compute_all_baselines.duration_skipped", reason="no_new_events")

    log.info(
        "compute_all_baselines.summary",
        computed=len(results),
        skipped_types=skipped,
        force=force,
    )
    return results
