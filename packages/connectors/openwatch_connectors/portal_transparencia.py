"""Connector for Portal da Transparência (api.portaldatransparencia.gov.br).

API docs: https://api.portaldatransparencia.gov.br/swagger-ui.html
Auth: header `chave-api-dados` with registered token.
Pagination: `pagina` (1-based), responses return list of items.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from sqlalchemy import select

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_connectors.http_client import portal_transparencia_client, DEFAULT_PAGE_SIZE
from openwatch_utils.logging import log
from openwatch_models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from openwatch_models.raw import RawItem

# Endpoint mapping per job
_ENDPOINTS: dict[str, str] = {
    "pt_sancoes_ceis_cnep": "/ceis",
    "pt_servidores_remuneracao": "/servidores",
    "pt_viagens": "/viagens",
    "pt_cartao_pagamento": "/cartoes",
    "pt_despesas_execucao": "/despesas/recursos-recebidos",
    "pt_beneficios": "/bolsa-familia-por-municipio",
    "pt_emendas": "/emendas",
    "pt_convenios_transferencias": "/convenios",
}

# Endpoints with MM/YYYY windowing (mesAnoInicio/mesAnoFim or equivalent)
_WINDOWED_MONTH_RANGES: dict[str, tuple[str, str]] = {
    "pt_despesas_execucao": ("mesAnoInicio", "mesAnoFim"),
    "pt_cartao_pagamento": ("mesExtratoInicio", "mesExtratoFim"),
    "pt_servidores_remuneracao": ("mesInicio", "mesFim"),
}
# Endpoints with DD/MM/YYYY day-level windowing
_WINDOWED_DAY_RANGES: dict[str, tuple[str, str]] = {
    "pt_viagens": ("dataIdaDe", "dataIdaAte"),
    "pt_convenios_transferencias": ("dataInicial", "dataFinal"),
}
# Endpoints with single YYYYMM mesAno param (one month per window)
_WINDOWED_MESANO_JOBS: set[str] = {"pt_beneficios"}

# Dimension-keyed jobs: iterate over external dimension keys from reference_data.
# Maps job_name -> (reference_data category, API query param name)
_DIMENSION_KEYED_JOBS: dict[str, tuple[str, str]] = {
    "pt_servidores_remuneracao": ("siape_orgao", "orgaoServidorExercicio"),
    "pt_beneficios": ("ibge_municipio", "codigoIbge"),
    "pt_viagens": ("siape_orgao", "codigoOrgao"),
}


def _parse_dimension_cursor(cursor: Optional[str]) -> tuple[int, int, int]:
    """Parse 3D cursor 'd{dim}w{window}p{page}' -> (dim_idx, window_idx, page)."""
    if cursor and cursor.startswith("d") and "w" in cursor and "p" in cursor:
        rest = cursor[1:]
        dim_str, rest2 = rest.split("w", 1)
        win_str, page_str = rest2.split("p", 1)
        return int(dim_str), int(win_str), int(page_str)
    return 0, 0, 1


def _parse_window_cursor(cursor: Optional[str]) -> tuple[int, int]:
    """Parse composite cursor 'w{window}p{page}' -> (window_idx, page)."""
    if cursor and cursor.startswith("w") and "p" in cursor:
        parts = cursor[1:].split("p", 1)
        return int(parts[0]), int(parts[1])
    # Legacy numeric cursors are incompatible with windowed mode.
    return 0, 1


def _add_months(month_start: date, months: int) -> date:
    total = month_start.year * 12 + (month_start.month - 1) + months
    year = total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def _last_day_of_month(month_start: date) -> date:
    return _add_months(month_start, 1) - timedelta(days=1)


def _parse_mm_yyyy(value: object) -> date:
    parsed = datetime.strptime(str(value).strip(), "%m/%Y").date()
    return parsed.replace(day=1)


def _parse_dd_mm_yyyy(value: object) -> date:
    return datetime.strptime(str(value).strip(), "%d/%m/%Y").date()


def _build_month_windows(
    start_month: date,
    end_month: date,
    months_per_window: int,
) -> list[tuple[date, date]]:
    windows: list[tuple[date, date]] = []
    current = start_month.replace(day=1)
    end_month = end_month.replace(day=1)
    while current <= end_month:
        next_start = _add_months(current, months_per_window)
        candidate_end = _last_day_of_month(_add_months(next_start, -1))
        final_end = min(candidate_end, _last_day_of_month(end_month))
        windows.append((current, final_end))
        current = next_start
    return windows


def _build_calendar_month_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Build windows fully contained within calendar months."""
    windows: list[tuple[date, date]] = []
    current_month = start.replace(day=1)
    while current_month <= end:
        month_end = _last_day_of_month(current_month)
        window_start = max(current_month, start)
        window_end = min(month_end, end)
        windows.append((window_start, window_end))
        current_month = _add_months(current_month, 1)
    return windows


def _extract_records(data: object) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        records = data.get("data", data.get("registros", [data]))
        return [item if isinstance(item, dict) else {"value": item} for item in records]
    return []


class PortalTransparenciaConnector(BaseConnector):
    """Connector for Portal da Transparência (api.portaldatransparencia.gov.br)."""

    @property
    def name(self) -> str:
        return "portal_transparencia"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="pt_sancoes_ceis_cnep",
                description="CEIS/CNEP sanctions registry",
                domain="sancao",
                enabled=True,
            ),
            JobSpec(
                name="pt_servidores_remuneracao",
                description="Federal civil servants — iterates per SIAPE organ",
                domain="remuneracao",
                enabled=True,
            ),
            JobSpec(
                name="pt_viagens",
                description="Official travel expenses",
                domain="despesa",
                enabled=True,
            ),
            JobSpec(
                name="pt_cartao_pagamento",
                description="Government payment card transactions",
                domain="despesa",
                enabled=True,
            ),
            JobSpec(
                name="pt_despesas_execucao",
                description="Budget execution — expenditure items",
                domain="despesa",
                enabled=True,
            ),
            JobSpec(
                name="pt_beneficios",
                description="Social benefits — iterates per IBGE municipality",
                domain="beneficio",
                enabled=True,
            ),
            JobSpec(
                name="pt_emendas",
                description="Parliamentary amendments",
                domain="emenda",
                enabled=True,
            ),
            JobSpec(
                name="pt_convenios_transferencias",
                description="Agreements and voluntary transfers",
                domain="transferencia",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        endpoint = _ENDPOINTS.get(job.name)
        if endpoint is None:
            raise ValueError(f"Unknown job: {job.name}")

        params = params or {}

        # Dimension-keyed jobs: iterate dimension × window × page
        if job.name in _DIMENSION_KEYED_JOBS:
            return await self._fetch_dimension_windowed(
                job, endpoint, cursor=cursor, params=params
            )

        # Endpoints with windowed pagination (month, day, or mesAno)
        if (
            job.name in _WINDOWED_MONTH_RANGES
            or job.name in _WINDOWED_DAY_RANGES
            or job.name in _WINDOWED_MESANO_JOBS
        ):
            return await self._fetch_windowed(job, endpoint, cursor=cursor, params=params)

        page = int(cursor) if cursor else 1
        query_params: dict = {"pagina": page}

        # Merge user params (date ranges, filters, etc.)
        query_params.update(params)

        async with portal_transparencia_client() as client:
            response = await client.get(endpoint, params=query_params)
            # Portal da Transparência returns 405 when pagination depth is exceeded.
            # Treat as end-of-data instead of an error to preserve already-fetched items.
            if response.status_code in (405, 403):
                log.warning(
                    "portal_transparencia.pagination_limit",
                    job=job.name,
                    page=page,
                    status=response.status_code,
                )
                return [], None
            if response.status_code == 302:
                log.warning(
                    "portal_transparencia.rate_limited",
                    job=job.name,
                    page=page,
                )
                return [], str(page)
            response.raise_for_status()
            data = [] if response.status_code == 204 else response.json()

        # Portal Transparência returns a list; empty list means no more pages
        records = _extract_records(data)
        items = [
            RawItem(
                raw_id=f"{job.name}:{page}:{i}",
                data=item,
            )
            for i, item in enumerate(records)
        ]
        next_cursor = str(page + 1) if len(records) > 0 else None
        return items, next_cursor

    def _build_windowed_windows(
        self, job: JobSpec, params: dict
    ) -> tuple[list, str | None, str | None]:
        """Build the list of time windows for a windowed job.

        Returns (windows, window_type, error_message).
        window_type is one of 'month_range', 'day_range', 'mesano'.
        """
        if job.name in _WINDOWED_MONTH_RANGES:
            start_key, end_key = _WINDOWED_MONTH_RANGES[job.name]
            default_end = date.today().replace(day=1) - timedelta(days=1)
            default_start = _add_months(default_end.replace(day=1), -60)
            start_month = _parse_mm_yyyy(params[start_key]) if start_key in params else default_start
            end_month = _parse_mm_yyyy(params[end_key]) if end_key in params else default_end.replace(day=1)
            if start_month > end_month:
                raise ValueError(f"Invalid date range for {job.name}: {start_month} > {end_month}")
            return _build_month_windows(start_month, end_month, months_per_window=12), "month_range", None

        if job.name in _WINDOWED_DAY_RANGES:
            start_key, end_key = _WINDOWED_DAY_RANGES[job.name]
            default_end = date.today()
            default_start = _add_months(default_end.replace(day=1), -60)
            start_date = _parse_dd_mm_yyyy(params[start_key]) if start_key in params else default_start
            end_date = _parse_dd_mm_yyyy(params[end_key]) if end_key in params else default_end
            if start_date > end_date:
                raise ValueError(f"Invalid date range for {job.name}: {start_date} > {end_date}")
            return _build_calendar_month_windows(start_date, end_date), "day_range", None

        # _WINDOWED_MESANO_JOBS: single mesAno param (YYYYMM), one month per window
        default_end = date.today().replace(day=1) - timedelta(days=1)
        default_start = _add_months(default_end.replace(day=1), -60)
        months: list[date] = []
        current = default_start.replace(day=1)
        end_month = default_end.replace(day=1)
        while current <= end_month:
            months.append(current)
            current = _add_months(current, 1)
        return months, "mesano", None

    def _apply_windowed_query_params(
        self, job: JobSpec, windows: list, window_idx: int,
        window_type: str, query_params: dict, page: int,
    ) -> None:
        """Set query params for the given window index."""
        if window_type == "month_range":
            start_key, end_key = _WINDOWED_MONTH_RANGES[job.name]
            window_start, window_end = windows[window_idx]
            query_params["pagina"] = page
            query_params[start_key] = window_start.strftime("%m/%Y")
            query_params[end_key] = window_end.strftime("%m/%Y")
        elif window_type == "day_range":
            start_key, end_key = _WINDOWED_DAY_RANGES[job.name]
            window_start, window_end = windows[window_idx]
            query_params["pagina"] = page
            query_params[start_key] = window_start.strftime("%d/%m/%Y")
            query_params[end_key] = window_end.strftime("%d/%m/%Y")
            if job.name == "pt_viagens":
                query_params["dataRetornoDe"] = window_start.strftime("%d/%m/%Y")
                query_params["dataRetornoAte"] = window_end.strftime("%d/%m/%Y")
        else:  # mesano
            query_params["mesAno"] = windows[window_idx].strftime("%Y%m")
            query_params["pagina"] = page

    async def _fetch_windowed(
        self,
        job: JobSpec,
        endpoint: str,
        cursor: Optional[str],
        params: dict,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Fetch window-constrained endpoints using cursor format 'w{window}p{page}'.

        Skips windows that return 400 (e.g., old date ranges rejected by the API)
        internally, so the ingest loop doesn't stop on the first empty window.
        """
        window_idx, page = _parse_window_cursor(cursor)
        base_params = {k: v for k, v in params.items() if k != "pagina"}

        windows, window_type, _ = self._build_windowed_windows(job, base_params)
        total_windows = len(windows)

        # Skip through windows that return 400 (old date ranges, etc.)
        while window_idx < total_windows:
            query_params = dict(base_params)
            self._apply_windowed_query_params(
                job, windows, window_idx, window_type, query_params, page
            )

            async with portal_transparencia_client() as client:
                response = await client.get(endpoint, params=query_params)

                if response.status_code in (405, 403):
                    log.warning(
                        "portal_transparencia.pagination_limit_windowed",
                        job=job.name,
                        window=window_idx,
                        page=page,
                        status=response.status_code,
                    )
                    window_idx += 1
                    page = 1
                    continue

                if response.status_code == 400:
                    log.warning(
                        "portal_transparencia.windowed_bad_request",
                        job=job.name,
                        window=window_idx,
                        page=page,
                    )
                    window_idx += 1
                    page = 1
                    continue

                if response.status_code == 302:
                    log.warning(
                        "portal_transparencia.windowed_rate_limited",
                        job=job.name,
                        window=window_idx,
                        page=page,
                    )
                    return [], f"w{window_idx}p{page}"

                response.raise_for_status()
                data = [] if response.status_code == 204 else response.json()

            records = _extract_records(data)
            items = [
                RawItem(
                    raw_id=f"{job.name}:w{window_idx}p{page}:{i}",
                    data=item,
                )
                for i, item in enumerate(records)
            ]

            if len(records) > 0:
                next_cursor = f"w{window_idx}p{page + 1}"
            elif window_idx + 1 < total_windows:
                next_cursor = f"w{window_idx + 1}p1"
            else:
                next_cursor = None
            return items, next_cursor

        # All windows exhausted
        return [], None

    def _get_dimension_keys(self, category: str) -> list[str]:
        """Load dimension keys from reference_data table (cached on self)."""
        cache_attr = f"_cached_{category}"
        if hasattr(self, cache_attr):
            return getattr(self, cache_attr)

        from openwatch_db.db_sync import SyncSession
        from openwatch_models.orm import ReferenceData

        with SyncSession() as session:
            stmt = (
                select(ReferenceData.code)
                .where(ReferenceData.category == category)
                .order_by(ReferenceData.code)
            )
            codes = list(session.execute(stmt).scalars().all())

        if not codes:
            raise RuntimeError(
                f"reference_data table has no entries for category '{category}'. "
                f"Run: curl -X POST http://localhost:8000/internal/reference/seed"
            )

        setattr(self, cache_attr, codes)
        log.info(
            "portal_transparencia.dimension_keys_loaded",
            category=category,
            count=len(codes),
        )
        return codes

    def _build_windows_for_job(self, job: JobSpec) -> list:
        """Build time windows for a job (reuses windowed logic)."""
        if job.name in _WINDOWED_MONTH_RANGES:
            default_end = date.today().replace(day=1) - timedelta(days=1)
            default_start = _add_months(default_end.replace(day=1), -60)
            return _build_month_windows(default_start, default_end.replace(day=1), months_per_window=12)
        if job.name in _WINDOWED_MESANO_JOBS:
            default_end = date.today().replace(day=1) - timedelta(days=1)
            default_start = _add_months(default_end.replace(day=1), -60)
            months: list[date] = []
            current = default_start.replace(day=1)
            end_month = default_end.replace(day=1)
            while current <= end_month:
                months.append(current)
                current = _add_months(current, 1)
            return months
        if job.name in _WINDOWED_DAY_RANGES:
            default_end = date.today()
            default_start = _add_months(default_end.replace(day=1), -60)
            return _build_calendar_month_windows(default_start, default_end)
        return []

    def _apply_window_params(
        self, job: JobSpec, windows: list, window_idx: int, query_params: dict
    ) -> None:
        """Apply window-specific query parameters."""
        if job.name in _WINDOWED_MONTH_RANGES:
            start_key, end_key = _WINDOWED_MONTH_RANGES[job.name]
            window_start, window_end = windows[window_idx]
            query_params[start_key] = window_start.strftime("%m/%Y")
            query_params[end_key] = window_end.strftime("%m/%Y")
        elif job.name in _WINDOWED_MESANO_JOBS:
            query_params["mesAno"] = windows[window_idx].strftime("%Y%m")
        elif job.name in _WINDOWED_DAY_RANGES:
            start_key, end_key = _WINDOWED_DAY_RANGES[job.name]
            window_start, window_end = windows[window_idx]
            query_params[start_key] = window_start.strftime("%d/%m/%Y")
            query_params[end_key] = window_end.strftime("%d/%m/%Y")
            # pt_viagens requires return-date range as mandatory params.
            # Use same window so we capture trips that both departed and returned
            # within the month; cross-month trips are caught in the next window.
            if job.name == "pt_viagens":
                query_params["dataRetornoDe"] = window_start.strftime("%d/%m/%Y")
                query_params["dataRetornoAte"] = window_end.strftime("%d/%m/%Y")

    async def _fetch_dimension_windowed(
        self,
        job: JobSpec,
        endpoint: str,
        cursor: Optional[str],
        params: dict,
    ) -> tuple[list[RawItem], Optional[str]]:
        """Iterate: dimension_key x time_window x page (3D cursor).

        When a dimension/window returns empty data, skips forward internally
        (up to _MAX_EMPTY_SKIPS attempts) to find the next non-empty slot.
        This prevents the ingest task from stopping on the first empty dimension.
        """
        dim_idx, window_idx, page = _parse_dimension_cursor(cursor)
        ref_category, dim_param = _DIMENSION_KEYED_JOBS[job.name]

        dim_keys = self._get_dimension_keys(ref_category)
        if dim_idx >= len(dim_keys):
            return [], None

        windows = self._build_windows_for_job(job)
        total_windows = len(windows)

        # If no windows defined, treat as single-window job
        if total_windows == 0:
            total_windows = 1

        # Skip forward through empty dimension/window combinations.
        # 400 (invalid key) advances dim_idx without counting against the budget —
        # so all N dimension keys can be iterated regardless of how many are invalid.
        # Only truly empty-data responses (valid key, no records) count against the
        # budget to avoid hammering the API when a whole date range is legitimately empty.
        max_empty_skips = max(1000, len(dim_keys) * 3)
        skips = 0

        while skips < max_empty_skips:
            if dim_idx >= len(dim_keys):
                return [], None

            if window_idx >= total_windows:
                # Move to next dimension key
                dim_idx += 1
                window_idx = 0
                page = 1
                continue

            # Build query params
            query_params = {k: v for k, v in params.items() if k != "pagina"}
            query_params[dim_param] = dim_keys[dim_idx]
            query_params["pagina"] = page

            if windows:
                self._apply_window_params(job, windows, window_idx, query_params)

            async with portal_transparencia_client() as client:
                response = await client.get(endpoint, params=query_params)

                if response.status_code in (405, 403):
                    log.warning(
                        "portal_transparencia.dimension_pagination_limit",
                        job=job.name,
                        dim_idx=dim_idx,
                        window=window_idx,
                        page=page,
                        status=response.status_code,
                    )
                    # Skip to next window or dimension
                    window_idx += 1
                    page = 1
                    skips += 1
                    await asyncio.sleep(0.3)
                    continue

                if response.status_code == 400:
                    # Invalid dimension key — skip to next dim without counting
                    # against empty-data budget (these are structural, not data gaps).
                    log.warning(
                        "portal_transparencia.dimension_invalid_key",
                        job=job.name,
                        dim_key=dim_keys[dim_idx],
                        status=400,
                    )
                    dim_idx += 1
                    window_idx = 0
                    page = 1
                    # Do NOT increment skips — invalid keys are not empty-data skips
                    await asyncio.sleep(0.1)
                    continue

                if response.status_code == 302:
                    # PT API rate limit: 302 redirect to bloqueio-acesso.
                    # Return current position as cursor so ingest resumes later.
                    log.warning(
                        "portal_transparencia.dimension_rate_limited",
                        job=job.name,
                        dim_idx=dim_idx,
                        window=window_idx,
                        page=page,
                    )
                    return [], f"d{dim_idx}w{window_idx}p{page}"

                response.raise_for_status()
                data = [] if response.status_code == 204 else response.json()

            records = _extract_records(data)

            if not records:
                # Empty response — advance to next window or dimension
                window_idx += 1
                page = 1
                skips += 1
                # Throttle skip-ahead to avoid triggering rate limits
                await asyncio.sleep(0.3)
                continue

            # Found data — build items and cursor
            items = [
                RawItem(
                    raw_id=f"{job.name}:d{dim_idx}w{window_idx}p{page}:{i}",
                    data=r,
                )
                for i, r in enumerate(records)
            ]

            # 3D cursor advancement: page -> window -> dimension
            if len(records) > 0:
                next_cursor = f"d{dim_idx}w{window_idx}p{page + 1}"
            elif window_idx + 1 < total_windows:
                next_cursor = f"d{dim_idx}w{window_idx + 1}p1"
            elif dim_idx + 1 < len(dim_keys):
                next_cursor = f"d{dim_idx + 1}w0p1"
            else:
                next_cursor = None

            if skips > 0:
                log.info(
                    "portal_transparencia.dimension_skipped_empty",
                    job=job.name,
                    skips=skips,
                    landed_dim=dim_idx,
                    landed_window=window_idx,
                )

            return items, next_cursor

        # Exhausted skip budget — return current position as cursor for next call
        if dim_idx < len(dim_keys):
            log.info(
                "portal_transparencia.dimension_skip_budget_exhausted",
                job=job.name,
                dim_idx=dim_idx,
                window_idx=window_idx,
                skips=skips,
            )
            return [], f"d{dim_idx}w{window_idx}p1"

        return [], None

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "pt_sancoes_ceis_cnep":
            return self._normalize_sancoes(raw_items)
        if job.name == "pt_servidores_remuneracao":
            return self._normalize_servidores(raw_items)
        if job.name == "pt_viagens":
            return self._normalize_viagens(raw_items)
        if job.name == "pt_cartao_pagamento":
            return self._normalize_cartao(raw_items)
        if job.name == "pt_emendas":
            return self._normalize_emendas(raw_items)
        if job.name == "pt_convenios_transferencias":
            return self._normalize_convenios(raw_items)
        if job.name == "pt_beneficios":
            return self._normalize_beneficios(raw_items)
        # Generic fallback
        return self._normalize_generic(job, raw_items)

    # ── Normalizers ──────────────────────────────────────────────────

    def _normalize_sancoes(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            pessoa = d.get("pessoa", {}) if isinstance(d.get("pessoa"), dict) else {}
            sancionado = d.get("sancionado", d)
            nome = (
                sancionado.get("nome")
                or sancionado.get("razaoSocial")
                or pessoa.get("nome")
                or ""
            )
            cnpj_cpf = _extract_sancionado_identifier(d)
            tipo = "company" if len(cnpj_cpf) == 14 else "person"
            identifiers = (
                {"cnpj": cnpj_cpf}
                if len(cnpj_cpf) == 14
                else {"cpf": cnpj_cpf} if len(cnpj_cpf) == 11 else {}
            )

            sanction_start = _parse_any_datetime(
                d.get("dataInicioSancao") or d.get("dataPublicacao")
            )
            sanction_end = _parse_any_datetime(d.get("dataFimSancao"))
            sanction_type = (
                d.get("tipoSancao", {}).get("descricaoResumida")
                or d.get("tipoSancao", {}).get("descricao")
                or d.get("fonteSancao", "")
            )

            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=cnpj_cpf or item.raw_id,
                type=tipo,
                name=nome,
                identifiers=identifiers,
                attrs={"uf": sancionado.get("ufSancionado", "")},
            )
            entities.append(entity)

            # Sanctioning body as second participant (enables edges)
            participants = [
                CanonicalEventParticipant(entity_ref=entity, role="sanctioned"),
            ]
            orgao_raw = d.get("orgaoSancionador", {})
            orgao_nome = orgao_raw.get("nome", "") if isinstance(orgao_raw, dict) else str(orgao_raw) if orgao_raw else ""
            if orgao_nome:
                orgao_entity = CanonicalEntity(
                    source_connector="portal_transparencia",
                    source_id=f"org:{orgao_nome}",
                    type="org",
                    name=orgao_nome,
                )
                entities.append(orgao_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=orgao_entity, role="sanctioning_body")
                )

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="sancao",
                subtype=sanction_type,
                description=d.get("textoPublicacao", ""),
                occurred_at=sanction_start,
                attrs={
                    "orgao_sancionador": orgao_nome,
                    "sanction_start": sanction_start.isoformat() if sanction_start else None,
                    "sanction_end": sanction_end.isoformat() if sanction_end else None,
                    "sanction_type": sanction_type,
                    "fonte": d.get("fonteSancao", ""),
                    "uf": sancionado.get("ufSancionado", ""),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_servidores(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            orgao_nome = d.get("orgaoServidorExercicio", "")
            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=str(d.get("id", item.raw_id)),
                type="person",
                name=d.get("nome", ""),
                identifiers={"cpf": d.get("cpf", "")},
                attrs={
                    "orgao": orgao_nome,
                    "cargo": d.get("cargoEfetivo", d.get("funcao", "")),
                },
            )
            entities.append(entity)

            # Employer org as second participant (enables edges)
            participants = [
                CanonicalEventParticipant(entity_ref=entity, role="servant"),
            ]
            if orgao_nome:
                orgao_entity = CanonicalEntity(
                    source_connector="portal_transparencia",
                    source_id=f"org:{orgao_nome}",
                    type="org",
                    name=orgao_nome,
                )
                entities.append(orgao_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=orgao_entity, role="employer")
                )

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="remuneracao",
                description=f"Remuneração de {d.get('nome', '')}",
                occurred_at=_parse_mes_ano(d.get("mesAno")),
                value_brl=_safe_float(d.get("remuneracaoBasicaBruta")),
                attrs={
                    "mes_ano": d.get("mesAno", ""),
                    "remuneracao_liquida": _safe_float(d.get("remuneracaoAposDeducoes")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_viagens(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            orgao_nome = d.get("orgao", "")
            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=str(d.get("id", item.raw_id)),
                type="person",
                name=d.get("nome", d.get("beneficiario", "")),
                identifiers={"cpf": d.get("cpf", "")},
            )
            entities.append(entity)

            # Org as second participant (enables edges)
            participants = [
                CanonicalEventParticipant(entity_ref=entity, role="traveler"),
            ]
            if orgao_nome:
                orgao_entity = CanonicalEntity(
                    source_connector="portal_transparencia",
                    source_id=f"org:{orgao_nome}",
                    type="org",
                    name=orgao_nome,
                )
                entities.append(orgao_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=orgao_entity, role="org")
                )

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="viagem",
                description=d.get("motivo", ""),
                occurred_at=_parse_any_datetime(d.get("dataInicio")),
                value_brl=_safe_float(d.get("valor")),
                attrs={
                    "destino": d.get("destino", ""),
                    "orgao": orgao_nome,
                    "data_inicio": d.get("dataInicio", ""),
                    "data_fim": d.get("dataFim", ""),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_cartao(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            portador = d.get("portador", {})
            if isinstance(portador, dict):
                portador_nome = portador.get("nome", "")
                portador_cpf = _digits_only(portador.get("cpfFormatado", portador.get("cpf", d.get("cpf", ""))))
            else:
                portador_nome = str(portador) if portador else d.get("nome", "")
                portador_cpf = _digits_only(d.get("cpf", ""))
            ug = d.get("unidadeGestora", {})
            ug_nome = ug.get("nome", "") if isinstance(ug, dict) else ""
            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=portador_cpf or str(d.get("id", item.raw_id)),
                type="person",
                name=portador_nome,
                identifiers={"cpf": portador_cpf} if portador_cpf else {},
                attrs={"orgao": ug_nome},
            )
            entities.append(entity)

            # Org (unidadeGestora) as second participant (enables edges)
            participants = [
                CanonicalEventParticipant(entity_ref=entity, role="card_holder"),
            ]
            if ug_nome:
                ug_entity = CanonicalEntity(
                    source_connector="portal_transparencia",
                    source_id=f"org:{ug_nome}",
                    type="org",
                    name=ug_nome,
                )
                entities.append(ug_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=ug_entity, role="org")
                )

            tipo_cartao = d.get("tipoCartao", "")
            if isinstance(tipo_cartao, dict):
                tipo_cartao = tipo_cartao.get("descricao", tipo_cartao.get("nome", str(tipo_cartao)))
            estabelecimento = d.get("estabelecimento", "")
            if isinstance(estabelecimento, dict):
                estabelecimento = estabelecimento.get("nome", estabelecimento.get("descricao", str(estabelecimento)))
            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="pagamento_cartao",
                description=str(tipo_cartao),
                occurred_at=_parse_any_datetime(d.get("dataTransacao")),
                value_brl=_safe_float(d.get("valorTransacao", d.get("valor"))),
                attrs={
                    "estabelecimento": str(estabelecimento),
                    "data": d.get("dataTransacao", ""),
                    "uf": (
                        d.get("uf", "")
                        or (ug.get("uf", "") if isinstance(ug, dict) else "")
                    ),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_emendas(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            autor = d.get("autor", d.get("nomeAutor", ""))
            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=str(d.get("codigoEmenda", item.raw_id)),
                type="person",
                name=autor,
                attrs={"tipo_emenda": d.get("tipoEmenda", "")},
            )
            entities.append(entity)

            # Extract UF from dedicated field or parse from localidade ("Cidade/UF")
            localidade = d.get("localidadeDoGasto", d.get("localidadeGasto", ""))
            uf_emenda = d.get("uf", "")
            if not uf_emenda and isinstance(localidade, str) and "/" in localidade:
                uf_emenda = localidade.rsplit("/", 1)[-1].strip()[:2]

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="emenda",
                description=localidade,
                occurred_at=_parse_ano_only(d.get("ano")),
                value_brl=_safe_float(d.get("valorEmpenhado", d.get("valor"))),
                attrs={
                    "ano": d.get("ano", ""),
                    "funcao": d.get("funcao", ""),
                    "subfuncao": d.get("subfuncao", ""),
                    "valor_pago": _safe_float(d.get("valorPago")),
                    "uf": uf_emenda,
                },
                participants=[
                    CanonicalEventParticipant(entity_ref=entity, role="author")
                ],
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_convenios(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            proponente = d.get("proponente", d.get("nomeProponente", ""))
            cnpj = d.get("cnpjProponente", "")

            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=cnpj or str(d.get("id", item.raw_id)),
                type="company",
                name=proponente if isinstance(proponente, str) else str(proponente),
                identifiers={"cnpj": cnpj} if cnpj else {},
            )
            entities.append(entity)

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="convenio",
                description=d.get("objeto", ""),
                occurred_at=_parse_any_datetime(
                    d.get("dataInicioVigencia")
                    or d.get("dataAssinatura")
                    or d.get("dataCelebracao")
                ),
                value_brl=_safe_float(d.get("valorConvenio", d.get("valor"))),
                attrs={
                    "numero": d.get("numero", ""),
                    "orgao": d.get("orgaoConcedente", ""),
                    "situacao": d.get("situacao", ""),
                    "uf": d.get("ufProponente", d.get("uf", "")),
                },
                participants=[
                    CanonicalEventParticipant(entity_ref=entity, role="proponent")
                ],
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_beneficios(self, items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in items:
            d = item.data
            municipio = d.get("municipio", {})
            if isinstance(municipio, dict):
                municipio_nome = municipio.get("nomeIBGE", municipio.get("nome", ""))
                uf = municipio.get("uf", {}).get("sigla", "") if isinstance(municipio.get("uf"), dict) else municipio.get("uf", "")
                ibge_code = municipio.get("codigoIBGE", municipio_nome)
            else:
                municipio_nome = str(municipio) if municipio else ""
                uf = ""
                ibge_code = municipio_nome

            entity = CanonicalEntity(
                source_connector="portal_transparencia",
                source_id=f"municipio:{ibge_code}",
                type="org",
                name=f"{municipio_nome}/{uf}" if uf else municipio_nome,
                attrs={"municipio": municipio_nome, "uf": uf},
            )
            entities.append(entity)

            tipo_beneficio = d.get("tipoBeneficio", d.get("tipo", ""))
            if isinstance(tipo_beneficio, dict):
                tipo_beneficio = tipo_beneficio.get("descricao", tipo_beneficio.get("nome", str(tipo_beneficio)))

            event = CanonicalEvent(
                source_connector="portal_transparencia",
                source_id=item.raw_id,
                type="beneficio",
                subtype=str(tipo_beneficio),
                description=str(tipo_beneficio),
                occurred_at=_parse_mes_ano(d.get("mesAno")),
                value_brl=_safe_float(d.get("valor", d.get("valorBeneficio"))),
                attrs={
                    "municipio": municipio_nome,
                    "uf": uf,
                    "mes_ano": d.get("mesAno", ""),
                    "tipo_beneficio": str(tipo_beneficio),
                    "quantidade_beneficiarios": d.get("quantidadeBeneficiarios", d.get("quantidade")),
                },
                participants=[
                    CanonicalEventParticipant(entity_ref=entity, role="municipio"),
                ],
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_generic(
        self, job: JobSpec, items: list[RawItem]
    ) -> NormalizeResult:
        events = []
        for item in items:
            events.append(
                CanonicalEvent(
                    source_connector="portal_transparencia",
                    source_id=item.raw_id,
                    type=job.domain,
                    attrs=item.data,
                )
            )
        return NormalizeResult(events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw
    if "," in raw and "." in raw:
        normalized = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        normalized = raw.replace(",", ".")
    try:
        return float(normalized)
    except (ValueError, TypeError):
        return None


def _digits_only(value: object) -> str:
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _extract_sancionado_identifier(payload: dict) -> str:
    sancionado = payload.get("sancionado", {})
    pessoa = payload.get("pessoa", {})

    candidates = [
        sancionado.get("cnpjCpf"),
        sancionado.get("cpfCnpj"),
        sancionado.get("codigoFormatado"),
        pessoa.get("cnpj"),
        pessoa.get("cpf"),
        pessoa.get("cnpjFormatado"),
        pessoa.get("cpfFormatado"),
        payload.get("cnpjCpf"),
        payload.get("cpfCnpj"),
    ]

    for candidate in candidates:
        cleaned = _digits_only(candidate)
        if len(cleaned) in (11, 14):
            return cleaned
    return ""


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _parse_mes_ano(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value)
    if len(raw) == 6 and raw.isdigit():
        return datetime(int(raw[:4]), int(raw[4:6]), 1, tzinfo=timezone.utc)
    return None


def _parse_ano_only(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value)
    if len(raw) == 4 and raw.isdigit():
        return datetime(int(raw), 1, 1, tzinfo=timezone.utc)
    return None
