"""Thin offline adapter to the existing workspace hash-vector and route code.

No learned embedding, training, model download, or new ranking algorithm is
introduced. Only eligible original records enter this separate numeric index.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_SCRIPTS = ROOT.parent / "workspace/scripts"
LAYERS = {"L3": "L3_worldview", "L2": "L2_principle", "L1": "L1_method", "L0": "L0_source_detail"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modules():
    # Pin imports to this release. Never search the caller's working directory
    # or the originating user's .codex tree.
    root = str(WORKSPACE_SCRIPTS.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    import vectorize_workspace_knowledge as vectors
    import query_workspace_vectors as routes
    for module, name in ((vectors, "vectorize_workspace_knowledge.py"), (routes, "query_workspace_vectors.py")):
        if Path(module.__file__).resolve() != (WORKSPACE_SCRIPTS / name).resolve():
            raise ValueError("Vector adapter imported a module outside this release")
    return vectors, routes


def adapt_record(record: dict, source_files: dict) -> dict:
    layer = record["knowledge_layer"]
    adapted = {**record,
        "vector_id": "offline:" + record["corpus"] + ":" + record["node_id"],
        "source_group": {"chemical_principles": "chemical_principles_knowledge", "sun_lanyi": "aspen_sun_lanyi_knowledge", "aspen_v10": "aspen_user_guide_v10_knowledge"}[record["corpus"]],
        "source_type": "preserved_graph_card" if layer != "L0" else "v10_detail_record",
        "source_path": "knowledge/" + record["public_path"],
        "source_sha256": source_files[record["public_path"]]["sha256"],
        "source_knowledge_layer": layer, "knowledge_layer": LAYERS[layer],
        "knowledge_role": "concept" if layer == "L3" else "source_knowledge",
        "scope": "shared", "scope_keys": [],
        "default_retrieval_eligible": bool(record.get("content_available") and record.get("retrieval_eligible")),
    }
    return adapted


def build(root: Path = ROOT) -> dict:
    from query_knowledge import load_records
    import numpy as np
    vectors, _ = modules()
    manifest, records = load_records(root)
    source_files = {row["path"]: row for row in manifest["files"]}
    docs, excluded = [], []
    for record in records:
        doc = adapt_record(record, source_files)
        reason = vectors.record_admission_reason(doc)
        if not doc["default_retrieval_eligible"] or reason:
            excluded.append({"node_id": doc["node_id"], "corpus": doc["corpus"], "reason": reason or "BODY_UNAVAILABLE"})
            continue
        docs.append(doc)
    matrix = np.vstack([vectors.vectorize_text(vectors.document_text(doc)) for doc in docs]).astype(np.float32)
    output = root / "vectors"
    output.mkdir(parents=True, exist_ok=True)
    records_path = output / "records.jsonl"
    records_path.write_text("".join(json.dumps(doc, ensure_ascii=False) + "\n" for doc in docs), encoding="utf-8")
    vector_path = output / "vectors.npy"
    np.save(vector_path, matrix, allow_pickle=False)
    config = {"schema": "preserved-knowledge-hash-vector-v1", "algorithm": "existing_workspace_hash_ngram",
              "learned_model": False, "network_required": False,
              "record_count": len(docs), "dimension": vectors.DIM, "shape": list(matrix.shape), "dtype": str(matrix.dtype),
              "source_records_sha256": sha(root / "records.jsonl"),
              "records_jsonl": "records.jsonl", "records_sha256": sha(records_path),
              "vectors_npy": "vectors.npy", "vectors_sha256": sha(vector_path),
              "algorithm_sha256": sha(WORKSPACE_SCRIPTS / "vectorize_workspace_knowledge.py"),
              "query_routing_sha256": sha(WORKSPACE_SCRIPTS / "query_workspace_vectors.py"),
              "routes_sha256": sha(WORKSPACE_SCRIPTS / "retrieval_routes.json"),
              "excluded_records": excluded, "project_value_transfer_allowed": False,
              "source_modified": False, "learning_event": False}
    (output / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return config


def query(query: str, *, corpus="all", limit=5, detail=False, root: Path = ROOT) -> dict:
    from query_knowledge import load_records, query_terms
    import numpy as np
    if not query.strip():
        raise ValueError("Non-empty query is required")
    vectors, routes = modules()
    _, original = load_records(root)
    by_identity = {(row["corpus"], row["node_id"]): row for row in original}
    output = root / "vectors"
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    if config.get("schema") != "preserved-knowledge-hash-vector-v1":
        raise ValueError("Unknown knowledge vector schema")
    for path, expected in ((root / "records.jsonl", config["source_records_sha256"]),
                           (output / "records.jsonl", config["records_sha256"]),
                           (output / "vectors.npy", config["vectors_sha256"]),
                           (WORKSPACE_SCRIPTS / "vectorize_workspace_knowledge.py", config["algorithm_sha256"]),
                           (WORKSPACE_SCRIPTS / "query_workspace_vectors.py", config["query_routing_sha256"]),
                           (WORKSPACE_SCRIPTS / "retrieval_routes.json", config["routes_sha256"])):
        if sha(path) != expected:
            raise ValueError("Knowledge vector dependency drift: " + path.name)
    docs = [json.loads(line) for line in (output / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    matrix = np.load(output / "vectors.npy", allow_pickle=False)
    if matrix.shape != (len(docs), vectors.DIM) or matrix.dtype != np.float32 or not np.isfinite(matrix).all():
        raise ValueError("Invalid numeric vector payload")
    expanded_query = " ".join(query_terms(query))
    qvec = vectors.vectorize_text(expanded_query)
    scores = matrix @ qvec
    selected = routes.infer_routes(query, routes.load_route_config())
    selected_routes = [route for route, _ in selected]
    results = []
    for index, doc in enumerate(docs):
        if corpus != "all" and doc["corpus"] != corpus:
            continue
        if vectors.record_admission_reason(doc) or not routes.scope_allowed(query, doc):
            continue
        # Standard hash vectors are fuzzy routing support, never a claim of
        # semantic or engineering truth. Reuse the original hybrid bonuses.
        lexical = routes.lexical_bonus(expanded_query, doc)
        if doc["source_knowledge_layer"] in {"L3", "L2"} and lexical <= 0:
            continue
        score = float(scores[index]) + lexical + routes.route_bonus(doc, selected_routes) + routes.knowledge_role_bonus(query, doc) + routes.knowledge_layer_bonus(query, doc)
        if score <= 0:
            continue
        row = dict(by_identity[(doc["corpus"], doc["node_id"])])
        row.update(score=score, provenance_path={"corpus": row["corpus"], "node_id": row["node_id"], "source": row["source"], "public_path": row["public_path"]})
        row["text_is_excerpt"] = len(row["text"]) > 1600
        row["text"] = row["text"][:1600]
        results.append(row)
    order = {key: i for i, key in enumerate(("L1", "L2", "L0", "L3") if detail else ("L3", "L2", "L1", "L0"))}
    results.sort(key=lambda row: (order[row["knowledge_layer"]], -row["score"], row["node_id"]))
    return {"schema": "offline-knowledge-query-v1", "query": query, "corpus": corpus,
            "retrieval_method": "existing_workspace_hash_vector_and_routes", "mode": "detail" if detail else "macro_first",
            "matched_count": len(results), "results": results[:max(1, min(limit, 100))],
            "routes": [route["name"] for route in selected_routes], "remote_payload_available": False,
            "current_project_authority": False, "project_value_transfer_allowed": False, "learning_event": False,
            "scope_notice": "Deterministic offline hash-vector routing over preserved source knowledge; not a learned embedding or project evidence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    search = sub.add_parser("query")
    search.add_argument("--query", required=True)
    search.add_argument("--corpus", default="all", choices=("all", "chemical_principles", "sun_lanyi", "aspen_v10"))
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--detail", action="store_true")
    args = parser.parse_args()
    try:
        result = build() if args.command == "build" else query(args.query, corpus=args.corpus, limit=args.limit, detail=args.detail)
    except (ImportError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "optional_vector_unavailable", "reason": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
