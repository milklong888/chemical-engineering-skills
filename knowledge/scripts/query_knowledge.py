"""Read-only offline lookup over preserved original knowledge records.

The lexical scorer is the retained Aspen V10 query implementation; this adapter
adds source identity checks, corpus selection, and abstraction-layer ordering.
It does not load the original workspace, PDFs, cloud APIs, or project overlays.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CORPORA = ("chemical_principles", "sun_lanyi", "aspen_v10")
ALIASES = {
    "公用工程": ["热量", "utility"], "预热": ["换热", "heat"],
    "压缩": ["压缩机", "压力", "compressor"], "换热器": ["换热", "heatx"],
    "流程": ["系统", "flowsheet"], "合理": ["设计", "边界"],
    "收敛": ["convergence"], "精馏": ["distillation", "radfrac"],
    "物料衡算": ["守恒", "balance"], "热泵": ["压缩", "热量"],
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.is_relative_to(root.resolve()):
        raise ValueError("Knowledge path escapes package: " + relative)
    return path


def load_records(root: Path = ROOT) -> tuple[dict, list[dict]]:
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "chemical-offline-knowledge-manifest-v1":
        raise ValueError("Unsupported knowledge manifest schema")
    entries = {item["path"]: item for item in manifest["files"]}
    for relative in ("records.jsonl", "aspen_v10/scripts/query_user_guide_knowledge.py"):
        path = checked_path(root, relative)
        if relative not in entries or sha256(path.read_bytes()) != entries[relative]["sha256"]:
            raise ValueError("Knowledge content identity mismatch: " + relative)
    records = [json.loads(line) for line in (root / "records.jsonl").read_text(encoding="utf-8").splitlines() if line]
    seen, verified_payloads = set(), set()
    for record in records:
        identity = record["corpus"], record["node_id"]
        if identity in seen or record["corpus"] not in CORPORA:
            raise ValueError("Duplicate or invalid knowledge identity")
        seen.add(identity)
        if record.get("authority_scope") != "shared" or record.get("project_value_transfer_allowed") is not False:
            raise ValueError("Unsupported project value authority in shared lookup")
        if sha256(record["text"].encode("utf-8")) != record["text_sha256"]:
            raise ValueError("Knowledge record body mismatch")
        relative = record["public_path"]
        path = checked_path(root, relative)
        if relative not in verified_payloads:
            if relative not in entries or sha256(path.read_bytes()) != entries[relative]["sha256"]:
                raise ValueError("Knowledge source projection identity mismatch: " + relative)
            verified_payloads.add(relative)
    if len(records) != manifest["records"]:
        raise ValueError("Knowledge record count mismatch")
    return manifest, records


def load_original_scorer(root: Path = ROOT):
    path = root / "aspen_v10/scripts/query_user_guide_knowledge.py"
    spec = importlib.util.spec_from_file_location("preserved_v10_lexical_query", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.score_text


def query_terms(query: str) -> list[str]:
    terms = [term for term in re.split(r"[\s,，;；。！？、/]+", query.strip()) if term]
    for trigger, aliases in ALIASES.items():
        if trigger in query:
            terms.extend([trigger, *aliases])
    return list(dict.fromkeys(terms))[:24]


def search(query: str = "", *, corpus: str = "all", node_id: str | None = None,
           limit: int = 5, detail: bool = False, root: Path = ROOT,
           full_text: bool = False) -> dict:
    manifest, records = load_records(root)
    score_text = load_original_scorer(root)
    terms = query_terms(query)
    mode = "detail" if detail or any(term in query for term in ("公式", "计算", "数值", "多少", "kg", "kPa")) else "macro_first"
    order = {layer: index for index, layer in enumerate(("L1", "L2", "L0", "L3") if mode == "detail" else ("L3", "L2", "L1", "L0"))}
    ranked = []
    for record in records:
        if corpus != "all" and record["corpus"] != corpus:
            continue
        if node_id and record["node_id"].casefold() != node_id.casefold():
            continue
        if not node_id and not record.get("retrieval_eligible", False):
            continue
        text = " ".join((record["node_id"], record["title"], record["text"], " ".join(record.get("routes", [])), " ".join(record.get("keywords", []))))
        score, matches = score_text(text, record["title"], terms)
        if not node_id and score <= 0:
            continue
        result = dict(record)
        result.update(score=score, matches=matches,
                      provenance_path={"corpus": record["corpus"], "node_id": record["node_id"],
                                       "source": record["source"], "public_path": record["public_path"],
                                       "public_json_pointer": record.get("public_json_pointer")})
        result["text_is_excerpt"] = not full_text and len(result["text"]) > 1600
        if result["text_is_excerpt"]:
            result["text"] = result["text"][:1600]
        ranked.append(result)
    ranked.sort(key=lambda item: (order[item["knowledge_layer"]], -item["score"], item["node_id"]))
    return {"schema": "offline-knowledge-query-v1", "query": query, "corpus": corpus,
            "mode": mode, "retrieval_method": "preserved_v10_lexical_score_plus_layer_priority",
            "matched_count": len(ranked), "results": ranked[:max(1, min(limit, 100))],
            "remote_payload_available": False, "original_pdf_payload_bundled": False,
            "current_project_authority": False, "project_value_transfer_allowed": False,
            "learning_event": False, "knowledge_records_sha256": next(item["sha256"] for item in manifest["files"] if item["path"] == "records.jsonl"),
            "scope_notice": "Original method/operation knowledge; not current-project evidence. Unbundled source pages and held bodies are not silently fetched."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="")
    parser.add_argument("--corpus", choices=("all", *CORPORA), default="all")
    parser.add_argument("--node-id")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--full-text", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--vector", action="store_true", help="Optional existing workspace hash-vector index; requires bundled numpy/index.")
    args = parser.parse_args(argv)
    if not args.query.strip() and not args.node_id:
        parser.error("--query or --node-id is required")
    try:
        if args.vector and not args.node_id:
            from vector_adapter import query as vector_query
            result = vector_query(args.query, corpus=args.corpus, limit=args.limit, detail=args.detail)
        else:
            result = search(args.query, corpus=args.corpus, node_id=args.node_id, limit=args.limit, detail=args.detail, full_text=args.full_text)
    except (ValueError, OSError, KeyError, ImportError) as exc:
        print(json.dumps({"status": "knowledge_unavailable", "reason": str(exc)}, ensure_ascii=False))
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["scope_notice"])
        for item in result["results"]:
            print(f"{item['node_id']} | {item['knowledge_layer']} | {item['knowledge_status']} | {item['public_path']}")
            print(item["text"] if item["content_available"] else "Body held for item-specific source-expression review; see identity and source hash.")
    return 0 if result["results"] else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
