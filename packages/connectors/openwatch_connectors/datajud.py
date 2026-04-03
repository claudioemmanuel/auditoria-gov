"""Connector for DataJud (CNJ) — National judicial process registry.

API: https://api-publica.datajud.cnj.jus.br
Auth: Optional APIKey via DATAJUD_API_KEY env var; public access works
      without a key but is rate-limited.
Backend: Elasticsearch — queries use POST /{api_suffix}/_search with JSON body.

Cursor format: "{tribunal_idx}:{sort_token_b64}"
  - tribunal_idx : 0-based index into the job's tribunal list
  - sort_token   : base64-encoded JSON of the last Elasticsearch hit's "sort" array
  - Initial state: "0:" (tribunal 0, no search_after)
"""

import base64
import json
from datetime import datetime, timezone
from typing import Optional

import httpx

from openwatch_connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from openwatch_connectors.http_client import datajud_client
from openwatch_utils.logging import log as _log
from openwatch_models.canonical import CanonicalEvent, NormalizeResult
from openwatch_models.raw import RawItem

# ── Tribunal endpoint suffixes ────────────────────────────────────────────────
# Full list from: https://datajud-wiki.cnj.jus.br/api-publica/endpoints

# Superiores + Federais — highest signal for procurement/corruption cases
_TRIBUNALS_FEDERAL = [
    "api_publica_stj",
    "api_publica_trf1",
    "api_publica_trf2",
    "api_publica_trf3",
    "api_publica_trf4",
    "api_publica_trf5",
    "api_publica_trf6",
]

# State courts — critical for state-level public contracts
_TRIBUNALS_ESTADUAIS = [
    "api_publica_tjac", "api_publica_tjal", "api_publica_tjam", "api_publica_tjap",
    "api_publica_tjba", "api_publica_tjce", "api_publica_tjdft", "api_publica_tjes",
    "api_publica_tjgo", "api_publica_tjma", "api_publica_tjmg", "api_publica_tjms",
    "api_publica_tjmt", "api_publica_tjpa", "api_publica_tjpb", "api_publica_tjpe",
    "api_publica_tjpi", "api_publica_tjpr", "api_publica_tjrj", "api_publica_tjrn",
    "api_publica_tjro", "api_publica_tjrr", "api_publica_tjrs", "api_publica_tjsc",
    "api_publica_tjse", "api_publica_tjsp", "api_publica_tjto",
]

# Labor courts — relevant for labor fraud in public contracts
_TRIBUNALS_TRABALHO = [
    "api_publica_tst",
    "api_publica_trt1",  "api_publica_trt2",  "api_publica_trt3",  "api_publica_trt4",
    "api_publica_trt5",  "api_publica_trt6",  "api_publica_trt7",  "api_publica_trt8",
    "api_publica_trt9",  "api_publica_trt10", "api_publica_trt11", "api_publica_trt12",
    "api_publica_trt13", "api_publica_trt14", "api_publica_trt15", "api_publica_trt16",
    "api_publica_trt17", "api_publica_trt18", "api_publica_trt19", "api_publica_trt20",
    "api_publica_trt21", "api_publica_trt22", "api_publica_trt23", "api_publica_trt24",
]

# Electoral courts — corruption/financing intelligence
_TRIBUNALS_ELEITORAIS = [
    "api_publica_tse",
    "api_publica_tre-ac", "api_publica_tre-al", "api_publica_tre-am", "api_publica_tre-ap",
    "api_publica_tre-ba", "api_publica_tre-ce", "api_publica_tre-dft", "api_publica_tre-es",
    "api_publica_tre-go", "api_publica_tre-ma", "api_publica_tre-mg", "api_publica_tre-ms",
    "api_publica_tre-mt", "api_publica_tre-pa", "api_publica_tre-pb", "api_publica_tre-pe",
    "api_publica_tre-pi", "api_publica_tre-pr", "api_publica_tre-rj", "api_publica_tre-rn",
    "api_publica_tre-ro", "api_publica_tre-rr", "api_publica_tre-rs", "api_publica_tre-sc",
    "api_publica_tre-se", "api_publica_tre-sp", "api_publica_tre-to",
]

# Improbidade: federal + state courts cover the bulk of public-sector fraud cases
_TRIBUNALS_IMPROBIDADE = _TRIBUNALS_FEDERAL + _TRIBUNALS_ESTADUAIS

# Licitação: federal + state (where procurement contracts are enforced)
_TRIBUNALS_LICITACAO = _TRIBUNALS_FEDERAL + _TRIBUNALS_ESTADUAIS

# ── Base Elasticsearch query bodies ──────────────────────────────────────────

_QUERY_IMPROBIDADE: dict = {
    "query": {"match": {"assuntos.nome": "Improbidade Administrativa"}},
    "size": 100,
    "sort": [{"@timestamp": {"order": "asc"}}],
}

_QUERY_LICITACAO: dict = {
    "query": {
        "bool": {
            "should": [
                {"match": {"assuntos.nome": "Licitação"}},
                {"match": {"assuntos.nome": "Fraude"}},
            ],
            "minimum_should_match": 1,
        }
    },
    "size": 100,
    "sort": [{"@timestamp": {"order": "asc"}}],
}

# Job name → (base_query, tribunal_list)
_JOB_CONFIG: dict[str, tuple[dict, list[str]]] = {
    "datajud_processos_improbidade": (_QUERY_IMPROBIDADE, _TRIBUNALS_IMPROBIDADE),
    "datajud_processos_licitacao": (_QUERY_LICITACAO, _TRIBUNALS_LICITACAO),
}

# HTTP status codes that indicate the tribunal is temporarily unavailable;
# we skip it rather than aborting the entire run.
_SKIP_STATUSES: frozenset[int] = frozenset({404, 429, 503})


# ── Cursor helpers ────────────────────────────────────────────────────────────

def _parse_cursor(cursor: Optional[str]) -> tuple[int, Optional[list]]:
    """Parse a cursor string → (tribunal_idx, search_after_values | None)."""
    if not cursor:
        return 0, None
    parts = cursor.split(":", 1)
    idx = int(parts[0])
    token = parts[1] if len(parts) > 1 else ""
    if not token:
        return idx, None
    sort_values: list = json.loads(base64.b64decode(token).decode())
    return idx, sort_values


def _encode_cursor(tribunal_idx: int, sort_values: list) -> str:
    """Encode (tribunal_idx, sort_values) → cursor string."""
    token = base64.b64encode(json.dumps(sort_values).encode()).decode()
    return f"{tribunal_idx}:{token}"


# ── Date parsing ──────────────────────────────────────────────────────────────

def _parse_iso_datetime(value: object) -> Optional[datetime]:
    """Parse an ISO 8601 string into a timezone-aware datetime, or return None."""
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


# ── Connector ─────────────────────────────────────────────────────────────────

class DataJudConnector(BaseConnector):
    """Connector for DataJud (CNJ) — National judicial process registry."""

    @property
    def name(self) -> str:
        return "datajud"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="datajud_processos_improbidade",
                description="Administrative improbity processes (STJ, TRF1-6, all 27 state TJs)",
                domain="processo_judicial",
                enabled=True,
            ),
            JobSpec(
                name="datajud_processos_licitacao",
                description="Procurement fraud processes (STJ, TRF1-6, all 27 state TJs)",
                domain="processo_judicial",
                enabled=True,
            ),
        ]

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=5, burst=10)

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        """POST to DataJud Elasticsearch and return raw items + next cursor.

        Iterates through tribunals sequentially, advancing to the next tribunal
        when the current one returns an empty page or an unrecoverable error.
        """
        base_query, tribunals = _JOB_CONFIG[job.name]
        tribunal_idx, search_after = _parse_cursor(cursor)

        while tribunal_idx < len(tribunals):
            api_suffix = tribunals[tribunal_idx]
            url = f"/{api_suffix}/_search"

            body: dict = dict(base_query)
            if search_after is not None:
                body = {**body, "search_after": search_after}

            try:
                async with datajud_client() as client:
                    response = await client.post(url, json=body)
                    response.raise_for_status()
                    payload: dict = response.json()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in _SKIP_STATUSES:
                    _log.warning(
                        "datajud.tribunal_skip",
                        tribunal=api_suffix,
                        job=job.name,
                        status=status,
                    )
                    tribunal_idx += 1
                    search_after = None
                    continue
                raise

            hits: list[dict] = payload.get("hits", {}).get("hits", [])

            if not hits:
                # No more results for this tribunal — advance to the next one.
                tribunal_idx += 1
                search_after = None
                continue

            items = [
                RawItem(
                    raw_id=(
                        hit.get("_source", {}).get("numeroProcesso")
                        or f"{api_suffix}:{i}"
                    ),
                    data={
                        **hit.get("_source", {}),
                        "_tribunal_suffix": api_suffix,
                        "_sort": hit.get("sort"),
                    },
                )
                for i, hit in enumerate(hits)
            ]

            last_sort: Optional[list] = hits[-1].get("sort")
            if last_sort:
                next_cursor: Optional[str] = _encode_cursor(tribunal_idx, last_sort)
            else:
                # No sort field in response — can't paginate further; move on.
                next_tribunal = tribunal_idx + 1
                next_cursor = f"{next_tribunal}:" if next_tribunal < len(tribunals) else None

            return items, next_cursor

        return [], None

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        """Map DataJud raw items to CanonicalEvents (no entities — parties are
        not exposed in the basic search endpoint)."""
        events: list[CanonicalEvent] = []

        for item in raw_items:
            d = item.data
            numero_processo: str = d.get("numeroProcesso") or item.raw_id
            classe: dict = d.get("classe") or {}
            assuntos_raw: list[dict] = d.get("assuntos") or []
            assunto_names: list[str] = [
                a["nome"] for a in assuntos_raw if a.get("nome")
            ]
            orgao_julgador: dict = d.get("orgaoJulgador") or {}

            events.append(
                CanonicalEvent(
                    source_connector="datajud",
                    source_id=numero_processo,
                    type="processo_judicial",
                    subtype=assunto_names[0] if assunto_names else "",
                    description=classe.get("nome") or "",
                    occurred_at=_parse_iso_datetime(d.get("dataAjuizamento")),
                    attrs={
                        "tribunal": d.get("tribunal") or "",
                        "orgao_julgador": orgao_julgador.get("nome") or "",
                        "grau": d.get("grau") or "",
                        "assuntos": assunto_names,
                        "numero_processo": numero_processo,
                    },
                )
            )

        return NormalizeResult(events=events)
