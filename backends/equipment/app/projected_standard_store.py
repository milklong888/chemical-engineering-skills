"""Explicit, separately identified read-only projection of the original store.

Original dataset/record QA is inherited, not upgraded. Only the original pipe
consumer's qualified two datasets can supply its calculation records. Other
facts and figures are retrieval evidence, never automatic design approval.
"""
from __future__ import annotations

from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3

PARENT_DATABASE_SHA256 = "27A1C4B0FA5CA9DAEACD727808A4758ECC156835BADC83461BF789DA0BA8F551"
TABLE_COUNTS = {"datasets": 24, "standard_records": 24887, "figure_datasets": 14, "figure_records": 1844}
PIPE_DATASETS = ("gbt1048_nominal_pressure_series", "gbt17395_pipe_dimensions_weights")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical(value) -> str:
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def _paths(root: Path):
    root = Path(root).resolve()
    manifest_path = root / "data/standard_facts_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_path = (root / manifest.get("compressed_path", manifest["path"])).resolve()
    if not payload_path.is_relative_to(root) or payload_path.is_symlink():
        raise ValueError("PROJECTION_PATH_OUTSIDE_PACKAGE")
    return manifest_path, manifest, payload_path


@lru_cache(maxsize=2)
def _open_verified(root_text: str, manifest_sha: str, payload_size: int, payload_mtime_ns: int):
    root = Path(root_text)
    manifest_path, manifest, path = _paths(root)
    if (manifest.get("schema") != "equipment-standard-fact-projection-manifest-v1"
            or manifest.get("parent_database_sha256") != PARENT_DATABASE_SHA256
            or manifest.get("table_counts") != TABLE_COUNTS):
        raise ValueError("PROJECTION_IDENTITY_OR_COUNTS_INVALID")
    payload = path.read_bytes()
    if "compressed_path" in manifest:
        if sha(payload) != manifest["compressed_sha256"] or len(payload) != manifest["compressed_size_bytes"]:
            raise ValueError("PROJECTION_COMPRESSED_HASH_MISMATCH")
        payload = gzip.decompress(payload)
    if sha(payload) != manifest["sha256"] or len(payload) != manifest["size_bytes"]:
        raise ValueError("PROJECTION_DATABASE_HASH_MISMATCH")
    connection = sqlite3.connect(":memory:")
    if not hasattr(connection, "deserialize"):
        connection.close()
        raise RuntimeError("dependency_unavailable: SQLite deserialize support is required")
    connection.deserialize(payload)
    connection.execute("PRAGMA query_only=ON")
    if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        connection.close()
        raise ValueError("PROJECTION_SQLITE_INTEGRITY_FAILED")
    for table, expected in TABLE_COUNTS.items():
        if connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0] != expected:
            raise ValueError(f"PROJECTION_TABLE_COUNT_MISMATCH:{table}")
        for key, dataset_id, text, row_sha in connection.execute(f'SELECT * FROM "{table}"'):
            value = json.loads(text)
            if canonical(value) != row_sha or value["dataset_id"] != dataset_id:
                raise ValueError(f"PROJECTION_RECORD_HASH_MISMATCH:{table}:{key}")
    return connection, {**manifest, "manifest_sha256": sha(manifest_path.read_bytes())}


def verified_store(root: Path):
    manifest_path, _manifest, payload = _paths(root)
    stat = payload.stat()
    return _open_verified(str(Path(root).resolve()), sha(manifest_path.read_bytes()), stat.st_size, stat.st_mtime_ns)


def verification(root: Path) -> dict:
    _connection, manifest = verified_store(root)
    return {"status": "PASS", "quick_check": "ok", "counts": dict(TABLE_COUNTS),
            "database_id": "equipment_standard_facts_projection_v1", "relative_path": manifest.get("compressed_path", manifest["path"]),
            "sha256": manifest["sha256"], "scope_status": "SOURCE_FACTS_ONLY_QUALIFIED_CONSUMERS_REQUIRED",
            "projection_sha256": manifest["sha256"], "parent_database_sha256": PARENT_DATABASE_SHA256,
            "projection_manifest_sha256": manifest["manifest_sha256"],
            "role": "source_fact_not_automatic_design_evidence"}


def load_pipe_store(root: Path) -> dict:
    connection, manifest = verified_store(root)
    datasets = {}
    for dataset_id in PIPE_DATASETS:
        result = connection.execute("SELECT record_json FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        if result is None:
            raise ValueError(f"BLOCKED_PIPE_STANDARD_DATASET_MISSING:{dataset_id}")
        row = json.loads(result[0])
        if any(row.get(k) != v for k, v in {"qa_status": "VERIFIED", "reuse_class": "DIRECT_REUSE_VERIFIED", "lifecycle_state": "CURRENT"}.items()):
            raise ValueError(f"BLOCKED_PIPE_STANDARD_DATASET_NOT_PROMOTED:{dataset_id}")
        datasets[dataset_id] = row
    pn_fields = ("record_id", "raw_value", "normalized_number", "physical_page", "source_table", "source_row_label", "source_column_label", "source_sha256", "record_sha256", "standard_id", "standard_version", "qa_status", "reuse_class")
    wall_fields = ("record_id", "physical_page", "source_table", "source_row_label", "source_column_label", "source_sha256", "record_sha256", "standard_id", "standard_version", "normalized_number", "qa_status", "reuse_class")
    pn_records, wall_records = [], []
    for dataset_id in PIPE_DATASETS:
        for (text,) in connection.execute("SELECT record_json FROM standard_records WHERE dataset_id=?", (dataset_id,)):
            row = json.loads(text)
            if row["qa_status"] != "VERIFIED" or row["reuse_class"] != "DIRECT_REUSE_VERIFIED":
                continue
            if dataset_id == PIPE_DATASETS[0]:
                if str(row.get("raw_value") or "").upper().startswith("PN"):
                    pn_records.append({k: row[k] for k in pn_fields})
                continue
            payload = row.get("structured_payload", {})
            try:
                diameter = float(payload["nominal_outer_diameter_mm"])
                thickness = float(payload["nominal_wall_thickness_mm"])
            except (KeyError, ValueError, TypeError):
                continue  # Original loader's field-local rule, not a fabricated default.
            wall_records.append({**{k: row[k] for k in wall_fields},
                "source_payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                "outer_diameter_mm": diameter, "wall_thickness_mm": thickness,
                "outer_diameter_series": str(payload.get("outer_diameter_series") or ""),
                "wall_thickness_recommended": str(payload.get("wall_thickness_recommended")).strip().casefold() == "true",
                "unit_mass_kg_m": float(row["normalized_number"]), "table_id": payload.get("table_id"),
                "terminal_class": payload.get("terminal_class")})
    pn_records.sort(key=lambda x: x["normalized_number"])
    if len(pn_records) != 12 or len(wall_records) != 5620:
        raise ValueError("BLOCKED_PROJECTED_PIPE_CONSUMER_ROW_SET_CHANGED")
    manifest_path = Path(root).resolve() / "data/standard_facts_manifest.json"
    return {"build_id": manifest["parent_build_id"], "database_path": str(Path(root).resolve() / manifest.get("compressed_path", manifest["path"])),
        "database_sha256": manifest["sha256"], "parent_database_sha256": PARENT_DATABASE_SHA256,
        "database_authority_registry_path": str(manifest_path), "database_authority_registry_sha256": manifest["manifest_sha256"],
        "database_authority_status": "VERIFIED_EXPLICIT_PROJECTION_NOT_ORIGINAL_DATABASE",
        "database_scope_status": "ORIGINAL_QUALIFIED_PIPE_SUBSET_ONLY",
        "manifest_path": str(manifest_path), "manifest_sha256": manifest["manifest_sha256"],
        "datasets": datasets, "pn_records": pn_records, "wall_records": wall_records}


def search_facts(root: Path, query: str, limit: int) -> list[dict]:
    connection, manifest = verified_store(root)
    terms = [x for x in re.split(r"\s+", query.strip()) if x][:12]
    if not terms:
        return []
    results = []
    for table, id_key in (("standard_records", "record_id"), ("figure_records", "figure_record_id")):
        where = " OR ".join("record_json LIKE ?" for _ in terms)
        relevance = " + ".join("(record_json LIKE ?)" for _ in terms)
        patterns = [f"%{x}%" for x in terms]
        for text, projection_sha in connection.execute(f'SELECT record_json,projection_record_sha256 FROM "{table}" WHERE {where} ORDER BY ({relevance}) DESC,record_key LIMIT ?', (*patterns, *patterns, limit)):
            row = json.loads(text)
            summary = {key: row.get(key) for key in ("standard_id", "standard_version", "normalized_value", "normalized_number", "unit", "applicability", "condition_text", "relation_from_entity_id", "relation_to_entity_id", "direction", "error_bound") if row.get(key) not in (None, "")}
            results.append({"package_id": "design_standards", "source": f"standard-fact:{row['dataset_id']}:{row[id_key]}",
                "source_path": f"data/standard_facts.sqlite#{row['dataset_id']}/{row[id_key]}",
                "title": f"{row['standard_id']} / {row[id_key]}", "text": json.dumps(summary, ensure_ascii=False),
                "score": 1.0, "source_pdf_sha256": row.get("source_sha256"), "page": row.get("physical_page"),
                "source_record_sha256": row["record_sha256"], "projection_record_sha256": projection_sha,
                "projection_database_sha256": manifest["sha256"], "parent_database_sha256": PARENT_DATABASE_SHA256,
                "evidence_class": "X", "reuse_class": row["reuse_class"], "qa_status": row["qa_status"],
                "lifecycle_state": row["lifecycle_state"], "numeric_reuse_allowed": False,
                "reuse_boundary": "source_fact_retrieval_only; qualified calculation consumer and same-duty applicability required"})
    return results[:limit]
