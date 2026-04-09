"""Regression tests that lock in the post-`shared/` open-core boundary."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_shared_directory():
    assert not (ROOT / "shared").exists()


def test_no_alembic_directory():
    assert not (ROOT / "api" / "alembic").exists()
    assert not (ROOT / "api" / "alembic.ini").exists()


def test_no_shared_imports_in_public_tree():
    hits: list[str] = []
    for py in ROOT.rglob("*.py"):
        rel = py.relative_to(ROOT)
        if rel.parts[0] in {".venv", "node_modules"}:
            continue
        for line_no, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            stripped = line.lstrip()
            if stripped.startswith(("from shared.", "import shared.")):
                hits.append(f"{rel}:{line_no}: {stripped}")
    assert not hits, "stale shared.* imports:\n" + "\n".join(hits)
