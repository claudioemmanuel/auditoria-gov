"""Tests for shared/connectors/receita_cnpj.py.

Coverage targets:
- InsufficientDiskError
- _safe_extractall (Zip Slip protection)
- _ensure_single_file (idempotency, download, disk check, 404, bad ZIP)
- _delete_exhausted_file
- ReceitaCNPJConnector.list_jobs (always enabled, no env var)
- ReceitaCNPJConnector.fetch (lazy download, file deletion, cursor, zero-result, edge cases)
- ReceitaCNPJConnector.normalize / _normalize_* (empresas, socios, estabelecimentos)
- ReceitaCNPJConnector.cleanup_bulk_files
"""

import csv
import io
import os
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import respx
import httpx

from openwatch_connectors.receita_cnpj import (
    InsufficientDiskError,
    ReceitaCNPJConnector,
    _RFB_NEXTCLOUD_BASE,
    _RFB_SHARE_TOKEN,
    _RFB_CNPJ_WEBDAV_PATH,
    _RFB_ZIP_FILES,
    _build_download_url,
    _delete_exhausted_file,
    _discover_latest_month,
    _ensure_single_file,
    _safe_extractall,
)
from openwatch_connectors.base import JobSpec
from openwatch_models.raw import RawItem


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_csv_bytes(rows: list[list[str]], encoding: str = "iso-8859-1") -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode(encoding)


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    path.write_bytes(_make_csv_bytes(rows))


def _make_zip(zip_path: Path, csv_name: str, csv_bytes: bytes) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_name, csv_bytes)


def _empresas_row(
    cnpj_basico: str = "12345678",
    razao: str = "EMPRESA TESTE",
    natureza: str = "2062",
    qualif: str = "49",
    capital: str = "10000,00",
) -> list[str]:
    return [cnpj_basico, razao, natureza, qualif, capital, "01", ""]


def _socios_row(
    cnpj: str = "12345678",
    tipo: str = "2",
    nome: str = "JOAO SILVA",
    doc: str = "***123456**",
    qualif: str = "05",
    data: str = "20100101",
) -> list[str]:
    return [cnpj, tipo, nome, doc, qualif, data]


def _estab_row(
    cnpj_basico: str = "12345678",
    ordem: str = "0001",
    dv: str = "00",
) -> list[str]:
    # Build a row with enough columns (30+) to satisfy all index accesses in
    # _normalize_estabelecimentos. Column indices per Receita Federal layout:
    # 0=cnpj_basico, 1=cnpj_ordem, 2=cnpj_dv, 5=situacao_cadastral, 6=data_situacao,
    # 10=data_abertura, 11=cnae_principal, 13=logradouro, 14=numero, 17=cep,
    # 18=municipio, 19=uf, 20=telefone, 27=email
    row = [""] * 30
    row[0]  = cnpj_basico
    row[1]  = ordem
    row[2]  = dv
    row[5]  = "02"
    row[6]  = "20200101"
    row[10] = "19990301"
    row[11] = "6201500"
    row[13] = "RUA DAS FLORES"
    row[14] = "100"
    row[17] = "01310100"
    row[18] = "SAO PAULO"
    row[19] = "SP"
    row[20] = "11999990000"
    row[27] = "test@test.com"
    return row


# ─── InsufficientDiskError ────────────────────────────────────────────────────

class TestInsufficientDiskError:
    def test_is_runtime_error(self):
        err = InsufficientDiskError("not enough space")
        assert isinstance(err, RuntimeError)
        assert "not enough space" in str(err)


# ─── _safe_extractall ─────────────────────────────────────────────────────────

class TestSafeExtractall:
    def test_normal_extraction(self, tmp_path):
        csv_bytes = b"col1;col2\nval1;val2\n"
        zip_path = tmp_path / "test.zip"
        _make_zip(zip_path, "test.csv", csv_bytes)

        _safe_extractall(str(zip_path), str(tmp_path))

        assert (tmp_path / "test.csv").exists()
        assert (tmp_path / "test.csv").read_bytes() == csv_bytes

    def test_zip_slip_blocked(self, tmp_path):
        """A ZIP containing a path-traversal member must raise ValueError."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../../etc/passwd", "root:x:0:0")

        with pytest.raises(ValueError, match="Zip Slip blocked"):
            _safe_extractall(str(zip_path), str(tmp_path))

    def test_nested_path_inside_dest_allowed(self, tmp_path):
        """A member inside a subdir of dest_dir is fine."""
        zip_path = tmp_path / "ok.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("subdir/file.csv", "data")

        _safe_extractall(str(zip_path), str(tmp_path))
        assert (tmp_path / "subdir" / "file.csv").exists()


# ─── _discover_latest_month ───────────────────────────────────────────────────

class TestDiscoverLatestMonth:
    _WEBDAV_URL = f"{_RFB_NEXTCLOUD_BASE}{_RFB_CNPJ_WEBDAV_PATH}/"

    _PROPFIND_RESPONSE = """<?xml version="1.0"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/public.php/webdav/Dados/Cadastros/CNPJ/</d:href>
  </d:response>
  <d:response>
    <d:href>/public.php/webdav/Dados/Cadastros/CNPJ/2025-12/</d:href>
  </d:response>
  <d:response>
    <d:href>/public.php/webdav/Dados/Cadastros/CNPJ/2026-02/</d:href>
  </d:response>
</d:multistatus>"""

    @pytest.mark.asyncio
    async def test_positive_returns_latest_month(self):
        """Returns the lexicographically latest YYYY-MM from the WebDAV listing."""
        with respx.mock() as mock_http:
            mock_http.route(method="PROPFIND", url=self._WEBDAV_URL).mock(
                return_value=httpx.Response(207, text=self._PROPFIND_RESPONSE)
            )
            result = await _discover_latest_month()

        assert result == "2026-02"

    @pytest.mark.asyncio
    async def test_zero_result_raises_runtime_error(self):
        """Raises RuntimeError when the response contains no YYYY-MM directories."""
        empty_body = '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:"/>'
        with respx.mock() as mock_http:
            mock_http.route(method="PROPFIND", url=self._WEBDAV_URL).mock(
                return_value=httpx.Response(207, text=empty_body)
            )
            with pytest.raises(RuntimeError, match="no CNPJ month directories"):
                await _discover_latest_month()

    @pytest.mark.asyncio
    async def test_non_200_raises(self):
        """A non-success HTTP status propagates as an HTTPStatusError."""
        with respx.mock() as mock_http:
            mock_http.route(method="PROPFIND", url=self._WEBDAV_URL).mock(
                return_value=httpx.Response(503)
            )
            with pytest.raises(httpx.HTTPStatusError):
                await _discover_latest_month()


# ─── _ensure_single_file ──────────────────────────────────────────────────────

class TestEnsureSingleFile:
    @pytest.mark.asyncio
    async def test_idempotent_csv_exists(self, tmp_path):
        """If the CSV already exists, no HTTP request is made."""
        csv_path = tmp_path / "Empresas0.csv"
        csv_path.write_text("existing")

        with respx.mock(assert_all_called=False) as mock_http:
            await _ensure_single_file(str(tmp_path), "Empresas0.zip", "https://dados.rfb.gov.br/CNPJ/Empresas0.zip")

        assert len(mock_http.calls) == 0
        assert csv_path.read_text() == "existing"  # untouched

    @pytest.mark.asyncio
    async def test_raises_insufficient_disk(self, tmp_path):
        """Raises InsufficientDiskError when free space < 2 GB."""
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=500 * 1024 ** 2)  # 500 MB
            with pytest.raises(InsufficientDiskError, match="2 GB"):
                await _ensure_single_file(
                    str(tmp_path), "Empresas0.zip",
                    "https://dados.rfb.gov.br/CNPJ/Empresas0.zip",
                )

    @pytest.mark.asyncio
    async def test_downloads_extracts_deletes_zip(self, tmp_path):
        """Downloads ZIP, extracts CSV, deletes ZIP."""
        csv_bytes = _make_csv_bytes([_empresas_row()])
        zip_path_tmp = tmp_path / "_build.zip"
        _make_zip(zip_path_tmp, "Empresas0.csv", csv_bytes)
        zip_content = zip_path_tmp.read_bytes()

        url = "https://dados.rfb.gov.br/CNPJ/Empresas0.zip"
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock() as mock_http:
                mock_http.get(url).mock(
                    return_value=httpx.Response(200, content=zip_content)
                )
                await _ensure_single_file(str(tmp_path), "Empresas0.zip", url)

        assert (tmp_path / "Empresas0.csv").exists()
        assert not (tmp_path / "Empresas0.zip").exists()

    @pytest.mark.asyncio
    async def test_404_does_not_crash(self, tmp_path):
        """A 404 response logs a warning and returns without raising."""
        url = "https://dados.rfb.gov.br/CNPJ/Empresas9.zip"
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock() as mock_http:
                mock_http.get(url).mock(return_value=httpx.Response(404))
                # Should not raise
                await _ensure_single_file(str(tmp_path), "Empresas9.zip", url)

        assert not (tmp_path / "Empresas9.csv").exists()

    @pytest.mark.asyncio
    async def test_bad_zip_cleans_up(self, tmp_path):
        """A corrupted ZIP is deleted; no CSV left behind."""
        url = "https://dados.rfb.gov.br/CNPJ/Empresas0.zip"
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock() as mock_http:
                mock_http.get(url).mock(
                    return_value=httpx.Response(200, content=b"not-a-zip")
                )
                # Should not raise; bad ZIP is swallowed
                await _ensure_single_file(str(tmp_path), "Empresas0.zip", url)

        assert not (tmp_path / "Empresas0.zip").exists()
        assert not (tmp_path / "Empresas0.csv").exists()

    @pytest.mark.asyncio
    async def test_oserror_removing_zip_after_extraction_is_tolerated(self, tmp_path):
        """If deleting the ZIP after extraction fails, the function completes normally."""
        csv_bytes = _make_csv_bytes([_empresas_row()])
        zip_path_tmp = tmp_path / "_build.zip"
        _make_zip(zip_path_tmp, "Empresas0.csv", csv_bytes)
        zip_content = zip_path_tmp.read_bytes()

        url = "https://dados.rfb.gov.br/CNPJ/Empresas0.zip"
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du, \
             patch("shared.connectors.receita_cnpj.os.remove", side_effect=OSError("busy")):
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock() as mock_http:
                mock_http.get(url).mock(
                    return_value=httpx.Response(200, content=zip_content)
                )
                # Should not raise even if os.remove fails
                await _ensure_single_file(str(tmp_path), "Empresas0.zip", url)

    @pytest.mark.asyncio
    async def test_bad_zip_oserror_on_cleanup_is_tolerated(self, tmp_path):
        """If os.remove fails during bad-zip cleanup, no exception propagates."""
        url = "https://dados.rfb.gov.br/CNPJ/Empresas0.zip"
        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock() as mock_http:
                mock_http.get(url).mock(
                    return_value=httpx.Response(200, content=b"not-a-zip")
                )
                with patch("shared.connectors.receita_cnpj.os.remove", side_effect=OSError("busy")):
                    await _ensure_single_file(str(tmp_path), "Empresas0.zip", url)

    @pytest.mark.asyncio
    async def test_skips_download_if_zip_already_present(self, tmp_path):
        """If the ZIP is already on disk (partial download?), extraction is attempted without re-downloading."""
        csv_bytes = _make_csv_bytes([_empresas_row()])
        zip_path = tmp_path / "Empresas0.zip"
        _make_zip(zip_path, "Empresas0.csv", csv_bytes)

        with patch("shared.connectors.receita_cnpj.shutil.disk_usage") as mock_du:
            mock_du.return_value = MagicMock(free=3 * 1024 ** 3)
            with respx.mock(assert_all_called=False) as mock_http:
                await _ensure_single_file(
                    str(tmp_path), "Empresas0.zip",
                    "https://dados.rfb.gov.br/CNPJ/Empresas0.zip",
                )

        assert len(mock_http.calls) == 0
        assert (tmp_path / "Empresas0.csv").exists()


# ─── _delete_exhausted_file ───────────────────────────────────────────────────

class TestDeleteExhaustedFile:
    def test_deletes_existing_file(self, tmp_path):
        csv_path = tmp_path / "Empresas0.csv"
        csv_path.write_text("data")
        _delete_exhausted_file(str(tmp_path), "Empresas0.csv")
        assert not csv_path.exists()

    def test_silently_ignores_missing_file(self, tmp_path):
        """Should not raise if file is already gone."""
        _delete_exhausted_file(str(tmp_path), "Empresas0.csv")  # no file — no crash


# ─── ReceitaCNPJConnector.list_jobs ───────────────────────────────────────────

class TestListJobs:
    def test_all_three_jobs_enabled_unconditionally(self):
        """No env var needed — jobs must always be enabled."""
        conn = ReceitaCNPJConnector()
        # Ensure the env var is absent
        os.environ.pop("RECEITA_CNPJ_ENABLED", None)

        jobs = conn.list_jobs()

        assert len(jobs) == 3
        names = {j.name for j in jobs}
        assert names == {"rf_empresas", "rf_socios", "rf_estabelecimentos"}
        for job in jobs:
            assert job.enabled is True, f"{job.name} must be enabled"

    def test_enabled_even_when_env_var_false(self):
        """RECEITA_CNPJ_ENABLED env var is no longer respected."""
        os.environ["RECEITA_CNPJ_ENABLED"] = "false"
        try:
            jobs = ReceitaCNPJConnector().list_jobs()
            for job in jobs:
                assert job.enabled is True
        finally:
            del os.environ["RECEITA_CNPJ_ENABLED"]

    def test_supports_incremental_false(self):
        for job in ReceitaCNPJConnector().list_jobs():
            assert job.supports_incremental is False

    def test_domain_is_empresa(self):
        for job in ReceitaCNPJConnector().list_jobs():
            assert job.domain == "empresa"


# ─── ReceitaCNPJConnector.fetch ───────────────────────────────────────────────

class TestFetch:
    def _job(self, name: str = "rf_empresas") -> JobSpec:
        return JobSpec(name=name, description="", domain="empresa", enabled=True)

    @pytest.mark.asyncio
    async def test_zero_result_unknown_job(self, tmp_path):
        """Unknown job name has no prefix → empty file list → ([], None)."""
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_unknown", description="", domain="empresa", enabled=True)

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)):
            items, cursor = await conn.fetch(job)

        assert items == []
        assert cursor is None

    @pytest.mark.asyncio
    async def test_zero_result_file_idx_past_end(self, tmp_path):
        """cursor points beyond available files → ([], None)."""
        conn = ReceitaCNPJConnector()
        job = self._job()
        n = len(_RFB_ZIP_FILES["Empresas"])

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", new_callable=AsyncMock):
            items, cursor = await conn.fetch(job, cursor=f"{n}:0")

        assert items == []
        assert cursor is None

    @pytest.mark.asyncio
    async def test_file_not_found_returns_empty(self, tmp_path):
        """If _ensure_single_file doesn't create the CSV (e.g. 404), fetch returns empty."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        async def noop(*a, **kw):
            pass  # don't create the file

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, cursor = await conn.fetch(job)

        assert items == []
        assert cursor is None

    @pytest.mark.asyncio
    async def test_reads_full_page_and_advances_cursor(self, tmp_path):
        """Reads exactly page_size rows → cursor stays on same file with new offset."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        # Write 10,001 rows so first page (10,000) doesn't exhaust the file
        rows = [_empresas_row(cnpj_basico=str(i).zfill(8)) for i in range(10_001)]
        csv_path = tmp_path / "Empresas0.csv"
        _write_csv(csv_path, rows)

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, cursor = await conn.fetch(job, cursor="0:0")

        assert len(items) == 10_000
        assert cursor is not None
        assert cursor.startswith("0:")
        offset = int(cursor.split(":")[1])
        assert offset > 0
        assert csv_path.exists()  # NOT deleted — file not exhausted

    @pytest.mark.asyncio
    async def test_exhausted_file_deleted_and_cursor_advances(self, tmp_path):
        """When a file is fully consumed (<10,000 rows), it is deleted and cursor moves to next file."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        # 5 rows — well under page_size, so file is exhausted in one call
        rows = [_empresas_row(cnpj_basico=str(i).zfill(8)) for i in range(5)]
        csv_path = tmp_path / "Empresas0.csv"
        _write_csv(csv_path, rows)

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, cursor = await conn.fetch(job, cursor="0:0")

        assert len(items) == 5
        assert not csv_path.exists()  # DELETED after exhaustion
        assert cursor == "1:0"  # advanced to next file

    @pytest.mark.asyncio
    async def test_last_file_exhausted_cursor_is_none(self, tmp_path):
        """When the last file (idx=9) is exhausted, cursor is None (pipeline done)."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        last_idx = len(_RFB_ZIP_FILES["Empresas"]) - 1  # 9
        csv_name = f"Empresas{last_idx}.csv"
        csv_path = tmp_path / csv_name
        _write_csv(csv_path, [_empresas_row()])

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, cursor = await conn.fetch(job, cursor=f"{last_idx}:0")

        assert len(items) == 1
        assert cursor is None
        assert not csv_path.exists()

    @pytest.mark.asyncio
    async def test_cursor_resume_mid_file(self, tmp_path):
        """Providing a non-zero byte_offset causes reading to start from that offset."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        # Write 10 rows
        rows = [_empresas_row(cnpj_basico=str(i).zfill(8)) for i in range(10)]
        csv_path = tmp_path / "Empresas0.csv"
        _write_csv(csv_path, rows)

        # Find offset after first 5 rows using readline (tell() is safe after readline)
        with open(csv_path, "r", encoding="iso-8859-1") as f:
            for _ in range(5):
                f.readline()
            mid_offset = f.tell()

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, cursor = await conn.fetch(job, cursor=f"0:{mid_offset}")

        # Only the last 5 rows should be returned
        assert len(items) == 5

    @pytest.mark.asyncio
    async def test_fetch_calls_ensure_with_correct_url(self, tmp_path):
        """_ensure_single_file is called with the correct zip name and URL."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job("rf_socios")

        csv_path = tmp_path / "Socios3.csv"
        _write_csv(csv_path, [_socios_row()])

        captured: list[tuple] = []

        async def capture(data_dir, zip_name, url):
            captured.append((zip_name, url))

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=capture):
            await conn.fetch(job, cursor="3:0")

        assert len(captured) == 1
        assert captured[0] == ("Socios3.zip", _build_download_url("2026-02", "Socios3.zip"))

    @pytest.mark.asyncio
    async def test_raw_item_ids_are_unique(self, tmp_path):
        """Every RawItem within a page must have a unique raw_id."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        rows = [_empresas_row(cnpj_basico=str(i).zfill(8)) for i in range(100)]
        csv_path = tmp_path / "Empresas0.csv"
        _write_csv(csv_path, rows)

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, _ = await conn.fetch(job, cursor="0:0")

        ids = [item.raw_id for item in items]
        assert len(ids) == len(set(ids)), "raw_ids must be unique"

    @pytest.mark.asyncio
    async def test_raw_item_contains_row_and_file(self, tmp_path):
        """Each RawItem.data has 'row' (list) and 'file' (str) keys."""
        conn = ReceitaCNPJConnector()
        conn._cnpj_month = "2026-02"
        job = self._job()

        _write_csv(tmp_path / "Empresas0.csv", [_empresas_row()])

        async def noop(*a, **kw):
            pass

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("shared.connectors.receita_cnpj._ensure_single_file", side_effect=noop):
            items, _ = await conn.fetch(job, cursor="0:0")

        assert len(items) == 1
        assert "row" in items[0].data
        assert "file" in items[0].data
        assert items[0].data["file"] == "Empresas0.csv"


# ─── _normalize_empresas ──────────────────────────────────────────────────────

class TestNormalizeEmpresas:
    def _items(self, rows: list[list[str]]) -> list[RawItem]:
        return [RawItem(raw_id=f"r{i}", data={"row": r, "file": "Empresas0.csv"}) for i, r in enumerate(rows)]

    def test_positive_private_company(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([_empresas_row()]))
        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.type == "company"
        assert e.name == "EMPRESA TESTE"
        assert e.identifiers["cnpj_basico"] == "12345678"
        assert e.attrs["capital_social"] == 10_000.0

    def test_public_entity_classified_as_org(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        row = _empresas_row(natureza="1015")  # Órgão Público Federal
        result = conn.normalize(job, self._items([row]))
        assert result.entities[0].type == "org"

    def test_short_row_skipped(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([["12345678", "NOME"]]))  # < 5 cols
        assert result.entities == []

    def test_invalid_capital_defaults_to_zero(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        row = _empresas_row(capital="N/A")
        result = conn.normalize(job, self._items([row]))
        assert result.entities[0].attrs["capital_social"] == 0.0

    def test_zero_result_empty_list(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, [])
        assert result.entities == []


# ─── _normalize_socios ────────────────────────────────────────────────────────

class TestNormalizeSocios:
    def _items(self, rows: list[list[str]]) -> list[RawItem]:
        return [RawItem(raw_id=f"r{i}", data={"row": r, "file": "Socios0.csv"}) for i, r in enumerate(rows)]

    def test_positive_pf_partner(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([_socios_row()]))
        assert len(result.entities) == 2  # partner + company
        assert len(result.events) == 1
        event = result.events[0]
        assert event.type == "sociedade"
        assert len(event.participants) == 2
        roles = {p.role for p in event.participants}
        assert roles == {"company", "partner"}

    def test_pj_partner_classified_as_company(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        row = _socios_row(tipo="1", doc="11222333000181")
        result = conn.normalize(job, self._items([row]))
        partner = next(e for e in result.entities if "socio:" in e.source_id)
        assert partner.type == "company"
        assert partner.identifiers.get("cnpj") == "11222333000181"

    def test_pf_with_full_cpf(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        row = _socios_row(tipo="2", doc="12345678901")
        result = conn.normalize(job, self._items([row]))
        partner = next(e for e in result.entities if "socio:" in e.source_id)
        assert partner.identifiers.get("cpf") == "12345678901"

    def test_pf_with_masked_cpf_stored_as_partial(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        row = _socios_row(tipo="2", doc="***123456**")
        result = conn.normalize(job, self._items([row]))
        partner = next(e for e in result.entities if "socio:" in e.source_id)
        assert "cpf_partial" in partner.identifiers

    def test_empty_nome_skipped(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        row = _socios_row(nome="")
        result = conn.normalize(job, self._items([row]))
        assert result.entities == []
        assert result.events == []

    def test_short_row_skipped(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([["12345678", "2", "NOME"]]))  # < 6 cols
        assert result.entities == []

    def test_zero_result_empty_list(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_socios", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, [])
        assert result.entities == []
        assert result.events == []


# ─── _normalize_estabelecimentos ─────────────────────────────────────────────

class TestNormalizeEstabelecimentos:
    def _items(self, rows: list[list[str]]) -> list[RawItem]:
        return [RawItem(raw_id=f"r{i}", data={"row": r, "file": "Estabelecimentos0.csv"}) for i, r in enumerate(rows)]

    def test_positive_full_row(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_estabelecimentos", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([_estab_row()]))
        assert len(result.entities) == 1
        e = result.entities[0]
        assert e.type == "company"
        assert e.identifiers["cnpj"] == "123456780001" + "00"
        assert e.attrs["uf"] == "SP"
        assert e.attrs["municipio"] == "SAO PAULO"
        assert e.attrs["cnae_principal"] == "6201500"

    def test_address_built_correctly(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_estabelecimentos", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([_estab_row()]))
        assert "RUA DAS FLORES" in result.entities[0].attrs["address"]

    def test_empty_logradouro_gives_empty_address(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_estabelecimentos", description="", domain="empresa", enabled=True)
        row = _estab_row()
        row[13] = ""  # logradouro empty
        result = conn.normalize(job, self._items([row]))
        assert result.entities[0].attrs["address"] == ""

    def test_short_row_skipped(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_estabelecimentos", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, self._items([["12345678", "0001"]]))  # < 20 cols
        assert result.entities == []

    def test_zero_result_empty_list(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_estabelecimentos", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, [])
        assert result.entities == []


# ─── normalize dispatch ───────────────────────────────────────────────────────

class TestNormalizeDispatch:
    def test_unknown_job_returns_empty_result(self):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_unknown", description="", domain="empresa", enabled=True)
        result = conn.normalize(job, [])
        assert result.entities == []


# ─── cleanup_bulk_files ───────────────────────────────────────────────────────

class TestCleanupBulkFiles:
    def test_deletes_all_files_in_data_dir(self, tmp_path):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)

        files = ["Empresas0.csv", "Socios0.csv", "leftover.zip"]
        for fname in files:
            (tmp_path / fname).write_text("data")

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)):
            deleted = conn.cleanup_bulk_files(job, object())

        assert deleted == 3
        for fname in files:
            assert not (tmp_path / fname).exists()

    def test_empty_dir_returns_zero(self, tmp_path):
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)):
            deleted = conn.cleanup_bulk_files(job, object())

        assert deleted == 0

    def test_oserror_during_delete_is_tolerated(self, tmp_path):
        """A file that cannot be deleted (e.g. permission error) is skipped gracefully."""
        conn = ReceitaCNPJConnector()
        job = JobSpec(name="rf_empresas", description="", domain="empresa", enabled=True)
        (tmp_path / "stubborn.csv").write_text("data")

        original_remove = os.remove

        def flaky_remove(path):
            if "stubborn" in path:
                raise OSError("permission denied")
            original_remove(path)

        with patch("shared.connectors.receita_cnpj._DATA_DIR", str(tmp_path)), \
             patch("os.remove", side_effect=flaky_remove):
            deleted = conn.cleanup_bulk_files(job, object())

        assert deleted == 0  # failed to delete → not counted


# ─── rate_limit_policy ────────────────────────────────────────────────────────

class TestRateLimitPolicy:
    def test_high_limit_for_local_reads(self):
        policy = ReceitaCNPJConnector().rate_limit_policy()
        assert policy.requests_per_second >= 100


class TestConnectorName:
    def test_name_is_receita_cnpj(self):
        assert ReceitaCNPJConnector().name == "receita_cnpj"
