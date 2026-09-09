import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys

from evaluate_learning_eligibility import evaluate, intrinsic_exclusion

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS / 'tests'))
from release_test_support import configure_test_arguments, current_parser_receipt, external_artifact
configure_test_arguments('learning-eligibility-regression-')
STANDARD = SCRIPTS.parent / 'references/STRICT_ACCEPTANCE_AND_LEARNING.md'
RECEIPT = current_parser_receipt()
SOURCE = SCRIPTS.parents[1] / 'aspen-plus-operations/scripts/aspen_evidence.py'

def reference(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest().upper()}


class LearningGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='chemical-learning-gate-')
        self.root = Path(self.temp.name)
        self.root.joinpath('source.txt').write_text('{"candidate_rule":"Missing counts are not zero"}', encoding='utf-8')
        ref = reference(self.root / 'source.txt')
        closure = {'schema': 'user-task-closure-event-v1', 'actor': 'user', 'event_type': 'close_task',
                   'task_id': 'SYNTHETIC-CLOSURE-TEST', 'task_revision': 1,
                   'user_quote': '我确认本任务已经结束。', 'source_locator': 'synthetic://unit-test/message-1',
                   'source_message_id': 'SYNTHETIC-1', 'contains_change_request': False,
                   'test_fixture': True, 'boundary': 'Synthetic format test, not a real user task closure.'}
        self.closure_path = self.root / 'synthetic_user_closure.json'
        self.closure_path.write_text(json.dumps(closure), encoding='utf-8')
        common = {'relaxation_applied': False, 'relaxations': [], 'origin_scope': 'shared_source', 'provenance_state': 'strict_verified'}
        verification = {'passed': True, 'standard_sha256': reference(STANDARD)['sha256'],
                        'required_checks': {'unit_tests': True, 'legacy_probes': True, 'real_formats': True}, 'receipt': reference(RECEIPT)}
        self.good = {'schema': 'strict-learning-lineage-v1', 'lineage_complete': True,
                     'task_id': closure['task_id'], 'task_revision': 1, 'task_state': 'closed',
                     'reopened_after_closure': False, 'learning_channel': 'data_pattern',
                     'task_closure': {'evidence': reference(self.closure_path)},
                     'strict_standard': reference(STANDARD), 'root_id': 'candidate', 'records': [
            {'id': 'source', 'kind': 'source', 'acceptance_mode': 'source_only', 'parents': [], 'artifact': reference(SOURCE), **common},
            {'id': 'candidate', 'kind': 'rule_candidate', 'acceptance_mode': 'strict', 'parents': ['result'], 'artifact': ref, **common,
             'strict_verification': copy.deepcopy(verification)},
            {'id': 'result', 'kind': 'code_result', 'acceptance_mode': 'strict', 'parents': ['source'], 'artifact': reference(RECEIPT), **common,
             'strict_verification': copy.deepcopy(verification)}]}

    def tearDown(self):
        self.temp.cleanup()

    def result(self, case):
        return evaluate(case, base_dir=self.root)

    def test_strict_only_admits_review_not_canonical_writes(self):
        result = self.result(self.good)
        self.assertTrue(result['eligible_for_candidate_review'])
        self.assertFalse(result['canonical_write_authorized'])
        self.assertFalse(result['success_case_eligible'])

    def test_nonbehavior_prompt_principle_retains_strict_code_evidence_path(self):
        case = copy.deepcopy(self.good)
        case['learning_channel'] = 'prompt_principle'
        root_path = self.root / 'source.txt'
        root_path.write_text(json.dumps({
            'learning_channel': 'prompt_principle',
            'candidate_rule': 'Evidence completeness precedes acceptance claims.',
            'rule_card': {
                'claim_type': 'deterministic_method', 'knowledge_layer': 'L3',
                'boundary': 'Offline parser evidence handling only; not universal engineering or simulation validation.',
            },
        }), encoding='utf-8')
        case['records'][1]['artifact'] = reference(root_path)
        result = self.result(case)
        self.assertTrue(result['learning_eligible'], result['rejection_reasons'])
        self.assertEqual(result['verified_evidence_kinds'], ['code_result'])
        self.assertTrue(result['task_closure_verified'])
        self.assertFalse(result['canonical_write_authorized'])
        self.assertFalse(result['success_case_eligible'])

    def test_relaxed_parent_taints_strict_summary(self):
        for field, value in [('relaxation_applied', True), ('relaxations', ['warnings']), ('acceptance_mode', 'case_relaxed')]:
            case = copy.deepcopy(self.good)
            case['records'][0][field] = value
            result = self.result(case)
            self.assertFalse(result['learning_eligible'])
            self.assertIn('candidate', result['tainted_ids'])

    def test_user_acceptance_cannot_override_exclusion(self):
        case = copy.deepcopy(self.good)
        case['user_approved'] = True
        case['records'][0]['relaxation_applied'] = True
        self.assertFalse(self.result(case)['learning_eligible'])

    def test_explicit_inherited_no_learning_flag_is_binding(self):
        case = copy.deepcopy(self.good)
        case['records'][0]['learning_eligible'] = False
        self.assertFalse(self.result(case)['learning_eligible'])

    def test_wrapped_or_renamed_audit_cannot_launder_intrinsic_flags(self):
        for suffix, content in [('txt', json.dumps({'schema': 'aspen-case-audit-event-v2', 'learning_eligible': False})),
                                ('jsonl', json.dumps({'schema': 'aspen-case-process-slice-v2', 'acceptance_mode': 'case_audit_only'})+'\n')]:
            case = copy.deepcopy(self.good)
            path = self.root / ('renamed.' + suffix)
            path.write_text(content, encoding='utf-8')
            case['records'][0]['artifact'] = {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            result = self.result(case)
            self.assertIn('INTRINSIC_ARTIFACT_EXCLUSION', result['rejection_reasons'])
            self.assertIn('candidate', result['tainted_ids'])

    def test_rename_or_strict_rerun_does_not_clear_origin(self):
        case = copy.deepcopy(self.good)
        case['records'][0]['provenance_state'] = 'relaxed_lineage'
        case['records'][1]['strict_rerun_passed'] = True
        self.assertFalse(self.result(case)['learning_eligible'])

    def test_missing_or_string_false_is_not_no_relaxation(self):
        for value in (None, 'false', 0):
            case = copy.deepcopy(self.good)
            case['records'][0]['relaxation_applied'] = value
            self.assertFalse(self.result(case)['learning_eligible'])

    def test_missing_lineage_duplicate_and_cycle(self):
        for mutation in ('missing', 'duplicate', 'cycle'):
            case = copy.deepcopy(self.good)
            if mutation == 'missing': case['records'][1]['parents'] = ['absent']
            if mutation == 'duplicate': case['records'].append(copy.deepcopy(case['records'][0]))
            if mutation == 'cycle': case['records'][0]['parents'] = ['candidate']
            self.assertFalse(self.result(case)['learning_eligible'])

    def test_legacy_verified_without_new_qualification_is_excluded(self):
        case = copy.deepcopy(self.good)
        case['records'][0]['provenance_state'] = 'legacy_unassessed'
        case['records'][0]['old_status'] = 'verified'
        self.assertFalse(self.result(case)['learning_eligible'])

    def test_artifact_drift_and_failed_or_unknown_check(self):
        case = copy.deepcopy(self.good)
        case['records'][1]['strict_verification']['required_checks']['physics'] = None
        self.assertFalse(self.result(case)['learning_eligible'])
        self.root.joinpath('source.txt').write_text('changed', encoding='utf-8')
        self.assertFalse(self.result(self.good)['learning_eligible'])

    def test_no_closure_ambiguous_assistant_and_old_revision_never_admit(self):
        original = json.loads(self.closure_path.read_text())
        case = copy.deepcopy(self.good)
        case.pop('task_closure')
        self.assertFalse(self.result(case)['task_closure_verified'])
        for quote in ['好', '收到', '先这样', '任务结束了吗？', '完成了吗？', '任务结束后再总结', '任务改完以后结束', '任务已经结束，但是请修改结果', '任务完成了，还要改X', '任务没有完成', '任务完成，还要补充一个数据', '局部完成']:
            event = copy.deepcopy(original)
            event['user_quote'] = quote
            self.closure_path.write_text(json.dumps(event), encoding='utf-8')
            case = copy.deepcopy(self.good)
            case['task_closure']['evidence'] = reference(self.closure_path)
            self.assertFalse(self.result(case)['task_closure_verified'], quote)
        for quote in ['本次任务已经完成，不再调整。', '本次任务已结束，不用再修改。', '本任务已经完成，不需要继续。', '任务完成，不用再修改', '结束了', '已完成', '可以结束了']:
            event = {**original, 'user_quote': quote}
            self.closure_path.write_text(json.dumps(event), encoding='utf-8')
            case = copy.deepcopy(self.good)
            case['task_closure']['evidence'] = reference(self.closure_path)
            self.assertTrue(self.result(case)['task_closure_verified'], quote)
        self.closure_path.write_text(json.dumps(original), encoding='utf-8')
        for difference in [{'actor': 'assistant'}, {'event_type': 'local_delivery'}, {'contains_change_request': True}]:
            event = {**original, **difference}
            self.closure_path.write_text(json.dumps(event), encoding='utf-8')
            case = copy.deepcopy(self.good)
            case['task_closure']['evidence'] = reference(self.closure_path)
            self.assertFalse(self.result(case)['learning_eligible'])
        self.closure_path.write_text(json.dumps(original), encoding='utf-8')
        for change in [{'task_revision': 2}, {'reopened_after_closure': True}, {'task_state': 'active'}]:
            case = {**self.good, **change}
            self.assertFalse(self.result(case)['learning_eligible'])

    def test_actual_failed_receipt_and_offline_simulation_swap_are_rejected(self):
        failed = external_artifact('failed_simulation_receipt')
        self.assertFalse(json.loads(failed.read_text())['simulation_clean'])
        case = copy.deepcopy(self.good)
        case['records'][2]['kind'] = 'simulation_result'
        case['records'][2]['artifact'] = reference(failed)
        case['records'][2]['strict_verification']['receipt'] = reference(failed)
        self.assertIn('RECEIPT_REPORTED_FAILED_UNKNOWN_OR_INCOMPLETE', self.result(case)['rejection_reasons'])
        case = copy.deepcopy(self.good)
        case['records'][2]['kind'] = 'simulation_result'
        self.assertIn('STRICT_RECEIPT_EVIDENCE_KIND_MISMATCH', self.result(case)['rejection_reasons'])

    def test_actual_legacy_index_and_nested_audit_metadata_are_excluded(self):
        index = external_artifact('legacy_error_index')
        self.assertTrue(intrinsic_exclusion(reference(index), self.root))
        for payload in [{'schema_version': 'wrapper', 'events': [{'learning_eligible': False}]},
                        {'payload': {'record_scope': 'case_audit_only'}},
                        {'data': [{'knowledge_status': 'legacy_unassessed'}]}]:
            path = self.root / 'wrapped.txt'
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertTrue(intrinsic_exclusion(reference(path), self.root))

    def test_json_schema_and_test_expectations_are_not_real_incidents(self):
        for payload in [{'$schema': 'https://json-schema.org/draft/2020-12/schema', 'properties': {'learning_eligible': {'const': False}}},
                        {'case': 'negative', 'expected_result': {'learning_eligible': False}}]:
            path = self.root / 'definition.json'
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertFalse(intrinsic_exclusion(reference(path), self.root))

    def test_public_offline_simulation_swap_is_rejected(self):
        # Also run the non-private half of the retained optional regression.
        case = copy.deepcopy(self.good)
        case['records'][2]['kind'] = 'simulation_result'
        self.assertIn('STRICT_RECEIPT_EVIDENCE_KIND_MISMATCH', self.result(case)['rejection_reasons'])

    def test_public_nested_audit_metadata_are_excluded(self):
        # Also run the non-private half of the retained optional regression.
        for payload in [{'schema_version': 'wrapper', 'events': [{'learning_eligible': False}]},
                        {'payload': {'record_scope': 'case_audit_only'}},
                        {'data': [{'knowledge_status': 'legacy_unassessed'}]}]:
            path = self.root / 'wrapped.txt'
            path.write_text(json.dumps(payload), encoding='utf-8')
            self.assertTrue(intrinsic_exclusion(reference(path), self.root))

    def test_unregistered_prose_receipt_standard_and_vacuous_ancestry_fail(self):
        case = copy.deepcopy(self.good)
        case['records'][1]['strict_verification']['receipt'] = reference(STANDARD)
        self.assertIn('STRICT_RECEIPT_UNREADABLE_OR_INVALID', self.result(case)['rejection_reasons'])
        case = copy.deepcopy(self.good)
        case['strict_standard'] = reference(self.root / 'source.txt')
        self.assertIn('STRICT_STANDARD_IS_NOT_CURRENT_GOVERNANCE', self.result(case)['rejection_reasons'])
        case = copy.deepcopy(self.good)
        case['records'] = [case['records'][1]]
        case['records'][0]['parents'] = []
        self.assertIn('DERIVED_ARTIFACT_ANCESTRY_REQUIRED', self.result(case)['rejection_reasons'])
        for state in [None, 'new_unrecognized_state']:
            case = copy.deepcopy(self.good)
            case['records'][0]['provenance_state'] = state
            self.assertIn('PROVENANCE_STATE_NOT_QUALIFIED', self.result(case)['rejection_reasons'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
