#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
"""
Boundary enforcement tool for the OpenWatch open-core split.

This script validates that files designated as PUBLIC do not import
from modules designated as PROTECTED CORE. Run this before publishing
the public repo, and in CI to prevent regressions.

Usage:
    python tools/check_boundaries.py [--strict]

Exit codes:
    0 — No violations found
    1 — Violations found (or --strict and warnings exist)
"""

import ast
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Classification: workspace package modules that must NEVER be imported from
# the public layer. These live in openwatch-core (private, BSL 1.1).
# ---------------------------------------------------------------------------
PROTECTED_MODULES: list[str] = [
    "openwatch_typologies",
    "openwatch_analytics",
    "openwatch_er",
    "openwatch_ai",
    "openwatch_baselines",
    "openwatch_services",
    "openwatch_pipelines",
    "openwatch_scheduler",
    "openwatch_queries",
    "openwatch_db",  # sync/async engine + upsert helpers — private ORM access
]

# Protected connector modules: gov API enrichment implementations live in
# openwatch-core. The public layer keeps only the generic transport helpers
# (http_client, domain_guard, base) shipped with openwatch_connectors.
PROTECTED_CONNECTORS: list[str] = [
    "openwatch_connectors.anvisa_bps",
    "openwatch_connectors.bacen",
    "openwatch_connectors.bndes",
    "openwatch_connectors.camara",
    "openwatch_connectors.datajud",
    "openwatch_connectors.jurisprudencia",
    "openwatch_connectors.orcamento_bim",
    "openwatch_connectors.querido_diario",
    "openwatch_connectors.receita_cnpj",
    "openwatch_connectors.senado",
    "openwatch_connectors.tce_pe",
    "openwatch_connectors.tce_rj",
    "openwatch_connectors.tce_rs",
    "openwatch_connectors.tce_sp",
    "openwatch_connectors.tcu",
    "openwatch_connectors.transferegov",
    "openwatch_connectors.tse",
    "openwatch_connectors.veracity",
]

ALL_PROTECTED = PROTECTED_MODULES + PROTECTED_CONNECTORS

# ---------------------------------------------------------------------------
# Files/directories that represent the PUBLIC layer.
# These are the only files in the public repo post-split.
# ---------------------------------------------------------------------------
PUBLIC_PATHS: list[str] = [
    "apps/web/src",
    "packages/sdk",
    "packages/ui",
    "packages/utils",
    "packages/config",
    "packages/models/openwatch_models",
    # Generic transport helpers only; per-connector implementations
    # belong in openwatch-core.
    "packages/connectors/openwatch_connectors/domain_guard.py",
    "packages/connectors/openwatch_connectors/http_client.py",
    # Public API surface (thin gateway that proxies to openwatch-core).
    "api/app/routers/public.py",
    "api/app/routers/internal.py",  # operator endpoints that proxy to core
    "api/app/main.py",
    "api/app/deps.py",
    "api/app/db.py",
    "api/app/adapters",
    "api/app/middleware",
    "api/core_client.py",
]


def collect_python_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in paths:
        p = ROOT / rel
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            files.extend(p.rglob("*.py"))
    return files


def extract_imports(file: Path) -> list[tuple[int, str]]:
    """Return (line_no, module_name) for all imports in a Python file."""
    try:
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    except SyntaxError:
        return []

    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))
    return imports


def check_violations(strict: bool = False) -> int:
    files = collect_python_files(PUBLIC_PATHS)
    violations: list[str] = []
    warnings: list[str] = []

    for file in files:
        rel_path = file.relative_to(ROOT)
        for line_no, module in extract_imports(file):
            for protected in ALL_PROTECTED:
                if module == protected or module.startswith(protected + "."):
                    msg = f"  {rel_path}:{line_no}  imports  {module!r}"
                    if protected in PROTECTED_MODULES:
                        violations.append(msg)
                    else:
                        warnings.append(msg)

    if violations:
        print(f"\n🔴 BOUNDARY VIOLATIONS ({len(violations)}) — public files importing PROTECTED modules:\n")
        for v in violations:
            print(v)

    if warnings:
        print(f"\n🟡 BOUNDARY WARNINGS ({len(warnings)}) — public files importing PROTECTED connectors:\n")
        for w in warnings:
            print(w)

    if not violations and not warnings:
        print("✅ No boundary violations found. Public layer is clean.")
        return 0

    if violations:
        print(
            "\n❌ Fix violations before publishing the public repo."
            "\n   Replace direct imports with calls to core_client.py (API gateway pattern)."
        )
        return 1

    if warnings and strict:
        print("\n❌ Warnings treated as errors in --strict mode.")
        return 1

    if warnings:
        print("\n⚠️  Warnings found. These connectors should not be imported in the public layer post-split.")
        return 0

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenWatch boundary enforcement check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat connector warnings as errors",
    )
    parser.add_argument(
        "--list-protected",
        action="store_true",
        help="Print the full list of protected modules and exit",
    )
    args = parser.parse_args()

    if args.list_protected:
        print("Protected modules (NEVER import from public layer):\n")
        for m in ALL_PROTECTED:
            print(f"  {m}")
        sys.exit(0)

    print("OpenWatch Boundary Checker")
    print("=" * 50)
    print(f"Checking {len(collect_python_files(PUBLIC_PATHS))} public Python files...")
    sys.exit(check_violations(strict=args.strict))


if __name__ == "__main__":
    main()
