"""
Docs/code contract checker.

Checks:
1) File path references in docs that do not exist in repo.
2) API endpoint mentions in docs that do not match current FastAPI route map.

Usage:
    venv\\Scripts\\python scripts\\check_docs_contracts.py
    venv\\Scripts\\python scripts\\check_docs_contracts.py --strict
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Iterable, Set

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SRC = ROOT / "src"
DOC_EXTENSIONS = {".md", ".rst"}

PATH_PATTERNS = [
    r"(?:src|config|scripts|tests)/[A-Za-z0-9_./-]+(?:\\.[A-Za-z0-9_+-]+)?",
]

API_PATTERN = re.compile(r"/api/[A-Za-z0-9_/{}/.-]+")
ROUTE_DECORATOR = re.compile(r'@router\.(?:get|post|put|delete|patch)\("([^"]+)"')
INCLUDE_ROUTER = re.compile(r'app\.include_router\([^,]+,\s*prefix="([^"]+)"')


def read_docs_text() -> str:
    chunks: list[str] = []
    for p in DOCS.rglob("*"):
        if p.is_file() and p.suffix.lower() in DOC_EXTENSIONS:
            chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def extract_doc_paths(text: str) -> Set[str]:
    found: Set[str] = set()
    for pat in PATH_PATTERNS:
        found.update(re.findall(pat, text))
    return found


def extract_doc_api_paths(text: str) -> Set[str]:
    return {
        p for p in API_PATTERN.findall(text)
        if not p.endswith(".py")
    }


def normalize_param_path(path: str) -> str:
    # Convert {id} style to generic token for loose comparison.
    return re.sub(r"\{[^}]+\}", "{param}", path)


def get_router_prefixes(main_file: pathlib.Path) -> list[str]:
    text = main_file.read_text(encoding="utf-8", errors="ignore")
    return INCLUDE_ROUTER.findall(text)


def get_route_paths(route_files: Iterable[pathlib.Path]) -> Set[str]:
    paths: Set[str] = set()
    for file in route_files:
        text = file.read_text(encoding="utf-8", errors="ignore")
        for m in ROUTE_DECORATOR.findall(text):
            paths.add(m)
    return paths


def build_api_contract() -> Set[str]:
    prefixes = get_router_prefixes(SRC / "api" / "main.py")
    route_files = (SRC / "api" / "routes").glob("*.py")
    route_paths = get_route_paths(route_files)

    full: Set[str] = set()
    for prefix in prefixes:
        full.add(normalize_param_path(prefix))
        for route in route_paths:
            if route.startswith("/ws"):
                continue
            full.add(normalize_param_path(f"{prefix}{route}"))
    full.add("/api/docs")
    return full


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="return non-zero when mismatches exist")
    args = parser.parse_args()

    docs_text = read_docs_text()

    doc_paths = extract_doc_paths(docs_text)
    missing_paths = sorted({p for p in doc_paths if not (ROOT / p).exists()})

    doc_api = {normalize_param_path(p) for p in extract_doc_api_paths(docs_text)}
    real_api = build_api_contract()
    stale_api = sorted(doc_api - real_api)

    print("== Docs Contract Report ==")
    print(f"Doc path refs: {len(doc_paths)}")
    print(f"Missing file refs: {len(missing_paths)}")
    if missing_paths:
        for p in missing_paths[:50]:
            print(f"  MISSING_PATH: {p}")

    print(f"Doc API refs: {len(doc_api)}")
    print(f"Stale API refs: {len(stale_api)}")
    if stale_api:
        for p in stale_api[:50]:
            print(f"  STALE_API: {p}")

    mismatches = bool(missing_paths or stale_api)
    if args.strict and mismatches:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
