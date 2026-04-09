"""Regression tests for the open-core boundary.

Locks in the post-cleanup invariants so that future changes cannot
silently reintroduce the dead `shared/` tree or start importing
private workspace packages from the public API.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_shared_directory():
    """shared/ was deleted in Phase 3 of the open-core cleanup.

    If this file is back, someone reintroduced pre-split dead code.
    """
    assert not (ROOT / "shared").exists(), (
        "openwatch/shared/ should not exist post-cleanup. "
        "See .omc/plans/openwatch-open-core-cleanup.md (Phase 3)."
    )


def test_no_alembic_directory():
    """alembic/ was deleted in Phase 4 — schema ownership is openwatch-core.

    See docs/ARCHITECTURE.md: 'Schema migrations are managed by Alembic in openwatch-core'.
    """
    assert not (ROOT / "api" / "alembic").exists(), (
        "openwatch/api/alembic/ should not exist post-cleanup. "
        "Public API is a thin proxy; schema migrations live in openwatch-core."
    )
    assert not (ROOT / "api" / "alembic.ini").exists(), (
        "openwatch/api/alembic.ini should not exist post-cleanup."
    )


def test_boundary_check_strict_passes():
    """tools/check_boundaries.py --strict must exit 0."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "check_boundaries.py"), "--strict"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        f"check_boundaries --strict failed with exit {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_no_shared_imports_in_public_api():
    """No .py file outside the (non-existent) shared/ may still import shared.*"""
    api = ROOT / "api"
    packages = ROOT / "packages"
    tests_public = ROOT / "tests" / "public"
    hits: list[str] = []
    for base in (api, packages, tests_public):
        if not base.exists():
            continue
        for py in base.rglob("*.py"):
            src = py.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(src.splitlines(), start=1):
                stripped = line.lstrip()
                if stripped.startswith(("from shared.", "import shared.")):
                    hits.append(f"{py.relative_to(ROOT)}:{line_no}: {stripped}")
    assert not hits, "Found stale shared.* imports:\n" + "\n".join(hits)
