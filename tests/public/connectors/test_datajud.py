"""Tests for DataJud connector — cursor helpers, normalize, fetch."""
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openwatch_connectors.base import JobSpec, RateLimitPolicy
from openwatch_connectors.datajud import (
    DataJudConnector,
    _encode_cursor,
    _parse_cursor,
    _TRIBUNALS_FEDERAL,
    _TRIBUNALS_ESTADUAIS,
    _TRIBUNALS_IMPROBIDADE,
    _TRIBUNALS_LICITACAO,
)
from openwatch_models.raw import RawItem


# ── Connector structure ───────────────────────────────────────────────────────


class TestDataJudConnector:
    def setup_method(self):
        self.c = DataJudConnector()

    def test_name(self):
        assert self.c.name == "datajud"

    def test_has_2_jobs(self):
        assert len(self.c.list_jobs()) == 2

    def test_job_names(self):
        names = {j.name for j in self.c.list_jobs()}
        assert names == {
            "datajud_processos_improbidade",
            "datajud_processos_licitacao",
        }

    def test_all_jobs_enabled(self):
        for job in self.c.list_jobs():
            assert job.enabled is True

    def test_rate_limit_policy(self):
        policy = self.c.rate_limit_policy()
        assert isinstance(policy, RateLimitPolicy)
        assert policy.requests_per_second == 5


# ── Cursor helpers ────────────────────────────────────────────────────────────


class TestDataJudCursorParsing:
    def test_parse_none_cursor(self):
        idx, sort_after = _parse_cursor(None)
        assert idx == 0
        assert sort_after is None

    def test_parse_cursor_no_token(self):
        idx, sort_after = _parse_cursor("3:")
        assert idx == 3
        assert sort_after is None

    def test_parse_cursor_with_token(self):
        sort_values = [1234567890]
        token = base64.b64encode(json.dumps(sort_values).encode()).decode()
        cursor = f"2:{token}"
        idx, sort_after = _parse_cursor(cursor)
        assert idx == 2
        assert sort_after == sort_values

    def test_encode_cursor(self):
        sort_values = [9876543210]
        cursor = _encode_cursor(4, sort_values)
        assert cursor.startswith("4:")
        token = cursor.split(":", 1)[1]
        decoded = json.loads(base64.b64decode(token).decode())
        assert decoded == sort_values

    def test_roundtrip_single_value(self):
        sort_values = [123456789]
        cursor = _encode_cursor(5, sort_values)
        idx, decoded = _parse_cursor(cursor)
        assert idx == 5
        assert decoded == sort_values

    def test_roundtrip_multiple_values(self):
        sort_values = [123, 456, 789]
        cursor = _encode_cursor(0, sort_values)
        idx, decoded = _parse_cursor(cursor)
        assert idx == 0
        assert decoded == sort_values


# ── Tribunal coverage ─────────────────────────────────────────────────────────


class TestDataJudTribunalCoverage:
    def test_improbidade_includes_all_federal_courts(self):
        for t in _TRIBUNALS_FEDERAL:
            assert t in _TRIBUNALS_IMPROBIDADE, f"{t} missing from improbidade list"

    def test_improbidade_includes_all_state_courts(self):
        for t in _TRIBUNALS_ESTADUAIS:
            assert t in _TRIBUNALS_IMPROBIDADE, f"{t} missing from improbidade list"

    def test_licitacao_includes_all_federal_courts(self):
        for t in _TRIBUNALS_FEDERAL:
            assert t in _TRIBUNALS_LICITACAO, f"{t} missing from licitacao list"

    def test_licitacao_includes_all_state_courts(self):
        for t in _TRIBUNALS_ESTADUAIS:
            assert t in _TRIBUNALS_LICITACAO, f"{t} missing from licitacao list"

    def test_federal_list_has_stj_and_all_trfs(self):
        names = set(_TRIBUNALS_FEDERAL)
        assert "api_publica_stj" in names
        assert "api_publica_trf1" in names
        assert "api_publica_trf6" in names

    def test_state_list_covers_all_27_ufs(self):
        # 27 state TJs (26 states + DF)
        assert len(_TRIBUNALS_ESTADUAIS) == 27


# ── Normalize ─────────────────────────────────────────────────────────────────


class TestDataJudNormalize:
    def setup_method(self):
        self.c = DataJudConnector()

    def test_normalize_creates_events(self):
        items = [RawItem(raw_id="1234567-89.2023.1.01.0001", data={
            "numeroProcesso": "1234567-89.2023.1.01.0001",
            "classe": {"nome": "Acao Civil Publica"},
            "assuntos": [{"codigo": 10, "nome": "Improbidade Administrativa"}],
            "orgaoJulgador": {"nome": "1a Vara Federal de Brasilia"},
            "tribunal": "TRF1",
            "dataAjuizamento": "2023-01-15T00:00:00",
            "grau": "G1",
            "_tribunal_suffix": "api_publica_trf1",
        })]
        job = JobSpec(
            name="datajud_processos_improbidade",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)

        assert len(result.events) == 1
        ev = result.events[0]
        assert ev.type == "processo_judicial"
        assert ev.subtype == "Improbidade Administrativa"
        assert ev.attrs["tribunal"] == "TRF1"
        assert ev.attrs["orgao_julgador"] == "1a Vara Federal de Brasilia"
        assert ev.attrs["grau"] == "G1"
        assert ev.description == "Acao Civil Publica"
        assert result.entities == []

    def test_normalize_empty(self):
        job = JobSpec(
            name="datajud_processos_improbidade",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, [])
        assert result.events == []
        assert result.entities == []

    def test_normalize_missing_assuntos_returns_empty_subtype(self):
        items = [RawItem(raw_id="proc-001", data={
            "numeroProcesso": "proc-001",
            "tribunal": "TJSP",
            "grau": "G1",
        })]
        job = JobSpec(
            name="datajud_processos_licitacao",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)
        assert len(result.events) == 1
        assert result.events[0].subtype == ""

    def test_normalize_missing_numero_processo_falls_back_to_raw_id(self):
        items = [RawItem(raw_id="fallback-id", data={"tribunal": "TJMG"})]
        job = JobSpec(
            name="datajud_processos_licitacao",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)
        assert result.events[0].source_id == "fallback-id"

    def test_normalize_multiple_assuntos_uses_first(self):
        items = [RawItem(raw_id="proc-multi", data={
            "numeroProcesso": "proc-multi",
            "assuntos": [
                {"nome": "Improbidade Administrativa"},
                {"nome": "Dano ao Erario"},
            ],
            "tribunal": "STJ",
        })]
        job = JobSpec(
            name="datajud_processos_improbidade",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)
        assert result.events[0].subtype == "Improbidade Administrativa"

    def test_normalize_date_parsing(self):
        items = [RawItem(raw_id="proc-date", data={
            "numeroProcesso": "proc-date",
            "dataAjuizamento": "2022-06-15T00:00:00",
            "tribunal": "TRF2",
        })]
        job = JobSpec(
            name="datajud_processos_improbidade",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)
        ev = result.events[0]
        assert ev.occurred_at is not None
        assert ev.occurred_at.year == 2022
        assert ev.occurred_at.month == 6

    def test_normalize_assuntos_stored_in_attrs(self):
        items = [RawItem(raw_id="proc-attrs", data={
            "numeroProcesso": "proc-attrs",
            "assuntos": [
                {"nome": "Licitacao"},
                {"nome": "Fraude"},
            ],
            "tribunal": "TRF3",
        })]
        job = JobSpec(
            name="datajud_processos_licitacao",
            description="",
            domain="processo_judicial",
        )
        result = self.c.normalize(job, items)
        ev = result.events[0]
        assert "Licitacao" in ev.attrs["assuntos"]
        assert "Fraude" in ev.attrs["assuntos"]


# ── Fetch ─────────────────────────────────────────────────────────────────────


class TestDataJudFetch:
    def setup_method(self):
        self.c = DataJudConnector()

    def _make_mock_client(self, hits):
        payload = {"hits": {"hits": hits}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return mock_client

    @pytest.mark.asyncio
    async def test_fetch_returns_items_and_next_cursor(self):
        hits = [
            {"_source": {"numeroProcesso": "proc-1", "tribunal": "TRF1"}, "sort": [1000]}
        ]
        mock_client = self._make_mock_client(hits)
        with patch("shared.connectors.datajud.datajud_client", return_value=mock_client):
            job = JobSpec(
                name="datajud_processos_improbidade",
                description="",
                domain="processo_judicial",
            )
            items, next_cursor = await self.c.fetch(job)
        assert len(items) == 1
        assert items[0].raw_id == "proc-1"
        assert next_cursor is not None

    @pytest.mark.asyncio
    async def test_fetch_empty_hits_exhausts_all_tribunals(self):
        """Empty hits for every tribunal → returns [], None after exhausting all."""
        payload = {"hits": {"hits": []}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.datajud.datajud_client", return_value=mock_client):
            job = JobSpec(
                name="datajud_processos_improbidade",
                description="",
                domain="processo_judicial",
            )
            # Start at the last tribunal so we only do 1 empty-hit call
            last_idx = len(_TRIBUNALS_IMPROBIDADE) - 1
            items, next_cursor = await self.c.fetch(job, cursor=f"{last_idx}:")
        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_search_after_included_in_body(self):
        """Cursor with sort token → search_after is appended to the ES body."""
        hits = [
            {"_source": {"numeroProcesso": "proc-2", "tribunal": "TRF1"}, "sort": [2000]}
        ]
        mock_client = self._make_mock_client(hits)
        sort_values = [1234567890]
        cursor = _encode_cursor(0, sort_values)
        with patch("shared.connectors.datajud.datajud_client", return_value=mock_client):
            job = JobSpec(
                name="datajud_processos_improbidade",
                description="",
                domain="processo_judicial",
            )
            items, next_cursor = await self.c.fetch(job, cursor=cursor)
        assert len(items) == 1
        call_body = mock_client.post.call_args[1]["json"]
        assert "search_after" in call_body
        assert call_body["search_after"] == sort_values

    @pytest.mark.asyncio
    async def test_fetch_skips_tribunal_on_404(self):
        """HTTP 404 for every tribunal → skip all, return [], None."""
        import httpx

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        err = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )
        mock_client = AsyncMock()
        mock_client.post.side_effect = err
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("shared.connectors.datajud.datajud_client", return_value=mock_client):
            job = JobSpec(
                name="datajud_processos_improbidade",
                description="",
                domain="processo_judicial",
            )
            # Start at last tribunal to only do 1 skipped call
            last_idx = len(_TRIBUNALS_IMPROBIDADE) - 1
            items, next_cursor = await self.c.fetch(job, cursor=f"{last_idx}:")
        assert items == []
        assert next_cursor is None

    @pytest.mark.asyncio
    async def test_fetch_item_raw_id_falls_back_to_index(self):
        """Hit without numeroProcesso uses '{api_suffix}:{i}' as raw_id."""
        hits = [{"_source": {"tribunal": "TRF1"}, "sort": [100]}]
        mock_client = self._make_mock_client(hits)
        with patch("shared.connectors.datajud.datajud_client", return_value=mock_client):
            job = JobSpec(
                name="datajud_processos_improbidade",
                description="",
                domain="processo_judicial",
            )
            items, _ = await self.c.fetch(job, cursor="1:")
        assert items[0].raw_id == "api_publica_trf1:0"

