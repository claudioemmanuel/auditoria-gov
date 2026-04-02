"""Connector for TCE-PE — Tribunal de Contas do Estado de Pernambuco."""

import json
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.connectors.base import BaseConnector, JobSpec, RateLimitPolicy
from shared.connectors.http_client import tce_pe_client
from shared.models.canonical import (
    CanonicalEntity,
    CanonicalEvent,
    CanonicalEventParticipant,
    NormalizeResult,
)
from shared.models.raw import RawItem

_MIN_YEAR_OFFSET = 5


def _clean(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _digits(value: object) -> str:
    if value is None:
        return ""
    return re.sub(r"\D+", "", str(value))


def _slug(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_-]+", "_", value).strip("_")
    return slug or "na"


def _parse_brl_value(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if "," in text:
        normalized = text.replace(".", "").replace(",", ".")
    else:
        normalized = text
    try:
        return float(normalized)
    except ValueError:
        compact = text.replace(".", "")
        try:
            return float(compact)
        except ValueError:
            return None


def _parse_any_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in (
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d",
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


def _decode_tce_pe_json(response: httpx.Response) -> dict:
    """Decode TCE-PE payloads that frequently arrive in ISO-8859-1."""
    try:
        body = response.json()
        if isinstance(body, dict):
            return body
    except ValueError:
        pass

    try:
        return json.loads(response.content.decode("iso-8859-1"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            body = json.loads(response.text)
            return body if isinstance(body, dict) else {}
        except json.JSONDecodeError:
            return {}


def _current_year() -> int:
    return datetime.now(timezone.utc).year


def _parse_cursor(cursor: Optional[str]) -> int:
    if cursor is None:
        return _current_year()
    try:
        return int(cursor)
    except ValueError:
        return _current_year()


def _next_cursor(year: int) -> Optional[str]:
    previous_year = year - 1
    if previous_year < _current_year() - _MIN_YEAR_OFFSET:
        return None
    return str(previous_year)


def _stable_key(record: dict, fields: list[str], fallback: str) -> str:
    for field in fields:
        value = _clean(record.get(field))
        if value:
            return _slug(value)
    return _slug(fallback)


def _build_document_entity(
    source_connector: str,
    cpf_cnpj: object,
    *,
    name_hint: Optional[str] = None,
) -> Optional[CanonicalEntity]:
    doc = _digits(cpf_cnpj)
    if len(doc) == 14:
        return CanonicalEntity(
            source_connector=source_connector,
            source_id=f"cnpj:{doc}",
            type="company",
            name=name_hint or "Empresa não identificada",
            identifiers={"cnpj": doc},
        )
    if len(doc) == 11:
        return CanonicalEntity(
            source_connector=source_connector,
            source_id=f"cpf:{doc}",
            type="person",
            name=name_hint or "Pessoa não identificada",
            identifiers={"cpf": doc},
        )
    return None


def _build_org_entity(
    source_connector: str,
    label: str,
    value: Optional[str],
) -> Optional[CanonicalEntity]:
    cleaned = _clean(value)
    if not cleaned:
        return None
    return CanonicalEntity(
        source_connector=source_connector,
        source_id=f"{label}:{_slug(cleaned)}",
        type="org",
        name=cleaned,
        identifiers={label: cleaned},
    )


class TCEPEConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "tce_pe"

    def list_jobs(self) -> list[JobSpec]:
        return [
            JobSpec(
                name="tce_pe_licitacoes",
                description="Licitações de unidades gestoras no TCE-PE",
                domain="licitacao",
                enabled=True,
            ),
            JobSpec(
                name="tce_pe_contratos",
                description="Contratos públicos no TCE-PE",
                domain="contrato",
                enabled=True,
            ),
            JobSpec(
                name="tce_pe_despesas",
                description="Despesas municipais no TCE-PE",
                domain="despesa_municipal",
                enabled=True,
            ),
        ]

    async def fetch(
        self,
        job: JobSpec,
        cursor: Optional[str] = None,
        params: Optional[dict] = None,
    ) -> tuple[list[RawItem], Optional[str]]:
        year = _parse_cursor(cursor)
        if year < _current_year() - _MIN_YEAR_OFFSET:
            return [], None

        if job.name == "tce_pe_licitacoes":
            entity = "LicitacaoUG"
            year_param = "ANOLICITACAO"
            id_fields = ["IDLICITACAOUG", "IDLICITACAO", "NUMEROLICITACAO", "NUMEROPROCESSO"]
        elif job.name == "tce_pe_contratos":
            entity = "Contratos"
            year_param = "ANOREFERENCIA"
            id_fields = ["IDCONTRATO", "NUMEROCONTRATO", "NUMEROPROCESSO"]
        elif job.name == "tce_pe_despesas":
            entity = "DespesasMunicipais"
            year_param = "ANOREFERENCIA"
            id_fields = ["IDDESPESA", "NUMEMPENHO", "NUMDOCUMENTO"]
        else:
            raise ValueError(f"Unknown TCE-PE job: {job.name}")

        query: dict[str, object] = {year_param: year}
        if params:
            query.update(params)
            query[year_param] = year

        async with tce_pe_client() as client:
            response = await client.get(f"/{entity}!json", params=query)
            response.raise_for_status()
            payload = _decode_tce_pe_json(response)

        resposta = payload.get("resposta", {}) if isinstance(payload, dict) else {}
        conteudo = resposta.get("conteudo", [])
        records = conteudo if isinstance(conteudo, list) else []

        seen: dict[str, int] = {}
        raw_items: list[RawItem] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            stable_key = _stable_key(record, id_fields, str(index))
            duplicate_count = seen.get(stable_key, 0)
            seen[stable_key] = duplicate_count + 1
            unique_key = stable_key if duplicate_count == 0 else f"{stable_key}_{duplicate_count}"
            raw_items.append(
                RawItem(
                    raw_id=f"{job.name}:{year}:{unique_key}",
                    data=record,
                )
            )

        return raw_items, _next_cursor(year)

    def normalize(
        self,
        job: JobSpec,
        raw_items: list[RawItem],
        params: Optional[dict] = None,
    ) -> NormalizeResult:
        if job.name == "tce_pe_licitacoes":
            return self._normalize_licitacoes(raw_items)
        if job.name == "tce_pe_contratos":
            return self._normalize_contratos(raw_items)
        if job.name == "tce_pe_despesas":
            return self._normalize_despesas(raw_items)
        raise ValueError(f"Unknown TCE-PE job: {job.name}")

    def _normalize_licitacoes(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            data = item.data
            participants: list[CanonicalEventParticipant] = []

            ug_entity = _build_org_entity("tce_pe", "ug", _clean(data.get("NOMEUNIDADEGESTORA")))
            if ug_entity:
                entities.append(ug_entity)
                participants.append(CanonicalEventParticipant(entity_ref=ug_entity, role="procuring_entity"))

            municipio_entity = _build_org_entity("tce_pe", "municipio", _clean(data.get("MUNICIPIO")))
            if municipio_entity:
                entities.append(municipio_entity)
                participants.append(CanonicalEventParticipant(entity_ref=municipio_entity, role="jurisdiction"))

            doc_entity = _build_document_entity(
                "tce_pe",
                data.get("CPFCNPJ") or data.get("CPF_CNPJ"),
                name_hint=_clean(data.get("NOMEFORNECEDOR")) or _clean(data.get("RAZAOSOCIAL")),
            )
            if doc_entity:
                entities.append(doc_entity)
                participants.append(CanonicalEventParticipant(entity_ref=doc_entity, role="supplier"))

            value = (
                _parse_brl_value(data.get("VALORLICITACAO"))
                or _parse_brl_value(data.get("VALORESTIMADO"))
                or _parse_brl_value(data.get("VALOR"))
            )
            event = CanonicalEvent(
                source_connector="tce_pe",
                source_id=item.raw_id,
                type="procurement",
                subtype="licitacao",
                description=_clean(data.get("OBJETOLICITACAO")) or _clean(data.get("OBJETO")),
                occurred_at=_parse_any_datetime(
                    data.get("DATALICITACAO")
                    or data.get("DATAABERTURA")
                    or data.get("DATAHOMOLOGACAO")
                ),
                value_brl=value,
                attrs={
                    "ano_licitacao": _clean(data.get("ANOLICITACAO")),
                    "numero_licitacao": _clean(data.get("NUMEROLICITACAO")),
                    "numero_processo": _clean(data.get("NUMEROPROCESSO")),
                    "modalidade": _clean(data.get("MODALIDADE")),
                    "municipio": _clean(data.get("MUNICIPIO")),
                    "nome_unidade_gestora": _clean(data.get("NOMEUNIDADEGESTORA")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_contratos(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            data = item.data
            participants: list[CanonicalEventParticipant] = []

            ug_entity = _build_org_entity("tce_pe", "ug", _clean(data.get("NOMEUNIDADEGESTORA")))
            if ug_entity:
                entities.append(ug_entity)
                participants.append(CanonicalEventParticipant(entity_ref=ug_entity, role="buyer"))

            municipio_entity = _build_org_entity("tce_pe", "municipio", _clean(data.get("MUNICIPIO")))
            if municipio_entity:
                entities.append(municipio_entity)
                participants.append(CanonicalEventParticipant(entity_ref=municipio_entity, role="jurisdiction"))

            contractor_entity = _build_document_entity(
                "tce_pe",
                data.get("CPFCNPJ") or data.get("CPF_CNPJ"),
                name_hint=_clean(data.get("NOMECONTRATADO")) or _clean(data.get("RAZAOSOCIAL")),
            )
            if contractor_entity:
                entities.append(contractor_entity)
                participants.append(CanonicalEventParticipant(entity_ref=contractor_entity, role="supplier"))

            value = (
                _parse_brl_value(data.get("VALORCONTRATO"))
                or _parse_brl_value(data.get("VALORGLOBAL"))
                or _parse_brl_value(data.get("VALOR"))
            )
            event = CanonicalEvent(
                source_connector="tce_pe",
                source_id=item.raw_id,
                type="contract",
                subtype="public_contract",
                description=_clean(data.get("OBJETOCONTRATO")) or _clean(data.get("OBJETO")),
                occurred_at=_parse_any_datetime(
                    data.get("DATAASSINATURA")
                    or data.get("DATAINICIO")
                    or data.get("DATACONTRATO")
                ),
                value_brl=value,
                attrs={
                    "ano_referencia": _clean(data.get("ANOREFERENCIA")),
                    "numero_contrato": _clean(data.get("NUMEROCONTRATO")),
                    "numero_processo": _clean(data.get("NUMEROPROCESSO")),
                    "municipio": _clean(data.get("MUNICIPIO")),
                    "nome_unidade_gestora": _clean(data.get("NOMEUNIDADEGESTORA")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def _normalize_despesas(self, raw_items: list[RawItem]) -> NormalizeResult:
        entities: list[CanonicalEntity] = []
        events: list[CanonicalEvent] = []

        for item in raw_items:
            data = item.data
            participants: list[CanonicalEventParticipant] = []

            ug_entity = _build_org_entity("tce_pe", "ug", _clean(data.get("NOMEUNIDADEGESTORA")))
            if ug_entity:
                entities.append(ug_entity)
                participants.append(
                    CanonicalEventParticipant(entity_ref=ug_entity, role="responsible_entity")
                )

            municipio_entity = _build_org_entity("tce_pe", "municipio", _clean(data.get("MUNICIPIO")))
            if municipio_entity:
                entities.append(municipio_entity)
                participants.append(CanonicalEventParticipant(entity_ref=municipio_entity, role="municipality"))

            beneficiary_entity = _build_document_entity(
                "tce_pe",
                data.get("CPF_CNPJ") or data.get("CPFCNPJ"),
                name_hint=_clean(data.get("NOMEFAVORECIDO")) or _clean(data.get("RAZAOSOCIAL")),
            )
            if beneficiary_entity:
                entities.append(beneficiary_entity)
                participants.append(CanonicalEventParticipant(entity_ref=beneficiary_entity, role="payee"))

            value = (
                _parse_brl_value(data.get("VALORPAGO"))
                or _parse_brl_value(data.get("VALOREMPENHADO"))
                or _parse_brl_value(data.get("VALORDESPESA"))
                or _parse_brl_value(data.get("VALOR"))
            )
            event = CanonicalEvent(
                source_connector="tce_pe",
                source_id=item.raw_id,
                type="spending",
                subtype="municipal_expense",
                description=_clean(data.get("OBJETODESPESA")) or _clean(data.get("HISTORICO")),
                occurred_at=_parse_any_datetime(
                    data.get("DATAEMPENHO")
                    or data.get("DATAPAGAMENTO")
                    or data.get("DATADESPESA")
                ),
                value_brl=value,
                attrs={
                    "ano_referencia": _clean(data.get("ANOREFERENCIA")),
                    "numero_empenho": _clean(data.get("NUMEMPENHO")),
                    "municipio": _clean(data.get("MUNICIPIO")),
                    "nome_unidade_gestora": _clean(data.get("NOMEUNIDADEGESTORA")),
                },
                participants=participants,
            )
            events.append(event)

        return NormalizeResult(entities=entities, events=events)

    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(requests_per_second=1, burst=1)
