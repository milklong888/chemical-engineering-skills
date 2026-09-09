# -*- coding: utf-8 -*-
"""Build a local vector index for the Aspen Plus V10 user-guide graph.

The index is intentionally local and deterministic. It uses signed hashing over
mixed Chinese/English character n-grams and tokens, then L2-normalizes dense
float32 vectors. No network access, model download, or API key is required.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Iterable

import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "knowledge_graph"
DETAIL_RECORDS_PATH = GRAPH_DIR / "operation_detail_records.json"
MANIFEST_PATH = ROOT / "manifest.json"
VECTOR_DIR = ROOT / "vector_index"
RECORDS_JSONL = VECTOR_DIR / "records.jsonl"
VECTORS_NPY = VECTOR_DIR / "vectors.npy"
CONFIG_PATH = VECTOR_DIR / "vector_index_config.json"
README_PATH = VECTOR_DIR / "README.md"

DIM = 768
CHAR_NGRAM_RANGE = (2, 5)
TOKEN_NGRAM_RANGE = (1, 3)
GENERATED_MARKER = "<!-- generated: aspen_user_guide_v10_vector_index -->"
CODEX_SKILLS = Path(r"{CHEM_SKILLS}")
V14_MANUAL_GRAPH = CODEX_SKILLS / "aspen-plus-operations" / "references" / "manual_knowledge_graph.json"


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def assert_output_guard() -> None:
    root_resolved = ROOT.resolve()
    vector_resolved = VECTOR_DIR.resolve()
    skills_resolved = CODEX_SKILLS.resolve()
    if not str(vector_resolved).startswith(str(root_resolved)):
        raise RuntimeError(f"Refusing to write vector index outside V10 graph root: {vector_resolved}")
    if str(vector_resolved).startswith(str(skills_resolved)):
        raise RuntimeError(f"Refusing to write vector index inside Codex skills: {vector_resolved}")
    for path in [RECORDS_JSONL, VECTORS_NPY, CONFIG_PATH, README_PATH]:
        resolved = path.resolve()
        if not str(resolved).startswith(str(vector_resolved)):
            raise RuntimeError(f"Refusing unexpected output path: {resolved}")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def tokenise(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{0,32}|[0-9]+(?:\.[0-9]+)?|[\u4e00-\u9fff]{1,6}", text)


def char_ngrams(text: str, min_n: int, max_n: int) -> Iterable[str]:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return
    for n in range(min_n, max_n + 1):
        if len(compact) < n:
            continue
        for i in range(0, len(compact) - n + 1):
            yield compact[i : i + n]


def token_ngrams(tokens: list[str], min_n: int, max_n: int) -> Iterable[str]:
    for n in range(min_n, max_n + 1):
        if len(tokens) < n:
            continue
        for i in range(0, len(tokens) - n + 1):
            yield " ".join(tokens[i : i + n])


def hashed_add(vector: np.ndarray, feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8", errors="ignore"), digest_size=8).digest()
    raw = int.from_bytes(digest, "little", signed=False)
    idx = raw % vector.shape[0]
    sign = 1.0 if ((raw >> 63) & 1) == 0 else -1.0
    vector[idx] += sign * weight


def vectorize_text(text: str, dim: int = DIM) -> np.ndarray:
    norm = normalize_text(text)
    vector = np.zeros(dim, dtype=np.float32)
    tokens = tokenise(norm)

    for gram in char_ngrams(norm, *CHAR_NGRAM_RANGE):
        hashed_add(vector, "c:" + gram, 1.0)
    for gram in token_ngrams(tokens, *TOKEN_NGRAM_RANGE):
        hashed_add(vector, "t:" + gram, 1.8)
    for token in tokens:
        if len(token) >= 2:
            hashed_add(vector, "k:" + token, 2.2)

    length = float(np.linalg.norm(vector))
    if length > 0:
        vector /= length
    return vector


def compact_text(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def is_low_value_detail(detail: dict) -> bool:
    if "page-source-fallback" in detail.get("kind", []):
        return False
    text = normalize_text(detail.get("text", ""))
    title = normalize_text(detail.get("chapter_title", ""))
    if not text:
        return True
    if title and text.replace(" ", "") == title.replace(" ", ""):
        return True
    if re.fullmatch(r"第\s*\d+\s*章.*", text) and len(text) < 80:
        return True
    if len(text) < 8 and not re.search(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", text):
        return True
    return False


def document_text(record: dict) -> str:
    parts = [
        record.get("node_id", ""),
        record.get("scope", ""),
        record.get("title", ""),
        " ".join(record.get("routes", [])),
        " ".join(record.get("kind", [])),
        " ".join(record.get("keywords", [])),
        record.get("text", ""),
    ]
    return "\n".join(str(part) for part in parts if part)


def build_documents() -> list[dict]:
    manifest = read_json(MANIFEST_PATH)
    detail_records = read_json(DETAIL_RECORDS_PATH)

    docs: list[dict] = []

    for chapter in manifest["chapters"]:
        text = "\n".join(
            [
                chapter["node_id"],
                chapter["title"],
                " ".join(chapter.get("routes", [])),
                " ".join(chapter.get("triggers", [])),
                " ".join(chapter.get("headings", [])),
            ]
        )
        docs.append(
            {
                "vector_id": chapter["node_id"],
                "node_id": chapter["node_id"],
                "scope": "chapter",
                "title": chapter["title"],
                "page": f"{chapter['start_page']}-{chapter['end_page']}",
                "routes": chapter.get("routes", []),
                "kind": ["chapter"],
                "keywords": chapter.get("triggers", []) + chapter.get("headings", [])[:16],
                "text": compact_text(text, 1200),
                "source": chapter["node_file"],
                "extract": chapter["extract_file"],
            }
    )

    for detail in detail_records:
        scope = "page-fallback" if "page-source-fallback" in detail.get("kind", []) else "detail"
        docs.append(
            {
                "vector_id": detail["node_id"],
                "node_id": detail["node_id"],
                "chapter_node_id": detail.get("chapter_node_id", ""),
                "scope": scope,
                "title": detail.get("chapter_title", ""),
                "page": detail.get("page", ""),
                "routes": detail.get("routes", []),
                "kind": detail.get("kind", []),
                "keywords": detail.get("keywords", []),
                "text": compact_text(detail.get("text", ""), 1600 if scope == "page-fallback" else 900),
                "source": detail.get("detail_index", ""),
                "extract": detail.get("source_extract", ""),
            }
        )

    seen: set[str] = set()
    deduped: list[dict] = []
    for doc in docs:
        vector_id = doc["vector_id"]
        if vector_id in seen:
            raise RuntimeError(f"duplicate vector_id: {vector_id}")
        seen.add(vector_id)
        deduped.append(doc)
    return deduped


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_readme(config: dict) -> None:
    text = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Vector Index

This directory stores a deterministic local vector index for the user-guide
knowledge graph.

## Files

- `records.jsonl`: vector metadata and short text for each indexed node.
- `vectors.npy`: L2-normalized float32 dense vectors.
- `vector_index_config.json`: build metadata, source hashes, and vectorizer settings.

## Coverage

- Total vectors: {config['record_count']}
- Vector dimension: {config['dimension']}
- Chapter vectors: {config['scope_counts'].get('chapter', 0)}
- Detail operation vectors: {config['scope_counts'].get('detail', 0)}
- Page fallback vectors: {config['scope_counts'].get('page-fallback', 0)}

## Query

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_vectors.py <terms>
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_vectors.py <terms> --scope detail --limit 8
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_vectors.py <terms> --json
```

## Boundary

This vector index is retrieval support. It does not change source authority:
project ledgers decide project values; the V14 help graph remains the
field-level card-rule authority; this V10 graph supplies workflow and operation
context.

## V14 Operation Preservation Guard

This V10 vector index never writes to `.codex/skills` and never rewrites the
V14 operation graph. Keep
`{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json`
as the field-level card authority.
"""
    README_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    assert_output_guard()
    if not MANIFEST_PATH.exists():
        print(f"Missing manifest: {MANIFEST_PATH}", file=sys.stderr)
        return 2
    if not DETAIL_RECORDS_PATH.exists():
        print(f"Missing detail records: {DETAIL_RECORDS_PATH}", file=sys.stderr)
        return 2

    docs = build_documents()
    vectors = np.vstack([vectorize_text(document_text(doc)) for doc in docs]).astype(np.float32)

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(RECORDS_JSONL, docs)
    np.save(VECTORS_NPY, vectors)

    scope_counts: dict[str, int] = {}
    for doc in docs:
        scope_counts[doc["scope"]] = scope_counts.get(doc["scope"], 0) + 1

    config = {
        "name": "aspen_user_guide_v10_vector_index",
        "source_graph": "aspen_user_guide_v10_knowledge",
        "dimension": DIM,
        "char_ngram_range": list(CHAR_NGRAM_RANGE),
        "token_ngram_range": list(TOKEN_NGRAM_RANGE),
        "record_count": len(docs),
        "scope_counts": scope_counts,
        "records_jsonl": "records.jsonl",
        "vectors_npy": "vectors.npy",
        "vectorizer": "signed_hashing_char_token_ngrams_v1",
        "manifest_sha256": sha256(MANIFEST_PATH),
        "detail_records_sha256": sha256(DETAIL_RECORDS_PATH),
        "read_only_v14_manual_graph": True,
        "v14_manual_graph_path": str(V14_MANUAL_GRAPH),
        "v14_manual_graph_sha256": sha256(V14_MANUAL_GRAPH) if V14_MANUAL_GRAPH.exists() else None,
    }
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(config)

    print(f"Vectorized {len(docs)} records into {vectors.shape[1]} dimensions.")
    print(f"Vector directory: {VECTOR_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
