"""Project-local audit storage and hash-bound admission to candidate review only."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

SKILLS_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVALUATOR = SKILLS_ROOT / 'chemical-engineering-expert/scripts/evaluate_learning_eligibility.py'
REVIEWED_SOURCE_EVALUATOR = DEFAULT_EVALUATOR  # compatibility alias; no source-machine exception
DEFAULT_ASSESSOR = DEFAULT_EVALUATOR.with_name('assess_evolution_candidate.py')
REVIEWED_SOURCE_ASSESSOR = DEFAULT_ASSESSOR  # same trusted package only
FORBIDDEN_COMPONENTS = {'archives', 'archive', 'backups', 'backup', 'source_snapshot', 'knowledge_pack', '.git', 'knowledge_vector_index'}


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def _safe_project_path(path: Path) -> Path:
    path = path.expanduser().resolve()
    lowered = [part.casefold() for part in path.parts]
    if path == Path(path.anchor) or path == Path.home().resolve():
        raise ValueError('A concrete project-local directory is required.')
    if path.is_relative_to(SKILLS_ROOT.resolve()) or '.codex' in lowered:
        raise ValueError('Canonical installed skills and Codex directories are not project audit destinations.')
    if any(part in FORBIDDEN_COMPONENTS or part.startswith(('backup_', 'archive_')) for part in lowered):
        raise ValueError('Archives, backups and source snapshots cannot receive active audit/candidate output.')
    if any(part in {'skill_packages', 'plugins', 'external_sources'} for part in lowered):
        raise ValueError('Canonical/source/plugin trees cannot receive project learning output.')
    # The workspace also keeps domain skill source mirrors below /skills.
    if 'skills' in lowered:
        raise ValueError('A skill tree cannot be used as a project audit destination.')
    return path


def resolve_project_output(project_dir: str, output_dir: str, default_folder: str) -> Path:
    if not project_dir and not output_dir:
        raise ValueError('Specify --project-dir or an explicit project-local --output-dir; writing into a skill is forbidden.')
    project = _safe_project_path(Path(project_dir)) if project_dir else None
    output = _safe_project_path(Path(output_dir)) if output_dir else project / default_folder
    output = _safe_project_path(output)
    if project is not None and not output.is_relative_to(project):
        raise ValueError('--output-dir must remain inside --project-dir.')
    return output


def evidence_references(items: list[str], *, base_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for raw in items:
        path = Path(raw).expanduser()
        path = path if path.is_absolute() else base_dir / path
        try:
            exists = path.is_file()
        except (OSError, ValueError):
            exists = False
        rows.append({'raw': raw, 'path': str(path.resolve()) if exists else None,
                     'sha256': sha256(path) if exists else None,
                     'binding_status': 'FILE_HASHED' if exists else 'UNRESOLVED_REFERENCE_OR_SELF_REPORTED_NOTE'})
    return rows


def lineage_admission(manifest_path: str | None, *, evaluator_path: str | None = None,
                      task_closure_path: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {'learning_eligible': False, 'eligible_for_candidate_review': False,
                             'canonical_write_authorized': False, 'default_retrieval': False,
                             'default_retrieval_eligible': False, 'task_closure_verified': False,
                             'rejection_reasons': []}
    if not manifest_path:
        result['rejection_reasons'] = ['LINEAGE_MANIFEST_REQUIRED_FOR_CANDIDATE']
        return result
    path = Path(manifest_path).expanduser().resolve()
    evaluator = Path(evaluator_path).expanduser() if evaluator_path else DEFAULT_EVALUATOR
    if not evaluator.is_absolute():
        result['rejection_reasons'] = ['EVALUATOR_PATH_MUST_BE_EXPLICIT_ABSOLUTE']
        return result
    evaluator = evaluator.resolve()
    if evaluator not in {DEFAULT_EVALUATOR.resolve()}:
        result['rejection_reasons'] = ['EVALUATOR_NOT_IN_TRUSTED_CANONICAL_LOCATIONS']
        return result
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw.decode('utf-8-sig'))
        if task_closure_path:
            closure_path = Path(task_closure_path).expanduser()
            closure_path = (closure_path if closure_path.is_absolute() else path.parent / closure_path).resolve()
            supplied_closure = {'evidence': {'path': str(closure_path), 'sha256': sha256(closure_path)}}
            if manifest.get('task_closure') and manifest['task_closure'].get('evidence') != supplied_closure['evidence']:
                raise ValueError('Explicit closure conflicts with the frozen manifest; update the current revision ledger first.')
            manifest['task_closure'] = supplied_closure
        evaluator_hash = sha256(evaluator)
        spec = importlib.util.spec_from_file_location('trusted_strict_learning_admission', evaluator)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        evaluated = module.evaluate(manifest, base_dir=path.parent)
        if sha256(evaluator) != evaluator_hash or hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(raw).digest():
            raise ValueError('Evaluator or lineage manifest changed during evaluation.')
        result.update(evaluated)
        if evaluated.get('task_closure_verified') is not True:
            result.update(learning_eligible=False, eligible_for_candidate_review=False,
                          rejection_reasons=[*evaluated.get('rejection_reasons', []), 'TASK_CLOSURE_NOT_VERIFIED_BY_CURRENT_GATE'])
        result.update({'manifest': {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest().upper()},
                       'manifest_snapshot': manifest, 'evaluator': {'path': str(evaluator), 'sha256': evaluator_hash},
                       'default_retrieval': False, 'canonical_write_authorized': False})
    except Exception as exc:
        result.update(learning_eligible=False, eligible_for_candidate_review=False,
                      rejection_reasons=['LINEAGE_EVALUATION_UNAVAILABLE_OR_INVALID'], error=str(exc))
    return result


def bind_proposed_rule(admission: dict[str, Any], texts: list[str]) -> dict[str, Any]:
    """The admitted root must contain the exact submitted rule, not an unrelated pass."""
    if admission.get('learning_eligible') is not True:
        return admission
    manifest = admission['manifest_snapshot']
    root = next(node for node in manifest['records'] if node['id'] == manifest['root_id'])
    raw_path = Path(root['artifact']['path'])
    path = raw_path if raw_path.is_absolute() else Path(admission['manifest']['path']).parent / raw_path
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest().casefold() != root['artifact']['sha256'].casefold():
            raise ValueError('Candidate root changed after lineage evaluation.')
        content = raw.decode('utf-8-sig')
        # Explicit candidate fields only: a quotation, rejection example, or
        # substring in a policy document is not the proposed positive claim.
        obj = json.loads(content)
        if not isinstance(obj, dict):
            raise ValueError('Candidate root must be a structured claim object')
        bound_values = []
        for key in ('lessons', 'candidate_rule', 'boundary', 'skill_target', 'safe_reuse_scope', 'forbidden_reuse_scope'):
            value = obj.get(key)
            if isinstance(value, str):
                bound_values.append(value)
            elif isinstance(value, list):
                bound_values.extend(item for item in value if isinstance(item, str))
        missing = [text for text in texts if text.strip() and text not in bound_values]
        if missing:
            return {**admission, 'learning_eligible': False, 'eligible_for_candidate_review': False,
                    'rejection_reasons': [*admission.get('rejection_reasons', []), 'PROPOSED_RULE_NOT_BOUND_TO_ROOT_ARTIFACT'],
                    'unbound_proposed_text': missing}
        return {**admission, 'proposed_rule_binding': {'path': str(path.resolve()), 'sha256': sha256(path), 'status': 'EXACT_CLAIM_FIELD_IN_ADMITTED_ROOT'}}
    except Exception as exc:
        return {**admission, 'learning_eligible': False, 'eligible_for_candidate_review': False,
                'rejection_reasons': [*admission.get('rejection_reasons', []), 'CANDIDATE_ROOT_BINDING_FAILED'], 'binding_error': str(exc)}


def quality_review(review_path: str | None, *, lineage_result: dict[str, Any], base_dir: Path,
                   assessor_path: str | None = None) -> dict[str, Any]:
    """Call the central quality owner; never substitute its JSON for bound rules."""
    result = {'decision': 'needs_review_fields', 'candidate_review_ready': False,
              'canonical_write_authorized': False, 'missing_fields': [], 'reasons': [], 'next_actions': []}
    if lineage_result.get('learning_eligible') is not True or lineage_result.get('task_closure_verified') is not True:
        return {**result, 'decision': 'audit_only', 'reasons': ['USER_CLOSURE_AND_STRICT_LINEAGE_REQUIRED']}
    if not review_path:
        return {**result, 'missing_fields': ['candidate_review'],
                'reasons': ['DRAFT_ONLY_QUALITY_REVIEW_NOT_SUPPLIED'],
                'next_actions': ['Provide an atomic, source-bound candidate review after user task closure.']}
    path = Path(review_path).expanduser()
    path = (path if path.is_absolute() else base_dir / path).resolve()
    assessor = Path(assessor_path).expanduser() if assessor_path else DEFAULT_ASSESSOR
    if not assessor.is_absolute() or assessor.resolve() not in {DEFAULT_ASSESSOR.resolve()}:
        return {**result, 'reasons': ['ASSESSOR_NOT_IN_TRUSTED_CANONICAL_LOCATIONS']}
    try:
        raw, assessor_hash = path.read_bytes(), sha256(assessor)
        proposal = json.loads(raw.decode('utf-8-sig'))
        spec = importlib.util.spec_from_file_location('trusted_evolution_quality_review', assessor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assessed = module.assess(proposal, base_dir=path.parent, lineage_result=lineage_result)
        if path.read_bytes() != raw or sha256(assessor) != assessor_hash:
            raise ValueError('Review proposal or assessor changed during assessment')
        return {**assessed, 'canonical_write_authorized': False,
                'review_artifact': {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest().upper()},
                'assessor': {'path': str(assessor.resolve()), 'sha256': assessor_hash}}
    except Exception as exc:
        return {**result, 'reasons': ['QUALITY_REVIEW_UNAVAILABLE_OR_INVALID'], 'error': str(exc)}


def begin_candidate_once(output_dir: Path, *, lineage_result: dict[str, Any], target: dict | str) -> dict[str, Any]:
    """Reserve one task-local candidate identity, or verify/reuse its artifacts."""
    if lineage_result.get('learning_eligible') is not True or lineage_result.get('task_closure_verified') is not True:
        raise ValueError('A current explicit user close and qualified lineage are required.')
    closure = lineage_result.get('task_closure', {}).get('evidence', {})
    root = lineage_result.get('root_artifact', {})
    identity = {'task_id': lineage_result.get('task_id'), 'task_revision': lineage_result.get('task_revision'),
                'closure_sha256': closure.get('sha256'), 'learning_channel': lineage_result.get('learning_channel'),
                'root_id': lineage_result.get('root_id'), 'root_sha256': root.get('sha256'), 'target': target}
    if not identity['closure_sha256'] or not identity['root_sha256']:
        raise ValueError('Closure/root identity is incomplete; old evaluator output cannot reserve a candidate.')
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    output_dir = _safe_project_path(output_dir)
    # Full identity remains in the receipt; short path components avoid the
    # Windows legacy path limit in otherwise ordinary project/temp directories.
    slot_dir = output_dir / '.candidate_slots' / digest[:24]
    slot_dir.parent.mkdir(parents=True, exist_ok=True)
    slot = {'identity': identity, 'identity_sha256': digest.upper(), 'output_dir': str(output_dir),
            'slot_dir': str(slot_dir), 'prefix': 'candidate_' + digest[:24]}
    try:
        slot_dir.mkdir()
        return {**slot, 'status': 'new'}
    except FileExistsError:
        try:
            receipt_path = slot_dir / 'artifacts.json'
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt.get('identity') != identity or receipt.get('completed') is not True or not receipt.get('artifacts'):
                raise ValueError('Identity receipt incomplete or inconsistent')
            for item in receipt['artifacts']:
                path = Path(item['path']).resolve()
                if not path.is_relative_to(output_dir) or not path.is_file() or sha256(path) != item['sha256']:
                    raise ValueError('Published candidate artifact missing or changed')
            return {**slot, 'status': 'reused', 'artifacts': receipt['artifacts'],
                    'receipt': {'path': str(receipt_path), 'sha256': sha256(receipt_path)}}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {**slot, 'status': 'incomplete_or_drifted', 'error': str(exc)}


def finish_candidate_once(slot: dict[str, Any], artifacts: list[Path]) -> dict[str, Any]:
    if slot.get('status') != 'new':
        raise ValueError('Only the newly reserved owner may finalize candidate artifacts')
    output_dir, slot_dir = Path(slot['output_dir']).resolve(), Path(slot['slot_dir'])
    references = []
    for artifact in artifacts:
        path = artifact.resolve()
        if not path.is_relative_to(output_dir) or not path.is_file():
            raise ValueError('Candidate artifacts must exist inside the reserved project output')
        references.append({'path': str(path), 'sha256': sha256(path)})
    if not references:
        raise ValueError('No candidate artifacts were written')
    receipt = {'schema': 'evolution-candidate-once-v1', 'identity': slot['identity'], 'completed': True,
               'artifacts': references, 'canonical_write_authorized': False, 'default_retrieval_eligible': False}
    path = slot_dir / 'artifacts.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    return {'path': str(path), 'sha256': sha256(path)}


def add_quality_review_version(slot: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    """An updated assessment adds a review version, never another rule patch."""
    if slot.get('status') not in {'new', 'reused'}:
        raise ValueError('Cannot review an incomplete candidate slot')
    payload = {'schema': 'evolution-candidate-quality-version-v1', 'candidate_identity': slot['identity'],
               'quality_review': quality, 'canonical_write_authorized': False, 'default_retrieval_eligible': False}
    data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    digest = hashlib.sha256(data).hexdigest()
    directory = Path(slot['slot_dir']) / 'reviews'
    directory.mkdir(exist_ok=True)
    path = directory / (digest[:24] + '.json')
    try:
        with path.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError('Review identity collision or changed review artifact')
    return {'path': str(path), 'sha256': digest.upper()}


def case_audit_metadata(admission: dict[str, Any]) -> dict[str, Any]:
    return {'record_scope': 'case_audit_only', 'learning_eligible': False, 'default_retrieval': False,
            'default_retrieval_eligible': False, 'canonical_write_authorized': False,
            'acceptance_mode': 'case_audit_only', 'lineage_check': admission,
            'self_reported_success_is_acceptance_evidence': False}

