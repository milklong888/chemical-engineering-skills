"""Real CLI checks using actual parser test receipts; never starts Aspen."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
EXPERT = SCRIPTS.parents[1] / 'chemical-engineering-expert'
sys.path.insert(0, str(EXPERT / 'scripts/tests'))
from release_test_support import configure_test_arguments, current_parser_receipt
configure_test_arguments('learning-admission-regression-')
EVALUATOR = EXPERT / 'scripts/evaluate_learning_eligibility.py'
STANDARD = EXPERT / 'references/STRICT_ACCEPTANCE_AND_LEARNING.md'
PARSER_RECEIPT = current_parser_receipt()
PARSER_SOURCE = SCRIPTS.parents[1] / 'aspen-plus-operations/scripts/aspen_evidence.py'
LESSON = 'Missing summary counts remain unresolved rather than being assumed zero.'


def reference(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest().upper()}


class LearningCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aspen-learning-admission-offline-')
        self.project = Path(self.temp.name)
        self.candidate = self.project / 'candidate.json'
        self.candidate.write_text(json.dumps({'lessons': [LESSON]}), encoding='utf-8')
        receipt = json.loads(PARSER_RECEIPT.read_text(encoding='utf-8'))
        self.assertEqual(receipt['status'], 'PASS_OFFLINE_DYNAMIC_UNVERIFIED')
        verified = {
            'unit_tests': receipt['unit_tests']['failures'] == 0 and receipt['unit_tests']['errors'] == 0,
            'legacy_probes': receipt['legacy_probes']['passed'] == receipt['legacy_probes']['count'],
            'real_formats': receipt['real_historical_format_fixtures']['passed'] == receipt['real_historical_format_fixtures']['count'],
        }
        standard = reference(STANDARD)
        common = {'relaxation_applied': False, 'relaxations': [], 'origin_scope': 'strict_case', 'provenance_state': 'strict_verified'}
        verification = {'passed': all(verified.values()), 'standard_sha256': standard['sha256'], 'required_checks': verified, 'receipt': reference(PARSER_RECEIPT)}
        self.manifest = {'schema': 'strict-learning-lineage-v1', 'lineage_complete': True, 'strict_standard': standard, 'root_id': 'rule', 'records': [
            {**common, 'id': 'source', 'kind': 'source', 'origin_scope': 'shared_source', 'acceptance_mode': 'source_only', 'parents': [], 'artifact': reference(PARSER_SOURCE)},
            {**common, 'id': 'result', 'kind': 'code_result', 'acceptance_mode': 'strict', 'parents': ['source'], 'artifact': reference(PARSER_RECEIPT), 'strict_verification': verification},
            {**common, 'id': 'rule', 'kind': 'rule_candidate', 'acceptance_mode': 'strict', 'parents': ['result'], 'artifact': reference(self.candidate), 'strict_verification': verification},
        ]}
        self.closure = {'schema': 'user-task-closure-event-v1', 'actor': 'user', 'event_type': 'close_task',
                        'task_id': 'SYNTHETIC-CLOSED-CLI-TEST', 'task_revision': 1,
                        'user_quote': '我确认本次任务已经结束，不再调整。',
                        'source_locator': 'synthetic://cli-test/user-close-1', 'source_message_id': 'SYNTHETIC-CLOSE-1',
                        'contains_change_request': False, 'test_fixture': True,
                        'boundary': 'Synthetic event for software testing, not an actual user closure.'}
        self.closure_path = self.project / 'synthetic_closure.json'
        self.closure_path.write_text(json.dumps(self.closure), encoding='utf-8')
        self.manifest.update(task_id=self.closure['task_id'], task_revision=1, task_state='closed',
                             reopened_after_closure=False, learning_channel='data_pattern',
                             task_closure={'evidence': reference(self.closure_path)})
        self.manifest_path = self.project / 'lineage.json'

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, script, args):
        return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / script), *args], cwd=self.project,
                              text=True, encoding='utf-8', capture_output=True, timeout=30)

    def evolve(self, manifest=True, extra=None, lesson_file=True):
        args = ['--project-name', 'SYNTHETIC-OFFLINE-ONLY', '--project-dir', str(self.project), '--accepted-evidence', 'Self-reported success does not grant eligibility']
        args += ['--lesson-file', str(self.candidate)] if lesson_file else ['--lesson', 'Unbound unrelated rule must not be admitted.']
        if manifest:
            self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
            args += ['--lineage-manifest', str(self.manifest_path), '--eligibility-module', str(EVALUATOR)]
        args += extra or []
        run = self.cli('self_evolve_skill.py', args)
        out = self.project / 'aspen_case_audit/evolution'
        records = list(out.glob('*.json')) if out.exists() else []
        record = json.loads(records[-1].read_text(encoding='utf-8')) if records else None
        return run, record, list(out.glob('*_candidate_patch.md')) if out.exists() else []

    def test_actual_strict_receipt_admits_review_not_canonical(self):
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(record['learning_eligible'])
        self.assertEqual(record['record_scope'], 'draft_review_only')
        self.assertTrue(record['task_closure_verified'])
        self.assertFalse(record['candidate_review_ready'])
        self.assertFalse(record['canonical_write_authorized'])
        self.assertFalse(record['default_retrieval'])
        self.assertEqual(len(patches), 1)
        self.assertIn(LESSON, patches[0].read_text(encoding='utf-8'))

    def test_success_claim_without_manifest_only_writes_audit(self):
        run, record, patches = self.evolve(manifest=False)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(record['record_scope'], 'case_audit_only')
        self.assertFalse(record['learning_eligible'])
        self.assertEqual(patches, [])

    def test_relaxed_ancestor_cannot_be_laundered_by_strict_root(self):
        self.manifest['records'][0].update(relaxation_applied=True, relaxations=['warning-waiver'], acceptance_mode='case_relaxed')
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertFalse(record['learning_eligible'])
        self.assertEqual(patches, [])

    def test_legacy_and_unknown_are_not_learning_candidates(self):
        self.manifest['records'][0]['provenance_state'] = 'legacy_unassessed'
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_missing_ancestor_and_incomplete_lineage_fail(self):
        self.manifest['records'][1]['parents'] = ['missing-node']
        self.manifest['lineage_complete'] = False
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_hash_drift_fails_without_touching_original_sources(self):
        self.manifest['records'][0]['artifact']['sha256'] = '0' * 64
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_admitted_other_rule_cannot_authorize_new_free_text(self):
        run, record, patches = self.evolve(lesson_file=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn('PROPOSED_RULE_NOT_BOUND_TO_ROOT_ARTIFACT', record['lineage_check']['rejection_reasons'])
        self.assertEqual(patches, [])

    def test_evaluator_from_arbitrary_cwd_cannot_replace_authority(self):
        fake = self.project / 'evaluate_learning_eligibility.py'
        fake.write_text('def evaluate(*a, **kw): return {"learning_eligible": True}', encoding='utf-8')
        run, record, patches = self.evolve(extra=['--eligibility-module', str(fake)])
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_canonical_and_archive_outputs_are_rejected(self):
        for output in [SCRIPTS.parent / 'evolution_records/SHOULD_NOT_WRITE', self.project / 'archives/candidates']:
            run = self.cli('self_evolve_skill.py', ['--project-name', 'TEST', '--lesson', LESSON, '--output-dir', str(output)])
            self.assertEqual(run.returncode, 2)
            self.assertFalse(output.exists())

    def test_no_project_output_never_defaults_to_skill(self):
        run = self.cli('self_evolve_skill.py', ['--project-name', 'TEST', '--lesson', LESSON])
        self.assertEqual(run.returncode, 2)
        self.assertIn('project', run.stderr)

    def test_event_log_retains_exact_paths_but_never_becomes_learning(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding='utf-8')
        run = self.cli('log_aspen_experience.py', ['--project-name', 'TEST', '--project-dir', str(self.project), '--event-type', 'success', '--phase', 'parser', '--category', 'code', '--problem-or-goal', 'Source-bound offline audit', '--evidence', str(PARSER_RECEIPT), '--lineage-manifest', str(self.manifest_path), '--eligibility-module', str(EVALUATOR), '--acceptance-mode', 'strict'])
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = list((self.project / 'aspen_learning_logs').glob('*.jsonl'))
        record = json.loads(rows[0].read_text(encoding='utf-8').splitlines()[0])
        self.assertFalse(record['learning_eligible'])
        self.assertFalse(record['default_retrieval'])
        self.assertEqual(record['evidence'], [str(PARSER_RECEIPT)])
        self.assertEqual(record['evidence_references'][0]['sha256'], reference(PARSER_RECEIPT)['sha256'])

    def test_relaxed_process_slice_is_case_audit_only(self):
        run = self.cli('record_process_slice.py', ['--project-name', 'TEST', '--project-dir', str(self.project), '--slice-id', 'SLICE-1', '--phase', 'diagnostic', '--scope', 'synthetic', '--acceptance-mode', 'case_relaxed', '--evidence', str(PARSER_RECEIPT)])
        self.assertEqual(run.returncode, 0, run.stderr)
        path = next((self.project / 'aspen_material_library').glob('*.jsonl'))
        record = json.loads(path.read_text(encoding='utf-8').splitlines()[0])
        self.assertEqual(record['record_scope'], 'case_audit_only')
        self.assertEqual(record['reported_acceptance_mode'], 'case_relaxed')
        self.assertFalse(record['learning_eligible'])
        self.assertFalse(record['default_retrieval'])

    def test_real_audit_jsonl_cannot_be_rewrapped_as_clean_source(self):
        run = self.cli('log_aspen_experience.py', ['--project-name', 'TEST', '--project-dir', str(self.project), '--event-type', 'success', '--phase', 'relaxed-case', '--category', 'diagnostic', '--problem-or-goal', 'A relaxed case remains excluded', '--acceptance-mode', 'case_relaxed'])
        self.assertEqual(run.returncode, 0, run.stderr)
        event = next((self.project / 'aspen_learning_logs').glob('*.jsonl'))
        # Attempted laundering: renamed extension and fresh manifest flags cannot
        # remove intrinsic case-audit/learning-ineligible content.
        renamed = self.project / 'apparently_clean_source.txt'
        renamed.write_bytes(event.read_bytes())
        self.manifest['records'][0]['artifact'] = reference(renamed)
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertFalse(record['learning_eligible'])
        self.assertEqual(patches, [])
        self.assertTrue(any('INTRINSIC' in reason for reason in record['lineage_check']['rejection_reasons']))

    def test_no_user_closure_has_no_draft_even_with_true_receipt(self):
        self.manifest.pop('task_closure')
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertFalse(record['task_closure_verified'])
        self.assertEqual(patches, [])

    def test_old_closure_after_reopen_cannot_start_learning(self):
        self.manifest.update(task_revision=2, task_state='active', reopened_after_closure=True)
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_optional_closure_cli_uses_same_current_identity(self):
        self.manifest.pop('task_closure')
        run, record, patches = self.evolve(extra=['--task-closure', str(self.closure_path)])
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(record['task_closure_verified'])
        self.assertEqual(len(patches), 1)

    def test_shallow_quote_in_policy_cannot_bind_as_positive_claim(self):
        self.manifest['records'][-1]['artifact'] = reference(SCRIPTS.parent / 'references/self_evolution_protocol.md')
        self.candidate.write_text(json.dumps({'lessons': ['check carefully']}), encoding='utf-8')
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])

    def test_chinese_exact_duplicate_is_hint_not_silent_deletion(self):
        import importlib.util
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location('evolve_chinese_test', SCRIPTS / 'self_evolve_skill.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        text = '每次更改必须检查物料守恒'
        self.assertEqual(module.overlap_score(text, text), 1.0)
        self.assertTrue(module.find_project_specific_terms('R201出口压力固定为5 MPa，塔板数30'))
        self.assertEqual(module.find_project_specific_terms('COM API NRTL'), [])
        self.candidate.write_text(json.dumps({'lessons': [text]}), encoding='utf-8')
        self.manifest['records'][-1]['artifact'] = reference(self.candidate)
        run, record, patches = self.evolve(extra=['--overlap-threshold', '0'])
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(record['lessons'][0]['already_likely_covered'])
        self.assertIn(text, patches[0].read_text(encoding='utf-8'))
        self.assertTrue(record['target_resolution']['exists'])
        self.assertEqual(patches[0].read_text(encoding='utf-8').count('\n## '), 1)

    def test_same_close_candidate_is_idempotent_without_new_patch(self):
        first, record, patches = self.evolve()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        paths = {path: reference(path)['sha256'] for path in (self.project / 'aspen_case_audit/evolution').glob('*') if path.is_file()}
        second, reused, repeated_patches = self.evolve()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('Reused ', second.stdout)
        self.assertEqual(patches, repeated_patches)
        self.assertEqual(paths, {path: reference(path)['sha256'] for path in paths})
        self.assertEqual(len(list((self.project / 'aspen_case_audit/evolution').glob('*.json'))), 1)

    def test_changed_quality_adds_review_version_not_rule_patch(self):
        first, record, patches = self.evolve()
        self.assertEqual(first.returncode, 0)
        before = reference(patches[0])
        # An unavailable/invalid review changes only review status, never the rule.
        second, reused, repeated = self.evolve(extra=['--candidate-review', str(self.project / 'missing_review.json')])
        self.assertEqual(second.returncode, 0)
        self.assertEqual(repeated, patches)
        self.assertEqual(reference(patches[0]), before)
        versions = list((self.project / 'aspen_case_audit/evolution/.candidate_slots').glob('*/reviews/*.json'))
        self.assertEqual(len(versions), 2)

    def user_principle_manifest(self):
        principle = '先冻结宏观设计目标，再展开实现细节；每次改动都回到整体约束复核。'
        root = {'learning_channel': 'prompt_principle', 'lessons': [principle],
                'rule_card': {'claim_type': 'behavior', 'knowledge_layer': 'L3',
                              'trigger': '开始化工设计或修改流程', 'observation': '用户要求宏观思考先于细节操作',
                              'mechanism': '先固定系统目标能防止局部实现偏离任务', 'action': principle,
                              'verification': '交付时对照被冻结的整体约束', 'boundary': '不提供工程参数或证明模拟已通过'}}
        self.candidate.write_text(json.dumps(root), encoding='utf-8')
        user = {'schema': 'user-instruction-source-v1', 'actor': 'user', 'user_quote': principle,
                'source_locator': 'synthetic://user-message/principle', 'source_message_id': 'SYNTHETIC-PRINCIPLE',
                'test_fixture': True, 'boundary': 'Synthetic source format, not an actual user principle capture.'}
        user_path = self.project / 'synthetic_user_instruction.json'
        user_path.write_text(json.dumps(user), encoding='utf-8')
        common = {'relaxation_applied': False, 'relaxations': [], 'origin_scope': 'shared_source', 'provenance_state': 'source_verified'}
        self.manifest['learning_channel'] = 'prompt_principle'
        self.manifest['records'] = [
            {**common, 'id': 'user', 'kind': 'user_instruction', 'acceptance_mode': 'source_only', 'parents': [], 'artifact': reference(user_path)},
            {**common, 'id': 'rule', 'kind': 'rule_candidate', 'acceptance_mode': 'source_only', 'parents': ['user'], 'artifact': reference(self.candidate)}]
        return root

    def test_user_macro_principle_source_only_needs_no_unrelated_parser_pass(self):
        self.user_principle_manifest()
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(record['lineage_check']['verified_evidence_kinds'], ['user_instruction_only'])
        self.assertEqual(record['lineage_check']['verified_receipts'], [])
        self.assertFalse(record['candidate_review_ready'])
        self.assertEqual(len(patches), 1)

    def test_behavior_source_cannot_be_switched_to_data_pattern(self):
        self.user_principle_manifest()
        self.manifest['learning_channel'] = 'data_pattern'
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])
        self.assertIn('BEHAVIOR_AUTHORITY_CANNOT_PROVE_DATA_PATTERN', record['lineage_check']['rejection_reasons'])

    def test_numeric_process_rule_cannot_hide_behind_behavior_label(self):
        root = self.user_principle_manifest()
        root['rule_card']['action'] = '将R201出口压力固定为5 MPa，所有项目均采用。'
        self.candidate.write_text(json.dumps(root), encoding='utf-8')
        self.manifest['records'][-1]['artifact'] = reference(self.candidate)
        run, record, patches = self.evolve()
        self.assertEqual(run.returncode, 2)
        self.assertEqual(patches, [])
        self.assertIn('TECHNICAL_CLAIM_NOT_ALLOWED_IN_USER_PRINCIPLE_BRANCH', record['lineage_check']['rejection_reasons'])

    def test_real_quality_no_change_writes_no_patch_and_is_idempotent(self):
        card = {'claim_type': 'deterministic_method', 'knowledge_layer': 'L2',
                'trigger': 'Parsing evidence', 'observation': 'Existing owner already handles missing counts',
                'mechanism': 'Missing data cannot prove zero', 'action': LESSON,
                'verification': 'Use current source-bound parser tests', 'boundary': 'Only parser behavior',
                'decision_change': 'No change to current owner', 'valid_for': ['Parser result interpretation'],
                'invalid_for': ['Physical design or simulation convergence']}
        self.candidate.write_text(json.dumps({'lessons': [LESSON], 'learning_channel': 'data_pattern', 'rule_card': card}), encoding='utf-8')
        self.manifest['records'][-1]['artifact'] = reference(self.candidate)
        baseline = SCRIPTS.parent / 'SKILL.md'
        snapshot = self.project / 'baseline_snapshot.md'
        snapshot.write_bytes(baseline.read_bytes())
        review = {'schema': 'chemical-evolution-review-v1', 'learning_channel': 'data_pattern', 'rule_card': card,
                  'placement': {'owner': 'aspen-document-driven-flowsheet', 'target_path': str(baseline), 'anchor': 'Hard Gates'},
                  'comparison': {'decision': 'no_change', 'reason': 'The current owner already contains the needed principle.', 'existing_refs': [reference(baseline)]},
                  'baseline': reference(baseline), 'candidate': reference(self.candidate), 'rollback_snapshot': reference(snapshot)}
        review_path = self.project / 'quality_review.json'
        review_path.write_text(json.dumps(review), encoding='utf-8')
        args = ['--candidate-review', str(review_path), '--quality-assessor', str(EVALUATOR.with_name('assess_evolution_candidate.py'))]
        run, record, patches = self.evolve(extra=args)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(record['quality_review']['decision'], 'not_improved')
        self.assertEqual(record['record_scope'], 'no_change')
        self.assertFalse(record['learning_eligible'])
        self.assertEqual(patches, [])
        first_paths = {path: reference(path)['sha256'] for path in (self.project / 'aspen_case_audit/evolution').glob('*.json')}
        again, _, patches = self.evolve(extra=args)
        self.assertEqual(again.returncode, 0)
        self.assertEqual(patches, [])
        self.assertEqual(first_paths, {path: reference(path)['sha256'] for path in first_paths})


if __name__ == '__main__':
    unittest.main()
