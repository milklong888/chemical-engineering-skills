"""Fail-closed lineage admission for learning candidates, not a truth oracle or writer."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

SCHEMA = 'strict-learning-lineage-v1'
EXCLUDED_STATES = {'case_relaxed', 'relaxed_lineage', 'legacy_unassessed', 'quarantined', 'unknown'}
AUDIT_SCHEMAS = {'aspen-case-audit-event-v2', 'aspen-case-process-slice-v2',
                 'aspen-learning-review-record-v2', 'strict-learning-eligibility-result-v1'}
QUALIFIED_STATES = {'strict_verified', 'source_verified', 'qualified', 'verified_by_user'}
LEARNING_CHANNELS = {'prompt_principle', 'data_pattern'}
ACTIVE_STANDARD = Path(__file__).resolve().parents[1] / 'references/STRICT_ACCEPTANCE_AND_LEARNING.md'


def resolved_reference(reference: dict, root: Path) -> dict:
    path = Path(reference['path'])
    return {'path': str((path if path.is_absolute() else root / path).resolve()),
            'sha256': reference['sha256'].upper()}


def inspect_task_closure(manifest: dict, root: Path) -> dict:
    """Require a source-bound current user close event, never assistant success."""
    reasons = []
    closure = manifest.get('task_closure', {})
    reference = closure.get('evidence') if isinstance(closure, dict) else None
    result = {'task_closure_verified': False, 'rejection_reasons': reasons}
    if not check_artifact(reference, root):
        reasons.append('TASK_CLOSURE_SOURCE_REQUIRED')
        return result
    try:
        resolved = resolved_reference(reference, root)
        event = json.loads(Path(resolved['path']).read_text(encoding='utf-8-sig'))
        task_id, revision = manifest.get('task_id'), manifest.get('task_revision')
        if not isinstance(task_id, str) or not task_id.strip() or type(revision) is not int or revision < 1:
            reasons.append('CURRENT_TASK_IDENTITY_REQUIRED')
        if not isinstance(event, dict):
            raise ValueError('Closure event must be an object')
        if event.get('schema') != 'user-task-closure-event-v1' or event.get('actor') != 'user' or event.get('event_type') != 'close_task':
            reasons.append('EXPLICIT_USER_CLOSE_EVENT_REQUIRED')
        if event.get('task_id') != task_id or type(event.get('task_revision')) is not int or event.get('task_revision') != revision:
            reasons.append('TASK_CLOSURE_REVISION_MISMATCH')
        if manifest.get('task_state') != 'closed' or manifest.get('reopened_after_closure') is not False:
            reasons.append('TASK_NOT_CLOSED_OR_REOPENED')
        quote, locator = event.get('user_quote'), event.get('source_locator')
        if not isinstance(quote, str) or not quote.strip() or not isinstance(locator, str) or not locator.strip() or not event.get('source_message_id'):
            reasons.append('USER_CLOSE_QUOTE_AND_LOCATOR_REQUIRED')
        else:
            # Explicitly saying no more edits is a close confirmation, not a
            # change request. Preserve all other conditional/unfinished signals.
            screened = re.sub(r'(?:不再|不用(?:再)?|无需(?:再)?|不需要(?:再)?|不要再)(?:进行)?(?:继续(?:进行)?(?:修改|改进|调整|改动)?|修改|改进|调整|改动|重开|重新打开)|不改了', '', quote)
            bad = re.search(r'[?？]|\b(?:if|when|after|once|unless)\b|(?:结束|完成)(?:后|以后|之后)|(?:如果|若|等你|待|改完以后).{0,24}(?:结束|完成)|尚未|未完成|未结束|还没|没有结束|没有完成|暂时|(?:还要|还需|仍需).{0,4}(?:改|补充|调整|检查|修复)|修改|改进|调整|但是|不过|继续|重开|重新打开', screened, re.I)
            explicit = re.search(r'(?:任务|项目|工作|本次|这次).{0,16}(?:已(?:经)?(?:完成|结束)|正式结束|结束了|完成了|结束|完成|结项)|(?:task|project|work).{0,20}(?:is complete|is finished|completed|closed)|^\s*(?:已(?:经)?(?:完成|结束)|可以结束了?|(?:结束|完成)了?|结项)[。.!！,，]?\s*$', screened, re.I)
            if bad or not explicit or event.get('contains_change_request') is not False:
                reasons.append('USER_CLOSURE_AMBIGUOUS_CONDITIONAL_OR_CHANGED')
        for key in ('task_id', 'task_revision', 'user_quote', 'source_locator'):
            if key in closure and closure[key] != event.get(key):
                reasons.append('CLOSURE_DECLARATION_SOURCE_MISMATCH')
        result.update({'event': event, 'evidence': resolved})
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        reasons.append('TASK_CLOSURE_UNREADABLE_OR_INVALID')
        result['error'] = str(exc)
    result['task_closure_verified'] = not reasons
    return result


def inspect_user_instruction(reference: dict, root: Path) -> dict:
    """Source authority for a user behavioral principle, not a technical oracle."""
    result = {'verified': False, 'rejection_reasons': []}
    try:
        resolved = resolved_reference(reference, root)
        value = json.loads(Path(resolved['path']).read_text(encoding='utf-8-sig'))
        if not isinstance(value, dict) or value.get('schema') != 'user-instruction-source-v1' or value.get('actor') != 'user':
            raise ValueError('A source-bound user instruction record is required')
        for key in ('user_quote', 'source_locator', 'source_message_id'):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ValueError('Missing original user field: ' + key)
        result.update(verified=True, source=resolved, source_message_id=value['source_message_id'],
                      source_locator=value['source_locator'], user_quote=value['user_quote'],
                      evidence_kind='user_instruction_only', technical_truth_verified=False)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        result['rejection_reasons'].append('USER_INSTRUCTION_SOURCE_UNVERIFIED')
        result['error'] = str(exc)
    return result


def check_artifact(reference: object, root: Path) -> bool:
    if not isinstance(reference, dict) or not isinstance(reference.get('path'), str):
        return False
    expected = reference.get('sha256')
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    path = Path(reference['path'])
    path = path if path.is_absolute() else root / path
    try:
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest().lower() == expected.lower()
    except OSError:
        return False


def intrinsic_exclusion(reference: object, root: Path) -> bool:
    """Read intrinsic local audit flags; a source_only wrapper cannot erase them.

    Check file content, not the suffix, so a renamed JSON/JSONL audit stays
    excluded. Do not recurse arbitrary test/standard prose as if it were a run.
    """
    if not isinstance(reference, dict) or not reference.get('path'):
        return False
    path = Path(reference['path'])
    path = path if path.is_absolute() else root / path
    try:
        with path.open('rb') as stream:
            prefix = stream.read(256).lstrip(b'\xef\xbb\xbf \r\n\t')
        if not prefix.startswith((b'{', b'[')):
            return False
        if path.stat().st_size > 20_000_000:
            return True  # Uninspectable large JSON cannot bypass intrinsic admission.
        raw = path.read_text(encoding='utf-8-sig')
        if not raw.lstrip().startswith(('{', '[')):
            return False
        try:
            loaded = json.loads(raw)
            rows = loaded if isinstance(loaded, list) else [loaded]
        except json.JSONDecodeError:
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    def excluded(value: object) -> bool:
        if isinstance(value, list):
            return any(excluded(item) for item in value)
        if not isinstance(value, dict):
            return False
        if '$schema' in value and ('properties' in value or '$defs' in value):
            return False  # Field definitions are not actual incident attestations.
        schema = value.get('schema', value.get('schema_version'))
        if schema == 'adaptive-error-memory-atomic-index-1.0':
            return True
        # Explicit metadata on a real record is binding even inside a wrapper.
        if value.get('learning_eligible') is False or value.get('relaxation_applied') is True:
            return True
        if any(isinstance(value.get(key), str) and value.get(key) in EXCLUDED_STATES | {'case_audit_only', 'audit_only'}
               for key in ('acceptance_mode', 'provenance_state', 'knowledge_status', 'effective_status', 'record_scope')):
            return True
        for key, child in value.items():
            # Explicit test expectations are examples, never actual outcomes.
            # These fields do not make an unknown document a valid receipt.
            if key in {'expected', 'expected_result', 'expected_output', 'expected_flags'}:
                continue
            if isinstance(child, (dict, list)) and excluded(child):
                return True
        return False
    return any(excluded(row) for row in rows)


def inspect_receipt(reference: dict, root: Path) -> dict:
    """Interpret only registered real receipt schemas, preserving proof scope."""
    result = {'verified': False, 'evidence_kind': None, 'rejection_reasons': [], 'receipt': resolved_reference(reference, root)}
    reasons = result['rejection_reasons']
    try:
        payload = json.loads(Path(result['receipt']['path']).read_text(encoding='utf-8-sig'))
        if not isinstance(payload, dict):
            raise ValueError('Receipt must be one object')
        schema = payload.get('schema', payload.get('schema_version'))
        result['schema'] = schema
        if schema == 'aspen-parser-refactor-validation-v1':
            result['evidence_kind'] = 'code_result'
            result['scope'] = 'offline_parser_code_behavior_not_simulation_or_engineering_acceptance'
            unit, legacy, formats = (payload.get(key, {}) for key in ('unit_tests', 'legacy_probes', 'real_historical_format_fixtures'))
            checks = {
                'unit_tests': type(unit.get('run')) is int and unit['run'] > 0 and unit.get('failures') == 0 and unit.get('errors') == 0,
                'legacy_probes': type(legacy.get('count')) is int and legacy['count'] > 0 and legacy.get('passed') == legacy['count'],
                'real_formats': type(formats.get('count')) is int and formats['count'] > 0 and formats.get('passed') == formats['count'],
            }
            if payload.get('status') != 'PASS_OFFLINE_DYNAMIC_UNVERIFIED' or payload.get('aspen_or_com_started') is not False or not all(checks.values()):
                reasons.append('RECEIPT_REPORTED_FAILED_UNKNOWN_OR_INCOMPLETE')
            files = payload.get('files')
            if not isinstance(files, list) or not files or not all(check_artifact(item, root) for item in files):
                reasons.append('RECEIPT_VALIDATED_INPUT_HASH_DRIFT_OR_MISSING')
            result['required_checks'] = checks
            result['validated_artifacts'] = [resolved_reference(item, root) for item in files or [] if isinstance(item, dict) and check_artifact(item, root)]
        elif schema == 'aspen_clean_delivery_audit/2':
            result['evidence_kind'] = 'simulation_result'
            result['scope'] = 'same_candidate_solver_clean_only_not_products_or_formal_delivery'
            if payload.get('passed') is not True or payload.get('simulation_clean') is not True or payload.get('source_unchanged') is not True or payload.get('operation_completed') is not True:
                reasons.append('RECEIPT_REPORTED_FAILED_UNKNOWN_OR_INCOMPLETE')
            checks = payload.get('gate_results')
            if not isinstance(checks, list) or not checks or any(item.get('passed') is not True for item in checks if isinstance(item, dict)) or any(not isinstance(item, dict) for item in checks):
                reasons.append('RECEIPT_GATES_FAILED_OR_MISSING')
            # Reuse the pure evidence owner for source/count/history replay.
            if not reasons:
                parser_path = Path(__file__).resolve().parents[2] / 'aspen-plus-operations/scripts/aspen_evidence.py'
                spec = importlib.util.spec_from_file_location('_learning_aspen_evidence', parser_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                control = payload.get('control_panel', {})
                histories = payload.get('histories', [])
                if not check_artifact(control, root) or not histories or not all(check_artifact(item, root) for item in histories):
                    reasons.append('RECEIPT_RAW_EVIDENCE_MISSING_OR_DRIFTED')
                else:
                    control_text = Path(resolved_reference(control, root)['path']).read_text(encoding='utf-8-sig')
                    replayed = []
                    for history in histories:
                        raw = Path(resolved_reference(history, root)['path']).read_bytes()
                        proof = history.get('encoding_evidence', {})
                        fallback = ()
                        if proof.get('fallback_eligible_for_current_history') is True and proof.get('fallback_roundtrip_verified') is True and proof.get('history_sha256') == history.get('sha256'):
                            fallback = (proof.get('codec'),) if isinstance(proof.get('codec'), str) else ()
                        decoded = module.decode_history_bytes(raw, verified_fallback_encodings=fallback)
                        replayed.append({**history, 'decode_verified': decoded['verified'], **module.inspect_history_text(decoded.get('text') or '', source=history['path'], source_sha256=history['sha256'])})
                    replay = module.evaluate_clean_gate(run=payload.get('run', {}), summary=module.parse_summary_counts(control_text),
                        control_messages=module.find_hard_messages(control_text), control_association=control.get('association'), histories=replayed,
                        block_statuses=payload.get('block_statuses'), artifacts=[payload.get('after_run_inp', {}), payload.get('after_run_bkp', {})])
                    if replay['passed'] is not True:
                        reasons.append('RECEIPT_RAW_EVIDENCE_REPLAY_FAILED')
                    result['replayed_gate'] = replay
            result['required_checks'] = {'solver_evidence_replayed': not reasons}
            source = {'path': payload.get('source'), 'sha256': payload.get('source_sha256')}
            if not check_artifact(source, root):
                reasons.append('RECEIPT_MODEL_SOURCE_HASH_DRIFT_OR_MISSING')
            result['validated_artifacts'] = [resolved_reference(source, root)] if check_artifact(source, root) else []
        else:
            reasons.append('UNREGISTERED_STRICT_RECEIPT_SCHEMA')
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
        reasons.append('STRICT_RECEIPT_UNREADABLE_OR_INVALID')
        result['error'] = str(exc)
    result['verified'] = not reasons
    return result


def evaluate(manifest: dict, *, base_dir: Path) -> dict:
    reasons = []
    def reject(code: str):
        if code not in reasons:
            reasons.append(code)
    if manifest.get('schema') != SCHEMA:
        reject('UNSUPPORTED_MANIFEST_SCHEMA')
    if manifest.get('lineage_complete') is not True:
        reject('LINEAGE_NOT_CONFIRMED_COMPLETE')
    closure_result = inspect_task_closure(manifest, base_dir)
    for reason in closure_result['rejection_reasons']:
        reject(reason)
    if manifest.get('learning_channel') not in LEARNING_CHANNELS:
        reject('LEARNING_CHANNEL_REQUIRED')
    if not check_artifact(manifest.get('strict_standard'), base_dir):
        reject('STRICT_STANDARD_IDENTITY_NOT_VERIFIED')
    else:
        try:
            expected_standard = hashlib.sha256(ACTIVE_STANDARD.read_bytes()).hexdigest()
            if manifest['strict_standard']['sha256'].lower() != expected_standard:
                reject('STRICT_STANDARD_IS_NOT_CURRENT_GOVERNANCE')
        except OSError:
            reject('CURRENT_STRICT_STANDARD_UNAVAILABLE')
    records = manifest.get('records')
    nodes = {}
    if not isinstance(records, list) or not records:
        reject('EMPTY_LINEAGE')
        records = []
    for node in records:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            reject('INVALID_LINEAGE_NODE')
            continue
        if node['id'] in nodes:
            reject('DUPLICATE_LINEAGE_ID')
        nodes[node['id']] = node
    root_node = nodes.get(manifest.get('root_id'), {})
    root_payload = {}
    if check_artifact(root_node.get('artifact'), base_dir):
        try:
            root_payload = json.loads(Path(resolved_reference(root_node['artifact'], base_dir)['path']).read_text(encoding='utf-8-sig'))
            if not isinstance(root_payload, dict):
                root_payload = {}
        except (OSError, UnicodeError, ValueError):
            pass
    card = root_payload.get('rule_card', {})
    card = card if isinstance(card, dict) else {}
    user_principle_only = manifest.get('learning_channel') == 'prompt_principle' and card.get('claim_type') == 'behavior'
    if card.get('claim_type') == 'behavior' and manifest.get('learning_channel') == 'data_pattern':
        reject('BEHAVIOR_AUTHORITY_CANNOT_PROVE_DATA_PATTERN')
    # Source-only user behavior is an additional branch, not the exclusive
    # source of prompt principles. Other claim types retain the strict receipt
    # and result-ancestry path below, with its original evidence-scope limits.
    if user_principle_only:
        if card.get('knowledge_layer') != 'L3':
            reject('USER_PRINCIPLE_MUST_BE_MACRO_L3')
        claim_text = '\n'.join(str(card.get(key, '')) for key in ('trigger', 'observation', 'mechanism', 'action', 'verification', 'boundary'))
        if re.search(r'\d+(?:\.\d+)?\s*(?:MPa|kPa|bar|kW|kJ|kmol|kg/h|t/h|°C|wt%|mol%)\b|(?:压比|回流比|温度|压力|转化率|容差)\D{0,8}\d|(?:设置|设定|固定|改为).{0,16}(?:RadFrac|NRTL|BLKSTAT|Run2|COM参数)', claim_text, re.I):
            reject('TECHNICAL_CLAIM_NOT_ALLOWED_IN_USER_PRINCIPLE_BRANCH')
    if root_payload.get('learning_channel') is not None and root_payload['learning_channel'] != manifest.get('learning_channel'):
        reject('ROOT_LEARNING_CHANNEL_MISMATCH')
    active, visited, tainted = set(), set(), set()
    verified_receipts = {}
    verified_user_sources = {}

    def walk(identity: str):
        if not isinstance(identity, str) or identity not in nodes:
            reject('MISSING_ANCESTOR')
            return
        if identity in active:
            reject('CYCLIC_LINEAGE')
            return
        if identity in visited:
            return
        active.add(identity)
        node = nodes[identity]
        if node.get('learning_eligible') is False:
            reject('EXPLICIT_LEARNING_EXCLUSION')
            tainted.add(identity)
        if node.get('relaxation_applied') is not False:
            reject('RELAXATION_USED_OR_UNKNOWN')
            tainted.add(identity)
        if node.get('relaxations') != []:
            reject('RELAXATION_LIST_NONEMPTY_OR_UNKNOWN')
            tainted.add(identity)
        if node.get('acceptance_mode') in EXCLUDED_STATES or node.get('provenance_state') in EXCLUDED_STATES:
            reject('EXCLUDED_ORIGIN_STATE')
            tainted.add(identity)
        if node.get('provenance_state') not in QUALIFIED_STATES:
            reject('PROVENANCE_STATE_NOT_QUALIFIED')
        if node.get('origin_scope') not in {'shared_source', 'strict_case'}:
            reject('UNQUALIFIED_ORIGIN_SCOPE')
        if not check_artifact(node.get('artifact'), base_dir):
            reject('ARTIFACT_HASH_OR_EXISTENCE_FAILED')
        elif intrinsic_exclusion(node.get('artifact'), base_dir):
            reject('INTRINSIC_ARTIFACT_EXCLUSION')
            tainted.add(identity)
        kind = node.get('kind')
        if kind in {'source', 'user_instruction'}:
            if node.get('acceptance_mode') != 'source_only':
                reject('SOURCE_MODE_INVALID')
            if kind == 'user_instruction' and check_artifact(node.get('artifact'), base_dir):
                user_source = inspect_user_instruction(node['artifact'], base_dir)
                for reason in user_source['rejection_reasons']:
                    reject(reason)
                if user_source['verified']:
                    verified_user_sources[identity] = user_source
        elif kind in {'code_result', 'simulation_result', 'summary', 'rule_candidate'}:
            if user_principle_only and identity == manifest.get('root_id') and kind == 'rule_candidate':
                if node.get('acceptance_mode') != 'source_only':
                    reject('USER_PRINCIPLE_ROOT_MUST_REMAIN_SOURCE_ONLY')
                verification = None
            else:
                verification = node.get('strict_verification', {})
            if verification is None:
                pass  # Source authority only; no invented strict PASS receipt.
            elif not isinstance(verification, dict):
                reject('NO_STRICT_PASS_EVIDENCE')
            else:
                verify_result_node(identity, node, verification, kind)
        else:
            reject('UNKNOWN_ARTIFACT_KIND')
        if user_principle_only and kind not in {'user_instruction', 'rule_candidate'}:
            reject('USER_PRINCIPLE_HAS_NONUSER_SUPPORT_ANCESTOR')
        parents = node.get('parents')
        if not isinstance(parents, list):
            reject('ANCESTRY_LIST_MISSING')
        else:
            if kind not in {'source', 'user_instruction'} and not parents:
                reject('DERIVED_ARTIFACT_ANCESTRY_REQUIRED')
            for parent in parents:
                walk(parent)
                if parent in tainted:
                    tainted.add(identity)
        active.remove(identity)
        visited.add(identity)

    def verify_result_node(identity, node, verification, kind):
            if node.get('acceptance_mode') != 'strict' or verification.get('passed') is not True:
                reject('NO_STRICT_PASS_EVIDENCE')
            if verification.get('standard_sha256') != manifest.get('strict_standard', {}).get('sha256'):
                reject('VERIFICATION_STANDARD_MISMATCH')
            required = verification.get('required_checks')
            if not isinstance(required, dict) or not required or any(v is not True for v in required.values()):
                reject('STRICT_CHECKS_INCOMPLETE_OR_FAILED')
            if not check_artifact(verification.get('receipt'), base_dir):
                reject('STRICT_RECEIPT_IDENTITY_NOT_VERIFIED')
            elif intrinsic_exclusion(verification.get('receipt'), base_dir):
                reject('STRICT_RECEIPT_HAS_EXCLUDED_ORIGIN')
                tainted.add(identity)
            else:
                interpreted = inspect_receipt(verification['receipt'], base_dir)
                for reason in interpreted['rejection_reasons']:
                    reject(reason)
                if kind in {'code_result', 'simulation_result'} and interpreted['evidence_kind'] != kind:
                    reject('STRICT_RECEIPT_EVIDENCE_KIND_MISMATCH')
                if (set(required) if isinstance(required, dict) else set()) != set(interpreted.get('required_checks', {})):
                    reject('STRICT_REQUIRED_CHECKS_DO_NOT_MATCH_RECEIPT_PROFILE')
                if interpreted['verified']:
                    verified_receipts[identity] = interpreted
                if kind in {'code_result', 'simulation_result'} and check_artifact(node.get('artifact'), base_dir):
                    target = resolved_reference(node['artifact'], base_dir)
                    if target not in [interpreted['receipt'], *interpreted.get('validated_artifacts', [])]:
                        reject('RESULT_ARTIFACT_NOT_BOUND_TO_RECEIPT')

    walk(manifest.get('root_id'))
    if nodes and set(nodes) != visited:
        reject('UNREACHABLE_OR_AMBIGUOUS_LINEAGE_RECORDS')
    root = nodes.get(manifest.get('root_id'), {})
    if root.get('kind') != 'rule_candidate':
        reject('ROOT_IS_NOT_A_RULE_CANDIDATE')
    evidence_nodes = [identity for identity in visited if nodes[identity].get('kind') in {'code_result', 'simulation_result'} and identity in verified_receipts]
    if user_principle_only and not verified_user_sources:
        reject('USER_INSTRUCTION_ANCESTOR_REQUIRED')
    elif not user_principle_only and not evidence_nodes:
        reject('VERIFIED_RESULT_ANCESTOR_REQUIRED')
    eligible = not reasons
    return {'schema': 'strict-learning-eligibility-result-v1', 'root_id': manifest.get('root_id'),
            'eligible_for_candidate_review': eligible, 'learning_eligible': eligible,
            'canonical_write_authorized': False, 'default_rule_eligible': False,
            'success_case_eligible': False, 'default_retrieval_eligible': False,
            'tainted_ids': sorted(tainted), 'visited_ids': sorted(visited), 'rejection_reasons': reasons,
            'task_id': manifest.get('task_id'), 'task_revision': manifest.get('task_revision'),
            'task_closure_verified': closure_result['task_closure_verified'], 'task_closure': closure_result,
            'learning_channel': manifest.get('learning_channel'),
            'root_artifact': resolved_reference(root['artifact'], base_dir) if check_artifact(root.get('artifact'), base_dir) else None,
            'verified_receipts': [{'node_id': key, **value} for key, value in verified_receipts.items()],
            'verified_user_sources': [{'node_id': key, **value} for key, value in verified_user_sources.items()],
            'verified_evidence_kinds': ['user_instruction_only'] if user_principle_only and verified_user_sources else sorted({verified_receipts[key]['evidence_kind'] for key in evidence_nodes}),
            'evidence_basis': 'user_instruction_only_not_technical_or_simulation_verification' if user_principle_only else 'registered_strict_result_receipts',
            'boundary': 'A passing lineage/receipt check admits human review only. It does not independently validate chemistry, authorize canonical mutation, or allow relaxed ancestry to be laundered.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.manifest.read_text(encoding='utf-8')), base_dir=args.manifest.resolve().parent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['eligible_for_candidate_review'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
