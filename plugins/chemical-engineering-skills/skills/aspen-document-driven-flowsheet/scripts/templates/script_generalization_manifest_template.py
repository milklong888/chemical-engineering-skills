#!/usr/bin/env python3
"""Write project-local script-reuse audit or governed candidate review only."""

from __future__ import annotations

import argparse
import inspect
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Reuse the existing admission owner; never carry a copied validator in a template.
SCRIPTS = Path(__file__).resolve().parents[1]
if not (SCRIPTS / 'learning_admission.py').is_file():
    raise SystemExit('Run the installed template beside its reviewed learning_admission helper; do not infer another gate.')
sys.path.insert(0, str(SCRIPTS))
import learning_admission
from learning_admission import (bind_proposed_rule, case_audit_metadata,
                                lineage_admission, resolve_project_output, sha256,
                                begin_candidate_once, finish_candidate_once,
                                add_quality_review_version)


SUSPICIOUS_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"\b[A-Z]{2,}\d+[A-Z0-9]*\b"),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:bar|kpa|kg/h|kmol/h|wt%|mol%)\b", re.I),
]


def find_suspicious_terms(text: str) -> list[str]:
    terms: set[str] = set()
    for pattern in SUSPICIOUS_PATTERNS:
        terms.update(match.group(0) for match in pattern.finditer(text))
    return sorted(terms)


def script_is_bound(admission: dict, script: Path, expected_hash: str) -> bool:
    """The exact reviewed source must be in the admitted reachable lineage."""
    if admission.get('learning_eligible') is not True:
        return False
    root = Path(admission['manifest']['path']).parent
    for node in admission['manifest_snapshot']['records']:
        reference = node.get('artifact', {})
        raw = reference.get('path')
        if not isinstance(raw, str):
            continue
        target = Path(raw)
        target = (target if target.is_absolute() else root / target).resolve()
        if (target == script and reference.get('sha256', '').casefold() == expected_hash.casefold()
                and sha256(script) == expected_hash):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a script reuse manifest.")
    parser.add_argument("--script-path", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--created-or-modified-in-current-work", required=True, choices=["yes", "no"])
    parser.add_argument("--safe-reuse-scope", required=True)
    parser.add_argument("--do-not-reuse-for", required=True)
    parser.add_argument("--target-location", required=True)
    parser.add_argument("--out-dir", default='', help='Existing CLI alias: explicit project-local audit/candidate output directory.')
    parser.add_argument('--project-dir', default='', help='Project root; default output is aspen_case_audit/script_reuse.')
    parser.add_argument('--lineage-manifest', help='Hash-bound strict lineage, including the exact source script and proposed scope.')
    parser.add_argument('--task-closure', help='User close_task event JSON; the shared helper binds its hash and the central owner verifies task/version.')
    parser.add_argument('--eligibility-module', help='Explicit reviewed central evaluator override for isolated integration tests.')
    parser.add_argument('--candidate-review', help='Existing central candidate-quality proposal JSON; not a publication authorization.')
    parser.add_argument('--quality-assessor', help='Explicit reviewed central assessor override for isolated integration tests.')
    args = parser.parse_args()

    try:
        out_dir = resolve_project_output(args.project_dir, args.out_dir, 'aspen_case_audit/script_reuse')
        script_path = Path(args.script_path).expanduser().resolve()
        source_hash = sha256(script_path)
        text = script_path.read_text(encoding='utf-8-sig')
    except (ValueError, OSError, UnicodeError) as exc:
        parser.error(str(exc))
    suspicious = find_suspicious_terms(text)

    admission_kwargs = {'evaluator_path': args.eligibility_module}
    closure_adapter_available = 'task_closure_path' in inspect.signature(lineage_admission).parameters
    if args.task_closure and not closure_adapter_available:
        admission = {'learning_eligible': False, 'eligible_for_candidate_review': False,
                     'rejection_reasons': ['SHARED_TASK_CLOSURE_ADAPTER_UNAVAILABLE']}
    else:
        if args.task_closure:
            admission_kwargs['task_closure_path'] = args.task_closure
        admission = lineage_admission(args.lineage_manifest, **admission_kwargs)
    admission = bind_proposed_rule(admission, [args.safe_reuse_scope, args.do_not_reuse_for])
    source_bound = script_is_bound(admission, script_path, source_hash)
    reasons = list(admission.get('rejection_reasons', []))
    if admission.get('task_closure_verified') is not True:
        reasons.append('TASK_CLOSURE_NOT_VERIFIED')
    if admission.get('learning_eligible') and not source_bound:
        reasons.append('SCRIPT_NOT_BOUND_TO_ADMITTED_LINEAGE')
    if args.created_or_modified_in_current_work != 'yes':
        reasons.append('NOT_CREATED_OR_MODIFIED_IN_CURRENT_WORK')
    if suspicious:
        reasons.append('PROJECT_SPECIFIC_TERMS_REQUIRE_REVIEW')
    if sha256(script_path) != source_hash:
        reasons.append('SCRIPT_CHANGED_DURING_REVIEW')
    lineage_eligible = admission.get('learning_eligible') is True and not reasons
    effective_admission = {**admission, 'learning_eligible': lineage_eligible,
                           'eligible_for_candidate_review': lineage_eligible,
                           'rejection_reasons': reasons}
    quality_helper = getattr(learning_admission, 'quality_review', None)
    if callable(quality_helper):
        quality = quality_helper(args.candidate_review, lineage_result=effective_admission,
                                 base_dir=Path(args.project_dir).resolve() if args.project_dir else out_dir,
                                 assessor_path=args.quality_assessor)
    else:
        # Fail closed during an incomplete installation; no local quality oracle.
        quality = {'decision': 'needs_review_fields' if lineage_eligible else 'audit_only',
                   'candidate_review_ready': False, 'canonical_write_authorized': False,
                   'reasons': ['SHARED_QUALITY_REVIEW_UNAVAILABLE'],
                   'missing_fields': ['central_candidate_quality_review']}
    ready = lineage_eligible and quality.get('candidate_review_ready') is True
    no_change = lineage_eligible and 'NO_CHANGE_NEEDED' in quality.get('reasons', [])

    record = {
        'schema': 'aspen-script-reuse-review-v2',
        **case_audit_metadata(effective_admission),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "project_name": args.project_name,
        "script_path": str(script_path),
        'script_sha256': source_hash,
        'source_bound_to_lineage': source_bound,
        "created_or_modified_in_current_work": args.created_or_modified_in_current_work,
        "suspicious_project_specific_terms": suspicious,
        "original_project_values_removed": 'not_proven_by_lexical_scan',
        "inputs_parameterized": "review_required",
        "outputs_and_evidence": "review_required",
        "tested_on_current_slice": "review_required",
        "safe_reuse_scope": args.safe_reuse_scope,
        "do_not_reuse_for": args.do_not_reuse_for,
        "target_location": args.target_location,
        'promotion_decision': 'no_change' if no_change else 'candidate_review_only' if ready else 'draft_review_only' if lineage_eligible else 'audit_only',
        'record_scope': 'case_audit_only' if no_change else 'learning_candidate_review_only' if ready else 'draft_review_only' if lineage_eligible else 'case_audit_only',
        'acceptance_mode': 'case_audit_only' if no_change else 'candidate_review_only' if ready else 'draft_review_only' if lineage_eligible else 'case_audit_only',
        'lineage_eligible': lineage_eligible,
        'task_closure_verified': admission.get('task_closure_verified') is True,
        'learning_eligible': ready,
        'candidate_review_ready': ready,
        'quality_review': quality,
        'rejection_reasons': reasons,
        'generalization_proven': False,
        'candidate_quality_review_required': not ready,
        'default_retrieval': False,
        'default_retrieval_eligible': False,
        'canonical_write_authorized': False,
        'source_script': {'path': str(Path(__file__).resolve()), 'sha256': sha256(Path(__file__))},
    }

    slot = None
    if lineage_eligible:
        # The shared owner determines closure/revision/root/channel/target
        # identity and verifies prior artifacts; this template does not copy it.
        slot = begin_candidate_once(out_dir, lineage_result=effective_admission,
                                    target={'kind': 'script_reuse',
                                            'target_location': args.target_location,
                                            'source_script': str(script_path)})
        if slot['status'] == 'incomplete_or_drifted':
            parser.exit(2, 'Existing candidate slot is incomplete or changed; preserve it for review: ' + slot.get('error', '') + '\n')
        review_version = add_quality_review_version(slot, quality)
        if slot['status'] == 'reused':
            print(json.dumps({'status': 'reused', 'candidate_identity_sha256': slot['identity_sha256'],
                              'artifacts': slot['artifacts'], 'quality_review_version': review_version,
                              'current_quality_decision': quality.get('decision'),
                              'canonical_write_authorized': False, 'default_retrieval_eligible': False},
                             ensure_ascii=False))
            return 0
        record.update(candidate_identity=slot['identity'], candidate_identity_sha256=slot['identity_sha256'],
                      initial_quality_review_version=review_version)
        out = out_dir / f"{slot['prefix']}_reuse_manifest.json"
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        out = out_dir / f"{script_path.stem}_{stamp}_reuse_manifest.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if slot is not None:
        finish_candidate_once(slot, [out])
    print(f"Wrote {out}")
    # Zero means an authorized post-closure draft/review record was created,
    # never that a candidate was promoted or a chemical claim proven.
    return 0 if lineage_eligible else 2


if __name__ == "__main__":
    raise SystemExit(main())
