# -*- coding: utf-8 -*-
"""Build one local vector index for workspace knowledge graphs and skill chain.

The index is deterministic and offline. It covers active project knowledge
graphs plus active Aspen/equipment skill routing files, while skipping backups
and generated duplicate trees.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

import numpy as np


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


WORKSPACE = Path(__file__).resolve().parents[1]
CHEM_PRINCIPLES_ROOT = WORKSPACE / "chemical_principles_knowledge"
BUNDLED_SKILLS = WORKSPACE.parent / "skills"
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
CODEX_SKILLS = Path(r'{CHEM_SKILLS}')
INDEX_DIR = WORKSPACE / "knowledge_vector_index"
RECORDS_JSONL = INDEX_DIR / "records.jsonl"
VECTORS_NPY = INDEX_DIR / "vectors.npy"
CONFIG_PATH = INDEX_DIR / "vector_index_config.json"
README_PATH = INDEX_DIR / "README.md"
ROUTES_CONFIG = WORKSPACE / "scripts" / "retrieval_routes.json"
RETRIEVAL_EVAL_SET = WORKSPACE / "scripts" / "retrieval_eval_set.jsonl"

DIM = 768
CHAR_NGRAM_RANGE = (2, 5)
TOKEN_NGRAM_RANGE = (1, 3)
MAX_CHARS = 2600
OVERLAP_CHARS = 260
GENERATED_MARKER = "<!-- generated: workspace_knowledge_vector_index -->"
V14_MANUAL_GRAPH = CODEX_SKILLS / "aspen-plus-operations" / "references" / "manual_knowledge_graph.json"


ACTIVE_SKILL_DIRS = [
    CODEX_SKILLS / 'aspen-adaptive-generalization-loop',
    CODEX_SKILLS / 'aspen-document-driven-flowsheet',
    CODEX_SKILLS / 'aspen-edr-rating-delivery',
    CODEX_SKILLS / 'aspen-flowsheet-cost-skill-builder',
    CODEX_SKILLS / 'aspen-flowsheet-error-repair',
    CODEX_SKILLS / 'aspen-heat-pump-distillation-replacement',
    CODEX_SKILLS / 'aspen-kinetics-documentation',
    CODEX_SKILLS / 'aspen-non-reactor-equipment-cost',
    CODEX_SKILLS / 'aspen-plus-operations',
    CODEX_SKILLS / 'aspen-plus-template',
    CODEX_SKILLS / 'aspen-pressure-pfd-delivery',
    CODEX_SKILLS / 'aspen-tower-optimization-workflow',
    CODEX_SKILLS / 'aspen-two-section-flowsheet',
    CODEX_SKILLS / 'chemical-engineering-expert',
    CODEX_SKILLS / 'chemical-equipment-selection-audit',
    CODEX_SKILLS / 'chemical-tower-design',
    CODEX_SKILLS / 'equipment-design-app',
    CODEX_SKILLS / 'subagent-dispatch',
    CODEX_SKILLS / 'sw6-scripted-equipment-design',
]

SCOPED_SOURCE_GROUPS = {}

WORKSPACE_FILES = [
    WORKSPACE / "AGENTS.md",
    WORKSPACE / "LOCAL_KNOWLEDGE_GRAPH_LINKS.md",
    WORKSPACE / "PROJECT_CHANGE_OFFSET_TABLE_TEMPLATE.md",
]

WORKSPACE_GRAPH_DIRS = [
    CHEM_PRINCIPLES_ROOT / 'knowledge_graph',
    WORKSPACE / 'aspen_knowledge' / 'knowledge_graph',
    WORKSPACE / 'equipment_knowledge' / 'knowledge_graph',
]

V10_ROOT = WORKSPACE / "aspen_user_guide_v10_knowledge"
V10_MANIFEST = V10_ROOT / "manifest.json"
V10_DETAIL_RECORDS = V10_ROOT / "knowledge_graph" / "operation_detail_records.json"

TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml"}
SKIP_DIR_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".tmp",
    "tmp",
    "_archive",
    "archive",
    "archives",
    "output",
    "outputs",
    "build",
    "dist",
    "cache",
    "qa_renders",
    "executable_data",
    "external_sources",
    "prior_state",
    "raw_l0",
    "rawl0",
    "vector_index",
    "knowledge_vector_index",
    "evolution_records",
    "aspen_case_audit",
    "case_audit",
    "case_audits",
}

RETRIEVAL_ADMISSION_POLICY = "strict-default-source-admission-v1"
AUDIT_SCHEMAS = {
    "aspen-case-audit-event-v2", "aspen-case-process-slice-v2",
    "aspen-learning-review-record-v2", "adaptive-error-memory-atomic-index-1.0",
}
EXCLUDED_STATES = {
    "case_audit_only", "audit_only", "case_relaxed", "case_accepted_with_relaxation",
    "relaxed_lineage", "legacy_unassessed", "learning_candidate_review_only",
    "candidate_review_only", "quarantined", "superseded",
}


def path_admission_reason(path: str | Path) -> str | None:
    """A source-group or history query is not permission to unquarantine data."""
    parts = [part for part in str(path).replace("\\", "/").casefold().split("/") if part]
    if set(parts) & SKIP_DIR_PARTS or any(
        "backup" in part or part.startswith(("build_", "output_", "outputs_", "_archive", "archive_"))
        or part.endswith(("_archive", "_backup")) for part in parts
    ):
        return "EXCLUDED_SOURCE_TREE"
    norm = "/".join(parts)
    if "aspen-adaptive-generalization-loop/references/error_memory/" in norm:
        return "ADAPTIVE_HISTORY_AUDIT_ONLY"
    if parts and (parts[-1].endswith(("_aspen_learning_log.md", "_aspen_learning_log.jsonl", "_process_slices.md", "_process_slices.jsonl", "_candidate_patch.md"))):
        return "AUDIT_OR_CANDIDATE_ARTIFACT"
    return None


def metadata_admission_reason(value: object) -> str | None:
    """Inspect structured record metadata, never keyword-match policy prose."""
    if isinstance(value, list):
        return next((reason for item in value if (reason := metadata_admission_reason(item))), None)
    if not isinstance(value, dict):
        return None
    schema = str(value.get("schema_version", value.get("schema", ""))).casefold()
    if schema in AUDIT_SCHEMAS:
        return "AUDIT_SCHEMA"
    for key in ("default_retrieval", "default_retrieval_eligible", "learning_eligible"):
        if key in value and value[key] is not True:
            return "INELIGIBLE_OR_UNKNOWN_" + key.upper()
    if value.get("relaxation_applied") is True or value.get("relaxations"):
        return "RELAXED_LINEAGE"
    for key in ("record_scope", "acceptance_mode", "provenance_state", "effective_state", "effective_status", "knowledge_status"):
        if str(value.get(key, "")).casefold() in EXCLUDED_STATES:
            return "EXCLUDED_" + key.upper()
    if value.get("knowledge_role") == "evolution_history":
        return "EVOLUTION_HISTORY"
    # JSON schemas describe fields rather than attest to an incident's state.
    # Do not interpret an example/default inside their property definitions as
    # source metadata. Ordinary wrappers/lists cannot wash away an audit record.
    if "$schema" in value and "properties" in value:
        return None
    for child in value.values():
        if isinstance(child, (dict, list)) and (reason := metadata_admission_reason(child)):
            return reason
    return None


def content_admission_reason(text: str, *, complete_source: bool = True) -> str | None:
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith(("{", "[")):
        try:
            return metadata_admission_reason(json.loads(stripped))
        except json.JSONDecodeError:
            # JSONL is identified by content as well as extension. A renamed
            # audit ledger remains excluded; malformed structured input closes.
            lines = [line for line in stripped.splitlines() if line.strip()]
            try:
                values = [json.loads(line) for line in lines]
            except json.JSONDecodeError:
                if complete_source:
                    return "STRUCTURED_SOURCE_UNPARSEABLE"
                # Stored chunks are truncated by design, not malformed source
                # files. Still catch explicit audit metadata in partial JSON.
                if re.search(r'"(?:default_retrieval(?:_eligible)?|learning_eligible)"\s*:\s*(?:false|null)\b', stripped):
                    return "INELIGIBLE_PARTIAL_RECORD"
                if any(re.search(r'"(?:schema_version|schema)"\s*:\s*"' + re.escape(schema) + r'"', stripped) for schema in AUDIT_SCHEMAS):
                    return "AUDIT_SCHEMA"
                return None
            return metadata_admission_reason(values)
    # Inspect actual scalar declarations only, not mentions such as the short
    # ERROR router explaining why `learning_eligible=false` is quarantined.
    fields: dict[str, object] = {}
    in_fence = False
    for line in stripped.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.fullmatch(r"\s*(?:-\s+)?`?(default_retrieval(?:_eligible)?|learning_eligible|record_scope|acceptance_mode|provenance_state|effective_state|effective_status)`?\s*:\s*`?([A-Za-z_]+)`?\s*", line)
        if match:
            key, raw = match.groups()
            fields[key] = {"false": False, "true": True}.get(raw.casefold(), raw.casefold())
    if fields:
        return metadata_admission_reason(fields)
    if re.match(r"# (?:Case Audit Only|Learning Candidate Review|Candidate SKILL\.md Patch):", stripped):
        return "AUDIT_OR_CANDIDATE_MARKDOWN"
    return None


def record_admission_reason(record: dict) -> str | None:
    """Also filter stale index rows before scope activation and ranking."""
    for key in ("source_path", "extract_path"):
        if reason := path_admission_reason(str(record.get(key, ""))):
            return reason
    if reason := metadata_admission_reason(record):
        return reason
    if record.get("retrieval_admission_policy") != RETRIEVAL_ADMISSION_POLICY:
        if reason := content_admission_reason(str(record.get("text", "")), complete_source=False):
            return reason
    norm = str(record.get("source_path", "")).replace("\\", "/").casefold()
    if norm.endswith("aspen-adaptive-generalization-loop/references/error_memory.md"):
        # The pre-migration 144-event blob had this same filename. Its old rows
        # cannot masquerade as the new small router until the index is rebuilt.
        if record.get("retrieval_admission_policy") != RETRIEVAL_ADMISSION_POLICY or not record.get("source_sha256"):
            return "ADAPTIVE_ROUTER_REBUILD_REQUIRED"
    return None


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def tokenise(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{0,32}|[0-9]+(?:\.[0-9]+)?|[\u4e00-\u9fff]{1,6}", text)


def char_ngrams(text: str, min_n: int, max_n: int) -> Iterable[str]:
    compact = re.sub(r"\s+", "", text)
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE.resolve()).as_posix()
    except ValueError:
        try:
            skill_relative = path.resolve().relative_to(CODEX_SKILLS.resolve()).as_posix()
            return f"skills/{skill_relative}"
        except ValueError:
            return str(path)


def assert_output_guard() -> None:
    workspace_resolved = WORKSPACE.resolve()
    index_resolved = INDEX_DIR.resolve()
    skills_resolved = CODEX_SKILLS.resolve()
    if not str(index_resolved).startswith(str(workspace_resolved)):
        raise RuntimeError(f"Refusing to write vector index outside workspace: {index_resolved}")
    if str(index_resolved).startswith(str(skills_resolved)):
        raise RuntimeError(f"Refusing to write vector index inside Codex skills: {index_resolved}")
    for path in [RECORDS_JSONL, VECTORS_NPY, CONFIG_PATH, README_PATH]:
        resolved = path.resolve()
        if not str(resolved).startswith(str(index_resolved)):
            raise RuntimeError(f"Refusing unexpected output path: {resolved}")


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def should_skip(path: Path) -> bool:
    parts = {part.casefold() for part in path.parts}
    # The full textbook evidence lives in its read-only local FTS index; source
    # payloads and upstream snapshots must not become shared concept vectors.
    if path.resolve().is_relative_to(CHEM_PRINCIPLES_ROOT / "source_pages"):
        return True
    if path_admission_reason(path):
        return True
    if any(
        "backup" in part
        or part.startswith(("build_", "output_", "outputs_", "_archive"))
        or part.endswith(("_archive", "_backup"))
        for part in parts
    ):
        return True
    return False


def iter_text_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    if root.is_file():
        if root.suffix.casefold() in TEXT_EXTS and not should_skip(root):
            yield root
        return
    for path in root.rglob("*"):
        if should_skip(path):
            continue
        if path.is_file() and path.suffix.casefold() in TEXT_EXTS:
            yield path


def split_long_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n##", start, end), text.rfind("\n\n", start, end), text.rfind("。", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def file_title(path: Path, text: str) -> str:
    for line in text.splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped and len(stripped) < 80:
            return stripped
    return path.stem


def classify_file(path: Path, text: str) -> dict[str, str]:
    """Classify authority/memory role so retrieval can avoid candidate pollution."""
    name = path.name.casefold()
    path_norm = path.as_posix().casefold()
    text_norm = text.casefold()

    if "chemical_principles_knowledge/knowledge_graph/" in path_norm:
        if "/concept_nodes/" in path_norm:
            if name.startswith("l3-"):
                layer = "L3_worldview"
            elif name.startswith("l2-"):
                layer = "L2_principle"
            elif name.startswith("l1-"):
                layer = "L1_method"
            else:
                layer = "L2_principle"
            return {
                "knowledge_role": "canonical_reference",
                "knowledge_status": "active",
                "retrieval_priority": "high",
                "knowledge_layer": layer,
            }
        if "/chapter_nodes/" in path_norm:
            return {
                "knowledge_role": "canonical_reference",
                "knowledge_status": "active",
                "retrieval_priority": "high",
                "knowledge_layer": "L2_principle",
            }
        if "/method_nodes/" in path_norm:
            return {
                "knowledge_role": "canonical_reference",
                "knowledge_status": "active",
                "retrieval_priority": "normal",
                "knowledge_layer": "L1_method",
            }
        if name == "00_hierarchy.md":
            return {
                "knowledge_role": "canonical_router",
                "knowledge_status": "active",
                "retrieval_priority": "high",
                "knowledge_layer": "L3_worldview",
            }

    if name in {"error_memory.md", "00_error_memory.md"}:
        priority = "P0" if "`priority`: p0" in text_norm else "first_read"
        has_entry = re.search(r"^##\s+\S*(?:ERR|错误|纠错)[-\s]", text, flags=re.MULTILINE | re.IGNORECASE) is not None
        return {
            "knowledge_role": "error_memory",
            "knowledge_status": "procedural_guards" if "## Three current procedural guards" in text else "verified_memory" if has_entry else "empty_memory",
            "retrieval_priority": priority,
        }
    if name == "new_knowledge.md":
        if "`status`: candidate" in text_norm:
            status = "mixed_or_candidate"
        elif "`status`: promoted" in text_norm:
            status = "promoted_or_empty"
        else:
            status = "empty_or_intake"
        return {
            "knowledge_role": "new_knowledge",
            "knowledge_status": status,
            "retrieval_priority": "on_demand",
        }
    if "evolution_records/" in path_norm or "candidate" in name:
        return {
            "knowledge_role": "evolution_history",
            "knowledge_status": "candidate_or_historical",
            "retrieval_priority": "low",
        }
    if "template" in name or "_seed" in name:
        return {
            "knowledge_role": "template",
            "knowledge_status": "reference_only",
            "retrieval_priority": "low",
        }
    if name in {"skill.md", "readme.md", "agents.md", "local_knowledge_graph_links.md"} or "router" in name:
        return {
            "knowledge_role": "canonical_router",
            "knowledge_status": "active",
            "retrieval_priority": "normal",
        }
    return {
        "knowledge_role": "canonical_reference",
        "knowledge_status": "active_or_scoped",
        "retrieval_priority": "normal",
    }


def declared_scope_aliases(text: str) -> list[str]:
    """Extract only explicitly labelled trigger/alias phrases near a case header."""
    aliases: list[str] = []
    lines = text.splitlines()[:60]
    collecting = False
    for line in lines:
        stripped = line.strip()
        lowered = stripped.casefold()
        if any(label in lowered for label in ["trigger sentence:", "natural-language aliases:", "query aliases:"]):
            collecting = True
            stripped = stripped.split(":", 1)[-1].strip()
        elif collecting and not stripped:
            collecting = False
            continue
        elif not collecting:
            continue
        for item in re.split(r"[,，;；]", stripped):
            item = item.strip(" .。`\t")
            if 3 <= len(item) <= 80:
                aliases.append(item.casefold())
    return aliases


def scope_metadata(path: Path, source_group: str, text: str = "") -> dict[str, object]:
    """Attach hard retrieval scope; similarity never overrides this metadata."""
    if source_group in SCOPED_SOURCE_GROUPS:
        return dict(SCOPED_SOURCE_GROUPS[source_group])

    path_norm = path.as_posix().casefold()
    if "selection_learning_graph_20260622" in path_norm:
        return {
            "authority_scope": "historical_case",
            "scope_keys": ["selection_learning_graph_20260622", "历史选型", "选型学习图谱"],
        }
    if "project_overlays/c1_hydraulic_check" in path_norm:
        return {
            "authority_scope": "project_overlay",
            "scope_keys": ["c1", "c1塔", "c1 hydraulic", "c1水力学"],
        }
    if "project_overlays/aspen_edr_rating_delivery" in path_norm:
        return {
            "authority_scope": "project_overlay",
            "scope_keys": ["7.9", "portfinal0713", "fullflow_hyd_edr", "e0201", "e0203", "e0207"],
        }
    if path.name.casefold().startswith("project_cases_"):
        case_keys = ["项目案例", "project case", path.stem.casefold()]
        case_keys.extend(re.findall(r"\d{4,8}", path.stem.casefold()))
        case_keys.extend(declared_scope_aliases(text))
        return {
            "authority_scope": "historical_case",
            "scope_keys": sorted(set(case_keys)),
        }
    if "evolution_records/" in path_norm:
        return {
            "authority_scope": "historical_case",
            "scope_keys": ["演化记录", "历史方案", "evolution", "candidate"],
        }
    return {"authority_scope": "shared", "scope_keys": []}


def make_file_documents(path: Path, source_group: str, source_type: str) -> list[dict]:
    if should_skip(path):
        return []
    text = safe_read(path)
    if content_admission_reason(text):
        return []
    if source_group == "aspen-adaptive-generalization-loop" and path.name.casefold() == "error_memory.md" and re.search(r"^##\s+AAG-ERR-", text, re.M):
        return []  # Unmigrated 144-event source; only the new small router enters.
    source_hash = sha256(path)
    title = file_title(path, text)
    classification = classify_file(path, text)
    if metadata_admission_reason(classification):
        return []
    scoped = scope_metadata(path, source_group, text)
    chunks = split_long_text(text)
    docs = []
    for idx, chunk in enumerate(chunks):
        vector_id = hashlib.sha1(f"{rel(path)}:{idx}".encode("utf-8", errors="ignore")).hexdigest()[:16]
        docs.append(
            {
                "vector_id": vector_id,
                "source_group": source_group,
                "source_type": source_type,
                "source_path": rel(path),
                "title": title,
                "scope": "file-chunk",
                "chunk_index": idx,
                "text": chunk,
                "source_sha256": source_hash,
                "retrieval_admission_policy": RETRIEVAL_ADMISSION_POLICY,
                "default_retrieval_eligible": True,
                **classification,
                **scoped,
            }
        )
    return docs


def make_v10_documents() -> list[dict]:
    if not V10_MANIFEST.exists() or not V10_DETAIL_RECORDS.exists():
        return []
    manifest = json.loads(V10_MANIFEST.read_text(encoding="utf-8"))
    detail_records = json.loads(V10_DETAIL_RECORDS.read_text(encoding="utf-8"))
    docs: list[dict] = []

    for chapter in manifest.get("chapters", []):
        text = "\n".join(
            [
                chapter.get("node_id", ""),
                chapter.get("title", ""),
                " ".join(chapter.get("routes", [])),
                " ".join(chapter.get("triggers", [])),
                " ".join(chapter.get("headings", [])),
            ]
        )
        docs.append(
            {
                "vector_id": "v10:" + chapter["node_id"],
                "source_group": "aspen_user_guide_v10",
                "source_type": "knowledge_graph_structured",
                "source_path": chapter.get("node_file", ""),
                "extract_path": chapter.get("extract_file", ""),
                "node_id": chapter["node_id"],
                "title": chapter.get("title", ""),
                "scope": "chapter-node",
                "routes": chapter.get("routes", []),
                "page": f"{chapter.get('start_page')}-{chapter.get('end_page')}",
                "text": text,
                "knowledge_role": "canonical_reference",
                "knowledge_status": "active",
                "retrieval_priority": "normal",
                "authority_scope": "shared",
                "scope_keys": [],
            }
        )

    for detail in detail_records:
        scope = "page-fallback-node" if "page-source-fallback" in detail.get("kind", []) else "detail-node"
        docs.append(
            {
                "vector_id": "v10:" + detail["node_id"],
                "source_group": "aspen_user_guide_v10",
                "source_type": "knowledge_graph_structured",
                "source_path": detail.get("detail_index", ""),
                "extract_path": detail.get("source_extract", ""),
                "node_id": detail["node_id"],
                "chapter_node_id": detail.get("chapter_node_id", ""),
                "title": detail.get("chapter_title", ""),
                "scope": scope,
                "routes": detail.get("routes", []),
                "kind": detail.get("kind", []),
                "page": detail.get("page", ""),
                "text": detail.get("text", ""),
                "knowledge_role": "canonical_reference",
                "knowledge_status": "active",
                "retrieval_priority": "normal",
                "authority_scope": "shared",
                "scope_keys": [],
            }
        )
    return docs


def document_text(doc: dict) -> str:
    parts = [
        doc.get("vector_id", ""),
        doc.get("source_group", ""),
        doc.get("source_type", ""),
        doc.get("source_path", ""),
        doc.get("node_id", ""),
        doc.get("chapter_node_id", ""),
        doc.get("title", ""),
        doc.get("knowledge_role", ""),
        doc.get("knowledge_status", ""),
        doc.get("retrieval_priority", ""),
        doc.get("knowledge_layer", ""),
        doc.get("authority_scope", "shared"),
        " ".join(doc.get("scope_keys", [])),
        " ".join(doc.get("routes", [])),
        " ".join(doc.get("kind", [])),
        doc.get("text", ""),
    ]
    return "\n".join(str(part) for part in parts if part)


def build_documents() -> list[dict]:
    docs: list[dict] = []
    docs.extend(make_v10_documents())

    for path in WORKSPACE_FILES:
        docs.extend(make_file_documents(path, "workspace_router", "router"))

    for root in WORKSPACE_GRAPH_DIRS:
        group = root.relative_to(WORKSPACE).parts[0] if root.exists() else root.name
        for path in iter_text_files(root):
            docs.extend(make_file_documents(path, group, "knowledge_graph_file"))

    for root in ACTIVE_SKILL_DIRS:
        if not root.exists():
            continue
        for path in iter_text_files(root):
            docs.extend(make_file_documents(path, root.name, "skill_chain_file"))

    seen: set[str] = set()
    unique_docs: list[dict] = []
    for doc in docs:
        if doc["vector_id"] in seen:
            raise RuntimeError(f"duplicate vector id: {doc['vector_id']}")
        seen.add(doc["vector_id"])
        unique_docs.append(doc)
    return unique_docs


def write_jsonl(path: Path, docs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for doc in docs:
            compact = dict(doc)
            if len(str(compact.get("text", ""))) > 1800:
                compact["text"] = str(compact["text"])[:1797] + "..."
            fh.write(json.dumps(compact, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_readme(config: dict) -> None:
    text = f"""{GENERATED_MARKER}
# Workspace Knowledge And Skill Vector Index

This index vectorizes the chemical-expert reasoning layer, active local
knowledge graphs, and the active chemical/Aspen/equipment skill chain.

## Coverage

- Total vectors: {config['record_count']}
- Vector dimension: {config['dimension']}
- Source groups: {len(config['source_group_counts'])}

## Included Source Families

- Workspace routers: `AGENTS.md`, `LOCAL_KNOWLEDGE_GRAPH_LINKS.md`,
  `PROJECT_CHANGE_OFFSET_TABLE_TEMPLATE.md`
- Chemical-engineering expert reasoning, error memory, new-knowledge lifecycle,
  and active-asset registry
- Aspen Plus V10 user-guide structured graph: chapters, detail nodes, page fallback nodes
- Aspen Sun Lanyi graph: knowledge graph, chapter extracts, source pages
- Equipment-selection graph, standards graph, C1 hydraulic overlay
- Chemical-principles hierarchy: worldview/concept, mechanism, and method cards
  in the global index; full OCR pages remain in the graph-local SQLite evidence
  index and are reached by downward source links
- Active chemical/Aspen/equipment skill chain under `{CHEM_SKILLS}`

Backup, archive, output, build, executable-data, generated vector, `tmp`, and
`__pycache__` folders are skipped to avoid duplicates. Evolution records,
audit-only/relaxed artifacts and unassessed adaptive historical events are
excluded before indexing and ranking, even with an explicit source-group or
history query. The compact adaptive ERROR_MEMORY router remains first-read;
its 144 raw events and index remain reachable only through the separate audit
reader. No historical label grants current learning or acceptance authority.

## Reuse-First Rule

Before implementing or exploring a new route, query this index and the relevant
skill/reference/script. Prefer skill-verified feasible methods. Build a new
method only when the indexed method is missing, blocked, unsafe for the active
authority files, contradicted by fresh exports, or explicitly requested by the
user.

## Current Reusable Capability Map

Chinese query aliases: 子代理, 最多三个, 并行, 复用, send_input.
MCP aliases: 没有MCP, 没mcp, 不装MCP, 要不要安装MCP, 启用MCP, 继续COM, 继续script.

| Need | Reuse First | Current Capability |
| --- | --- | --- |
| Chemical-engineering reasoning and memory | `chemical-engineering-expert` | Required-method lock, evidence classes, derivation-before-missing, non-compensable macro design gates, flowsheet-order/recycle/terminal audit, high-grade-utility preheat/recovery/MVR screening, and correction/new-knowledge governance |
| Chemical-engineering principles and common sense | `chemical_principles_knowledge` | Top-down L3 worldview -> L2 mechanisms -> L1 methods; page OCR, formula, figure, and table evidence stays in a separate local detail index |
| Find the right graph or skill rule | `query_workspace_vectors.py` | Vector search over routers, graphs, V10 detail nodes, and active skill chain |
| Aspen document-to-flowsheet routing | `aspen-document-driven-flowsheet` | Authority-first route, change-offset gate, scaffold/island routing, promotion/quarantine |
| Aspen card/operation mechanics | `aspen-plus-operations` | V14 card lookup, COM/script operations, run/export/delivery QA, V10 workflow context |
| Aspen EDR rating and delivery | `aspen-edr-rating-delivery` | HeatX coverage, COM/XML EDR audit, true-EDR readback, engineering gates, exact-file delivery |
| Fast Aspen MCP operations | `aspen_mcp_invocation.md` | Optional acceleration path: MCP open/run/get/set/close; enhanced simple block/stream place/connect/save. If MCP is absent, continue with COM/script and ask whether to install/enable MCP |
| Robust Aspen COM/export work | operation graph and reusable scripts | Watchdogs, locks, APW SaveAs/reopen, CSV exports, hashes, package QA |
| Kinetic reactor setup | kinetics expert/freeze templates plus V14 graph | Source-to-card freeze chain, unit conversion ledger, blocked/provisional handling |
| Tower/column optimization | `aspen-tower-optimization-workflow` | DSTWU/RadFrac route, feed-stage/reflux/reboiler tuning, Design Spec reconnects |
| Equipment and standards audit | equipment/standards graphs | Formula families, source classification, EDR/SW6/vendor/manual boundaries |
| Subagent factual delegation | `subagent-dispatch` | At most three open/running subagents unless the user sets a cap; later tasks reuse existing subagents or replace closed ones |

## Query

```text
python scripts/query_workspace_vectors.py <terms>
python scripts/query_workspace_vectors.py <terms> --show-route
python scripts/query_workspace_vectors.py <terms> --route off
python scripts/query_workspace_vectors.py <terms> --source-type skill_chain_file
python scripts/query_workspace_vectors.py <terms> --source-group aspen-plus-operations
python scripts/query_workspace_vectors.py <terms> --scope-key <project-or-course-id>
python scripts/query_workspace_vectors.py <terms> --json
python scripts/eval_workspace_retrieval.py
```

`query_workspace_vectors.py` uses `scripts/retrieval_routes.json` by default to
compose one domain route with matched cross-domain guard routes and rerank
source families. This keeps chemical-expert method/evidence/macro rules visible
beside mechanical Aspen or equipment results. Use `--route off` to compare
against plain vector plus lexical ranking. Route config is a retrieval prior
only; it does not change authority files or promote values.

## Files

- `records.jsonl`: vector metadata and short source text.
- `vectors.npy`: L2-normalized float32 vectors.
- `vector_index_config.json`: build metadata and source counts.

## Authority Boundary

This vector index is retrieval support only. It does not promote values or
override project ledgers, change-offset tables, source-freeze ledgers, Aspen
exports, or skill hard gates.

Records include `knowledge_role`, `knowledge_status`, and
`retrieval_priority`. Verified error memory receives first-read routing;
unpromoted NEW_KNOWLEDGE intake is demoted unless explicitly queried. Excluded
audit/evolution/relaxed material cannot bypass admission through query keywords.

Records also include `authority_scope` and `scope_keys`. Project-local,
project-overlay, course-local, and historical-case records are hard-filtered
unless the query or explicit caller context activates their scope. Similarity
score and route bonuses cannot bypass this boundary. After that hard gate, an
explicitly activated scope receives an authority prior so the intended local
source ranks ahead of broad shared references. Both scope leakage and explicit
scope activation are covered by retrieval regression cases.

## V14 Operation Preservation Guard

The Aspen Plus V14 operation manual graph is read-only input for this index:

`{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json`

This script never writes into `.codex/skills` or rewrites the V14 graph. V10
user-guide nodes and vector results may be cited beside V14 node IDs, but they
must not replace V14 card-field rules.
"""
    README_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    assert_output_guard()
    docs = build_documents()
    if not docs:
        print("No documents found to vectorize.", file=sys.stderr)
        return 2
    vectors = np.vstack([vectorize_text(document_text(doc)) for doc in docs]).astype(np.float32)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(RECORDS_JSONL, docs)
    np.save(VECTORS_NPY, vectors)

    group_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for doc in docs:
        group_counts[doc["source_group"]] = group_counts.get(doc["source_group"], 0) + 1
        type_counts[doc["source_type"]] = type_counts.get(doc["source_type"], 0) + 1

    config = {
        "name": "workspace_knowledge_vector_index",
        "dimension": DIM,
        "record_count": len(docs),
        "char_ngram_range": list(CHAR_NGRAM_RANGE),
        "token_ngram_range": list(TOKEN_NGRAM_RANGE),
        "vectorizer": "signed_hashing_char_token_ngrams_v1",
        "records_jsonl": "records.jsonl",
        "vectors_npy": "vectors.npy",
        "records_sha256": sha256(RECORDS_JSONL),
        "vectors_sha256": sha256(VECTORS_NPY),
        "retrieval_admission_policy": RETRIEVAL_ADMISSION_POLICY,
        "source_group_counts": dict(sorted(group_counts.items())),
        "source_type_counts": dict(sorted(type_counts.items())),
        "read_only_skill_chain": True,
        "v14_manual_graph_path": str(V14_MANUAL_GRAPH),
        "v14_manual_graph_sha256": sha256(V14_MANUAL_GRAPH) if V14_MANUAL_GRAPH.exists() else None,
        "retrieval_routes_path": str(ROUTES_CONFIG),
        "retrieval_routes_sha256": sha256(ROUTES_CONFIG) if ROUTES_CONFIG.exists() else None,
        "retrieval_eval_set_path": str(RETRIEVAL_EVAL_SET),
        "retrieval_eval_set_sha256": sha256(RETRIEVAL_EVAL_SET) if RETRIEVAL_EVAL_SET.exists() else None,
    }
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(config)

    print(f"Vectorized {len(docs)} workspace knowledge records into {vectors.shape[1]} dimensions.")
    print(f"Index directory: {INDEX_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
