#!/usr/bin/env python3
"""Create a reviewable self-evolution record for an Aspen skill.

The script is intentionally conservative: it writes evidence records and
candidate patch text, but it never edits SKILL.md directly.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable

from learning_admission import (bind_proposed_rule, evidence_references, lineage_admission,
                                quality_review, resolve_project_output, sha256, begin_candidate_once,
                                finish_candidate_once, add_quality_review_version)


SECTION_HINTS = {
    "authority-resume": ["SKILL.md Authority First", "references/skill_routing_graph.md Authority Gateways"],
    "source-taskbook-gate": ["references/source_taskbook_and_gate_protocol.md", "references/quick_router.md", "scripts/templates/source_taskbook_gate_audit_template.py"],
    "document-extraction": ["Non-Negotiable Rules", "Workflow", "Review Gates"],
    "flowsheet-architecture": ["SKILL.md Operational Architecture", "references/aspen_workflow_playbooks.md"],
    "error-repair": ["aspen-flowsheet-error-repair/SKILL.md", "references/aspen_zero_warning_repair.md"],
    "section-boundary": ["aspen-two-section-flowsheet/SKILL.md", "aspen-two-section-flowsheet references/case cards"],
    "scaffold": ["references/aspen_workflow_playbooks.md", "references/aspen_convergence_trials.md"],
    "kinetics": ["Non-Negotiable Rules", "Aspen Failure Patterns To Check", "Final Audit Commands"],
    "unit-conversion": ["Non-Negotiable Rules", "Aspen Failure Patterns To Check"],
    "property-method": ["SKILL.md Hard Gates", "references/source_taskbook_and_gate_protocol.md", "local Aspen graph ch03 property route"],
    "tower": ["aspen-tower-optimization-workflow/SKILL.md", "references/aspen_distillation_patterns.md"],
    "recycle": ["Non-Negotiable Rules", "Review Gates", "Aspen Failure Patterns To Check"],
    "pressure": ["aspen-pressure-pfd-delivery/SKILL.md", "Review Gates", "Aspen Failure Patterns To Check"],
    "pressure-hx": ["aspen-pressure-pfd-delivery/SKILL.md", "standards graph pressure/HX nodes"],
    "separator": ["Workflow", "Review Gates", "Aspen Failure Patterns To Check"],
    "convergence": ["Workflow", "Aspen Failure Patterns To Check"],
    "control-panel": ["references/aspen_zero_warning_repair.md", "references/aspen_failure_patterns.md"],
    "calculator-design-spec": ["references/aspen_builtin_solve_fit_tools.md", "SKILL.md Priority Operating Defaults"],
    "equipment-standards": ["chemical-equipment-selection-audit/SKILL.md", "equipment/standards knowledge graph nodes"],
    "delivery": ["Workflow", "Review Gates", "Final Audit Commands", "Output Standard"],
    "packaging": ["Workflow", "Output Standard"],
    "skill-routing": ["references/skill_routing_graph.md", "SKILL.md Cross-Skill Routing"],
    "self-evolution": ["references/self_evolution_protocol.md", "scripts/self_evolve_skill.py"],
    "material-library": ["references/material_library_protocol.md", "project aspen_material_library slice templates"],
    "script-reuse": ["references/material_library_protocol.md", "project-local reusable_scripts", "candidate skill scripts"],
    "delivery-preflight": ["references/material_library_protocol.md", "aspen-pressure-pfd-delivery/SKILL.md", "references/aspen_audit_gates.md"],
    "open-run-readiness": ["references/open_run_readiness_protocol.md", "aspen-flowsheet-error-repair/SKILL.md", "delivery gates"],
    "path-portability": ["references/delivery_portability_and_plausibility_gates.md", "references/open_run_readiness_protocol.md", "scripts/templates/path_migration_readiness_template.py"],
    "physical-plausibility": ["references/delivery_portability_and_plausibility_gates.md", "SKILL.md Hard Gates", "references/aspen_workflow_playbooks.md"],
}

PROJECT_SPECIFIC_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]*[-_]?\d+[A-Z0-9]*(?![A-Za-z0-9])"),
    re.compile(r"(?<![0-9])\d+(?:\.\d+)?\s*(?:MPa|bar|kpa|pa|°?c|k|kmol(?:/h)?|kg(?:/h)?|t/h|wt%|mol%|m²|m2|kW)(?![A-Za-z])", re.I),
    re.compile(r"(?:塔板数|级数|压力|温度|回流比|处理量|流量)\s*[:：=为]?\s*\d+(?:\.\d+)?"),
]

# Preserve category CLI names, but resolve each draft to one real current owner.
# Detailed engineering targets remain subject to the independent quality review.
_CATEGORY_SECTION = {
    'authority-resume': 'Authority First', 'source-taskbook-gate': 'Authority First',
    'document-extraction': 'Authority First', 'skill-routing': 'Fast Entry',
    'self-evolution': 'Learning Log And Self-Evolution', 'delivery': 'Output Standard',
    'packaging': 'Output Standard', 'delivery-preflight': 'Hard Gates',
    'physical-plausibility': 'Hard Gates', 'kinetics': 'Hard Gates',
    'unit-conversion': 'Hard Gates', 'property-method': 'Hard Gates',
}
SECTION_HINTS = {category: ['SKILL.md#' + _CATEGORY_SECTION.get(category, 'Operational Architecture')]
                 for category in SECTION_HINTS}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "_", value)
    value = value.strip("._-")
    return value or "project"


def tokenize(value: str) -> set[str]:
    value = unicodedata.normalize('NFKC', value).casefold()
    tokens = set(re.findall(r"[a-z][a-z0-9_-]{1,}", value))
    for run in re.findall(r'[\u4e00-\u9fff]+', value):
        tokens.update(run[index:index + 2] for index in range(max(len(run) - 1, 1)))
    return tokens


def overlap_score(lesson: str, skill_text: str) -> float:
    lesson_tokens = tokenize(lesson)
    if not lesson_tokens:
        return 0.0
    skill_tokens = tokenize(skill_text)
    return len(lesson_tokens & skill_tokens) / len(lesson_tokens)


def find_project_specific_terms(text: str) -> list[str]:
    terms: set[str] = set()
    for pattern in PROJECT_SPECIFIC_PATTERNS:
        terms.update(match.group(0) for match in pattern.finditer(text))
    return sorted(terms)


def redact_local_paths(text: str) -> str:
    """Legacy display-only helper. Never apply to a machine evidence ledger."""
    text = re.sub(r"[A-Za-z]:\\[^\n`]+", "<local-path>", text)
    text = re.sub(r"/(?:Users|home|mnt|workspace)/[^\n`]+", "<local-path>", text)
    return text


def read_optional_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def ensure_list(values: Iterable[str] | None) -> list[str]:
    return [value for value in values or [] if value.strip()]


def build_record(args: argparse.Namespace, skill_dir: Path, skill_text: str) -> dict:
    lessons = ensure_list(args.lesson)
    if not lessons and args.lesson_file:
        lesson_path = Path(args.lesson_file)
        raw = lesson_path.read_text(encoding="utf-8")
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list):
                lessons = [str(item) for item in loaded]
            elif isinstance(loaded, dict):
                lessons = [str(item) for item in loaded.get("lessons", [])]
        except json.JSONDecodeError:
            lessons = [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]

    if not lessons:
        raise SystemExit("At least one --lesson or --lesson-file entry is required.")

    evidence = ensure_list(args.evidence)
    lesson_records = []
    for lesson in lessons:
        specific_terms = find_project_specific_terms(lesson)
        score = overlap_score(lesson, skill_text)
        lesson_records.append(
            {
                "lesson": lesson,
                "category": args.category,
                "severity": args.severity,
                "suggested_sections": SECTION_HINTS.get(args.category, ["SKILL.md#Operational Architecture"]),
                "skill_overlap_score": round(score, 3),
                "already_likely_covered": score >= args.overlap_threshold,
                "duplicate_hint_only": True,
                "duplicate_search_scope": 'Current SKILL.md only; scope/negation/equivalent references require review',
                "project_specific_terms": specific_terms,
                "promotion_risk": "review_generalization" if specific_terms else "not_assessed",
                "scope_expansion_signals": [term for term in ('所有项目', '任何情况下', '一律', 'always', 'all projects') if term in lesson.casefold()],
            }
        )

    return {
        "project_name": args.project_name,
        "project_dir": str(Path(args.project_dir).resolve()) if args.project_dir else "",
        "skill_dir": str(skill_dir),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "category": args.category,
        "severity": args.severity,
        "success_review": {
            "task_completed": args.task_completed or "",
            "accepted_evidence": args.accepted_evidence or "",
            "initial_uncertainty": args.initial_uncertainty or "",
            "decisive_evidence": args.decisive_evidence or "",
            "root_cause": args.root_cause or "",
            "final_fix": args.final_fix or "",
            "weaker_attempts": args.weaker_attempts or "",
            "boundary": args.boundary or "",
            "skill_target": args.skill_target or "",
            "candidate_rule": args.candidate_rule or "",
        },
        "evidence": evidence,
        "lessons": lesson_records,
        "policy": {
            "edits_skill_directly": False,
            "promote_only_reusable_patterns": True,
            "do_not_promote_project_specific_facts": True,
        },
    }


def render_markdown(record: dict) -> str:
    lines = [
        f"# {'Learning Candidate Review' if record.get('learning_eligible') else 'Case Audit Only'}: {record['project_name']}",
        "",
        f"- Generated: `{record['generated_at']}`",
        f"- Category: `{record['category']}`",
        f"- Severity: `{record['severity']}`",
        f"- Skill: `{record['skill_dir']}`",
        f"- Scope: `{record.get('record_scope')}`; default retrieval: `false`; canonical write: `false`",
        f"- Learning eligible for candidate review: `{record.get('learning_eligible', False)}`",
    ]
    if record.get("project_dir"):
        lines.append(f"- Project: `{record['project_dir']}`")
    lines.append("")

    lines.append("## Evidence")
    if record["evidence"]:
        for item in record["evidence"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- No evidence supplied. Do not promote until evidence is attached.")
    lines.append("")

    review = record.get("success_review", {})
    if any(review.values()):
        lines.append("## Submitted Review Claims (not independent acceptance evidence)")
        labels = [
            ("task_completed", "Task completed"),
            ("accepted_evidence", "Accepted evidence"),
            ("initial_uncertainty", "Initial wrong assumption or uncertainty"),
            ("decisive_evidence", "First decisive diagnostic evidence"),
            ("root_cause", "Root cause mechanism"),
            ("final_fix", "Fix that actually worked"),
            ("weaker_attempts", "Why earlier attempts were weaker"),
            ("boundary", "Boundary where principle does not apply"),
            ("skill_target", "Skill/reference target"),
            ("candidate_rule", "Candidate rule or patch"),
        ]
        for key, label in labels:
            value = review.get(key, "")
            if value:
                lines.append(f"- {label}: {value}")
        lines.append("")

    lines.append("## Lessons")
    for item in record["lessons"]:
        lines.append(f"- {item['lesson']}")
        lines.append(f"  - Suggested sections: {', '.join(item['suggested_sections'])}")
        lines.append(f"  - Already likely covered: `{item['already_likely_covered']}`")
        lines.append(f"  - Promotion risk: `{item['promotion_risk']}`")
        if item["project_specific_terms"]:
            lines.append(f"  - Terms to generalize before promotion: `{', '.join(item['project_specific_terms'])}`")
    lines.append("")

    lines.append("## Promotion Rule")
    lines.append(
        "Promote only concise, evidence-backed rules that apply beyond this project. "
        "Keep project-specific route, stream, pressure, split, and kinetic values in the project package."
    )
    lines.append("")
    return "\n".join(lines)


def render_candidate_patch(record: dict) -> str:
    if record.get('learning_eligible') is not True:
        raise ValueError('A strict, fully bound lineage is required before candidate generation.')
    lines = [
        f"# Candidate SKILL.md Patch: {record['project_name']}",
        "",
        "Review this text manually. Do not paste project-specific values without generalizing them.",
        "",
    ]

    review = record.get("success_review", {})
    target = record.get('target_resolution', {})
    if target.get('exists') is not True:
        lines.extend(['Target requires review; no applicable patch is proposed.', ''])
        return "\n".join(lines)
    lines.extend([f"## {target['path']}#{target['section']}",
                  f"Baseline SHA256: `{target['sha256']}`", '',
                  'Draft only; duplicate and scope flags require review, not automatic deletion.', ''])
    rules = [review['candidate_rule']] if review.get('candidate_rule') else [item['lesson'] for item in record['lessons']]
    for rule in rules:
        lines.append('- ' + rule)
    if review.get('boundary'):
        lines.append('Boundary: ' + review['boundary'])
    lines.append('')
    return "\n".join(lines)


def resolve_target(record: dict) -> dict:
    proposed = record['success_review'].get('skill_target') or record['lessons'][0]['suggested_sections'][0]
    file_text, separator, section = proposed.partition('#')
    path = Path(file_text)
    path = path if path.is_absolute() else Path(record['skill_dir']) / path
    try:
        text = path.read_text(encoding='utf-8-sig')
        headings = {line.lstrip('#').strip() for line in text.splitlines() if line.startswith('#')}
        exists = bool(separator and section in headings)
        return {'requested': proposed, 'path': str(path.resolve()), 'section': section,
                'exists': exists, 'sha256': sha256(path), 'status': 'existing_target_pending_review' if exists else 'target_section_unresolved'}
    except (OSError, UnicodeError):
        return {'requested': proposed, 'exists': False, 'status': 'target_file_unresolved'}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an Aspen skill self-evolution record and candidate patch.")
    parser.add_argument("--skill-dir", default=str(Path(__file__).resolve().parents[1]), help="Read-only skill directory containing SKILL.md.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-dir", default="")
    parser.add_argument("--category", default="process", choices=sorted(set(SECTION_HINTS) | {"process"}))
    parser.add_argument("--severity", default="medium", choices=["info", "low", "medium", "high", "blocker"])
    parser.add_argument("--lesson", action="append", help="Reusable lesson to consider for promotion.")
    parser.add_argument("--lesson-file", help="UTF-8 text or JSON file with lessons.")
    parser.add_argument("--evidence", action="append", help="Evidence path or short evidence note.")
    parser.add_argument("--task-completed", help="Deep review: completed task.")
    parser.add_argument("--accepted-evidence", help="Deep review: accepted evidence.")
    parser.add_argument("--initial-uncertainty", help="Deep review: initial wrong assumption or uncertainty.")
    parser.add_argument("--decisive-evidence", help="Deep review: first decisive diagnostic evidence.")
    parser.add_argument("--root-cause", help="Deep review: root cause mechanism.")
    parser.add_argument("--final-fix", help="Deep review: fix that actually worked.")
    parser.add_argument("--weaker-attempts", help="Deep review: why earlier attempts were weaker.")
    parser.add_argument("--boundary", help="Deep review: where the principle does not apply.")
    parser.add_argument("--skill-target", help="Deep review: target skill/reference for promotion.")
    parser.add_argument("--candidate-rule", help="Deep review: exact candidate rule or patch.")
    parser.add_argument("--output-dir", default="", help="Explicit project-local output; default is <project-dir>/aspen_case_audit/evolution.")
    parser.add_argument('--lineage-manifest', help='Hash-bound strict lineage required to create a learning candidate or patch.')
    parser.add_argument('--eligibility-module', help='Explicit absolute reviewed canonical source module for offline integration tests; never searched in cwd.')
    parser.add_argument('--task-closure', help='Hashed same-task/revision explicit user close event; otherwise use task_closure in the manifest.')
    parser.add_argument('--candidate-review', help='Optional post-closure atomic quality/validation review JSON; never replaces bound lesson text.')
    parser.add_argument('--quality-assessor', help='Explicit trusted canonical assessor path for offline tests.')
    parser.add_argument("--overlap-threshold", type=float, default=0.72)
    args = parser.parse_args()

    try:
        out_dir = resolve_project_output(args.project_dir, args.output_dir, 'aspen_case_audit/evolution')
    except ValueError as exc:
        parser.error(str(exc))
    skill_dir = Path(args.skill_dir).resolve()
    skill_md = skill_dir / "SKILL.md"
    skill_text = read_optional_text(skill_md)
    if not skill_text:
        raise SystemExit(f"Could not read SKILL.md from {skill_md}")

    record = build_record(args, skill_dir, skill_text)
    admission = lineage_admission(args.lineage_manifest, evaluator_path=args.eligibility_module, task_closure_path=args.task_closure)
    candidate_texts = [item['lesson'] for item in record['lessons']] + [record['success_review'].get(key, '') for key in ('candidate_rule', 'boundary', 'skill_target')]
    admission = bind_proposed_rule(admission, candidate_texts)
    eligible = admission.get('learning_eligible') is True and admission.get('task_closure_verified') is True
    record['target_resolution'] = resolve_target(record)
    quality = quality_review(args.candidate_review, lineage_result=admission,
                             base_dir=Path(args.project_dir).resolve() if args.project_dir else out_dir,
                             assessor_path=args.quality_assessor)
    no_change = quality.get('decision') in {'not_improved', 'no_change'} or 'NO_CHANGE_NEEDED' in quality.get('reasons', [])
    write_patch = eligible and not no_change
    record.update({'schema': 'aspen-learning-review-record-v2',
                   'record_scope': 'no_change' if eligible and no_change else 'learning_candidate_review_only' if eligible and quality.get('candidate_review_ready') else 'draft_review_only' if eligible else 'case_audit_only',
                   'learning_eligible': eligible and not no_change, 'default_retrieval': False,
                   'default_retrieval_eligible': False, 'canonical_write_authorized': False,
                   'acceptance_mode': 'candidate_review_only' if eligible else 'case_audit_only',
                   'lineage_check': admission, 'self_reported_success_is_acceptance_evidence': False,
                   'task_closure_verified': admission.get('task_closure_verified') is True,
                   'learning_channel': admission.get('learning_channel'),
                   'candidate_review_ready': quality.get('candidate_review_ready') is True,
                   'quality_review': quality,
                   'source_script': {'path': str(Path(__file__).resolve()), 'sha256': sha256(Path(__file__))},
                   'evidence_references': evidence_references(record['evidence'], base_dir=Path(args.project_dir).resolve() if args.project_dir else out_dir)})
    out_dir.mkdir(parents=True, exist_ok=True)

    slot = None
    if eligible:
        target = record['target_resolution']
        target_identity = {'producer': 'self_evolve_skill', 'path': target.get('path', target.get('requested')),
                           'section': target.get('section')}
        slot = begin_candidate_once(out_dir, lineage_result=admission, target=target_identity)
        if slot['status'] == 'incomplete_or_drifted':
            raise SystemExit('Existing candidate is incomplete or changed; no overwrite or duplicate patch allowed: ' + slot.get('error', ''))
        review_version = add_quality_review_version(slot, quality)
        if slot['status'] == 'reused':
            for item in slot['artifacts']:
                print('Reused ' + item['path'])
            print('Quality review version: ' + review_version['path'])
            print('Existing rule patch retained; current quality decision: ' + str(quality.get('decision')))
            return 0
        record['candidate_identity'] = slot['identity']
        record['candidate_identity_sha256'] = slot['identity_sha256']
        record['quality_review_version'] = review_version

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    slug = slugify(args.project_name)
    base = out_dir / (slot['prefix'] if slot else f"{timestamp}_{slug}")

    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    patch_path = out_dir / f"{base.name}_candidate_patch.md"

    with json_path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    with md_path.open('x', encoding='utf-8') as stream:
        stream.write(render_markdown(record))
    if write_patch:
        with patch_path.open('x', encoding='utf-8') as stream:
            stream.write(render_candidate_patch(record))
    if eligible:
        finish_candidate_once(slot, [json_path, md_path] + ([patch_path] if write_patch else []))

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if write_patch:
        print(f"Wrote {patch_path}")
        print('Post-closure draft generated; quality decision: ' + str(quality.get('decision')) + '; canonical write remains forbidden.')
    elif eligible and no_change:
        print('No change needed; project review retained and no rule patch generated.')
    else:
        print('Case audit saved; no learning candidate or patch generated: ' + ', '.join(admission.get('rejection_reasons', [])))
    return 0 if eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
