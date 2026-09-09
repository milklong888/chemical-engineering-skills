#!/usr/bin/env python3
"""Validate chemical-expert skill, asset registry, memories, UTF-8, and routes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


REQUIRED_SKILL_REFERENCES = [
    "EVOLUTION_LOOP.md",
    "evolution_review_contract.md",
    "STRICT_ACCEPTANCE_AND_LEARNING.md",
    "HIGHEST_LEVEL_GUARDS.md",
    "PROCESS_EQUIPMENT_FEEDBACK.md",
    "COMMON_SENSE_RAG.md",
    "REASONING_PROTOCOL.md",
    "ERROR_MEMORY.md",
    "NEW_KNOWLEDGE.md",
    "MEMORY_MAINTENANCE.md",
    "ACTIVE_ASSET_REGISTRY.md",
    "CANONICAL_RULE_OWNERSHIP.md",
    "EXTERNAL_AGENT_RESEARCH.md",
    "EXTERNAL_CHEMICAL_SKILL_AUDIT.md",
    "KNOWLEDGE_DISTILLATION_PIPELINE.md",
    "MACRO_DESIGN_QUALITY.md",
    "VECTOR_KNOWLEDGE_BASE_DESIGN.md",
    "OFFICIAL_PLUGIN_MIGRATION.md",
]


def clean_cell(value: str) -> str:
    return value.strip().strip("`")


def parse_registry(path: Path, codex_skills_root: Path) -> list[dict[str, Path | str]]:
    section = ""
    entries: list[dict[str, Path | str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "## Knowledge graphs":
            section = "graph"
            continue
        if line == "## Installed global skills":
            section = "global_skill"
            continue
        if line in {"## Workspace-only skills", "## Workspace-only project skill"}:
            section = "workspace_skill"
            continue
        if not section or not line.startswith("|") or line.startswith("| ---") or "| Status |" in line:
            continue
        cells = [clean_cell(item) for item in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        status, asset, root_text, error_text, knowledge_text = cells
        root = Path(root_text)
        if section == "global_skill":
            root = codex_skills_root / root
        entries.append(
            {
                "section": section,
                "status": status,
                "asset": asset,
                "root": root,
                "error": root / error_text,
                "knowledge": root / knowledge_text,
            }
        )
    return entries


def declared_registry_total(path: Path) -> int | None:
    """Read the registry's own coverage total instead of freezing a stale magic number."""
    match = re.search(
        r"^-\s+(\d+)\s+canonical roots total\.",
        path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return int(match.group(1)) if match else None


def scan_utf8(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [f"not UTF-8: {exc}"]
    if "\ufffd" in text:
        issues.append("contains Unicode replacement character")
    if any("\ue000" <= char <= "\uf8ff" for char in text):
        issues.append("contains private-use characters")
    if "TODO" in text and path.name == "SKILL.md":
        issues.append("contains unresolved TODO")
    return issues


def duplicate_ids(path: Path, prefix: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    ids = re.findall(rf"^##\s+({re.escape(prefix)}-[A-Z]+-\d+)\b", text, flags=re.MULTILINE)
    return sorted({item for item in ids if ids.count(item) > 1})


def tree_manifest(root: Path) -> dict[str, str]:
    """Return a relative-path -> SHA256 manifest without transient caches."""
    manifest: dict[str, str] = {}
    if not root.is_dir():
        return manifest
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if any(part in {"__pycache__", ".git"} for part in path.relative_to(root).parts):
            continue
        manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--codex-skills-root", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    codex_skills_root = args.codex_skills_root.resolve()
    source_skill = workspace / "skill_packages" / "chemical-engineering-expert"
    references = source_skill / "references"
    registry = references / "ACTIVE_ASSET_REGISTRY.md"
    failures: list[str] = []

    for relative in [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/macro_design_gate.py",
        "scripts/evaluate_learning_eligibility.py",
        "scripts/assess_evolution_candidate.py",
        "scripts/validate_chemical_expert_system.py",
    ]:
        if not (source_skill / relative).is_file():
            failures.append(f"missing skill file: {source_skill / relative}")
    for name in REQUIRED_SKILL_REFERENCES:
        if not (references / name).is_file():
            failures.append(f"missing required reference: {references / name}")

    entries = parse_registry(registry, codex_skills_root) if registry.is_file() else []
    declared_total = declared_registry_total(registry) if registry.is_file() else None
    if declared_total is None:
        failures.append("registry coverage summary is missing canonical root total")
    elif len(entries) != declared_total:
        failures.append(
            f"registry entry count expected {declared_total} from coverage summary, found {len(entries)}"
        )

    seen_roots: set[Path] = set()
    for entry in entries:
        root = Path(entry["root"])
        if root in seen_roots:
            failures.append(f"duplicate canonical root: {root}")
        seen_roots.add(root)
        if not root.is_dir():
            failures.append(f"missing canonical root: {root}")
            continue
        expected_entry = root / ("SKILL.md" if "skill" in str(entry["section"]) else "README.md")
        if not expected_entry.is_file() and not (root / "00-index.md").is_file():
            failures.append(f"missing skill/graph entry file: {root}")
        for field in ["error", "knowledge"]:
            target = Path(entry[field])
            if not target.is_file():
                failures.append(f"missing {field} companion for {entry['asset']}: {target}")

    critical_text_files = [
        workspace / "AGENTS.md",
        workspace / "LOCAL_KNOWLEDGE_GRAPH_LINKS.md",
        workspace / "PROJECT_CHANGE_OFFSET_TABLE_TEMPLATE.md",
        workspace / "aspen_sun_lanyi_knowledge" / "knowledge_graph" / "unknowns_router.md",
        source_skill / "SKILL.md",
        *[references / name for name in REQUIRED_SKILL_REFERENCES],
    ]
    for path in critical_text_files:
        if not path.is_file():
            continue
        for issue in scan_utf8(path):
            failures.append(f"encoding/content issue in {path}: {issue}")

    for memory_path, prefix in [
        (references / "ERROR_MEMORY.md", "CE"),
        (references / "NEW_KNOWLEDGE.md", "CE"),
    ]:
        duplicates = duplicate_ids(memory_path, prefix)
        if duplicates:
            failures.append(f"duplicate memory IDs in {memory_path}: {duplicates}")

    installed_skill = codex_skills_root / "chemical-engineering-expert"
    if installed_skill.is_dir():
        source_manifest = tree_manifest(source_skill)
        installed_manifest = tree_manifest(installed_skill)
        if source_manifest != installed_manifest:
            missing = sorted(set(source_manifest) - set(installed_manifest))
            extra = sorted(set(installed_manifest) - set(source_manifest))
            changed = sorted(
                key for key in set(source_manifest) & set(installed_manifest)
                if source_manifest[key] != installed_manifest[key]
            )
            failures.append(
                "chemical-engineering-expert source/install mismatch: "
                f"missing={missing}, extra={extra}, changed={changed}"
            )

    plugin_skill = workspace / "plugins" / "chemical-engineering-expert" / "skills" / "chemical-engineering-expert"
    if plugin_skill.is_dir():
        source_manifest = tree_manifest(source_skill)
        plugin_manifest = tree_manifest(plugin_skill)
        if source_manifest != plugin_manifest:
            failures.append("chemical-engineering-expert canonical/plugin skill mismatch")

    routes_path = workspace / "scripts" / "retrieval_routes.json"
    eval_path = workspace / "scripts" / "retrieval_eval_set.jsonl"
    try:
        routes = json.loads(routes_path.read_text(encoding="utf-8"))
        route_names = [item.get("name") for item in routes.get("routes", [])]
        if "chemical_expert_reasoning" not in route_names:
            failures.append("chemical_expert_reasoning route missing")
        if len(route_names) != len(set(route_names)):
            failures.append("duplicate retrieval route names")
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid retrieval route JSON: {exc}")

    try:
        eval_cases = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        eval_ids = [item.get("id") for item in eval_cases]
        if len(eval_ids) != len(set(eval_ids)):
            failures.append("duplicate retrieval evaluation IDs")
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid retrieval evaluation JSONL: {exc}")

    print(f"registry_entries={len(entries)}")
    print(f"canonical_roots={len(seen_roots)}")
    print(f"retrieval_eval_cases={len(eval_cases) if 'eval_cases' in locals() else 0}")
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"SUMMARY failures={len(failures)}")
        return 1
    print("SUMMARY failures=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


