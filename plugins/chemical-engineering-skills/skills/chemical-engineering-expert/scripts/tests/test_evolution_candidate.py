"""Independent forward tests with synthetic evidence; no Aspen or publication.

Positive observations and fact oracles are independently calculated from input
quantities. A synthetic lineage result isolates assess() from the separate
closure/lineage verifier; it is never represented as a real admission receipt.
Failing tests are intentional defect detectors, not expected-failure passes.
"""
from __future__ import annotations
import copy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import assess_evolution_candidate as assessor

from release_test_support import configure_test_arguments, current_parser_receipt, case_directory_name
REPORT_ROOT = configure_test_arguments('evolution-forward-regression-').artifact_root
RUN_ROOT = REPORT_ROOT / datetime.now().strftime('%Y%m%d_%H%M%S_%f')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return ref(path)


def ref(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest().upper()}


class Scenario:
    def __init__(self, root, channel='data_pattern'):
        self.root = root
        root.mkdir(parents=True, exist_ok=False)
        self.channel = channel
        self.base = root / 'baseline_owner.md'
        self.base.write_text('# Synthetic owner\n## Rule\nBaseline implementation.\n', encoding='utf-8')
        self.candidate = root / 'candidate.json'
        write_json(self.candidate, {'synthetic': True})
        self.rollback = root / 'independent_rollback.md'
        self.rollback.write_bytes(self.base.read_bytes())
        self.input = {'synthetic': True, 'task_id': 'SYN-TASK', 'case_id': 'HOLDOUT-1',
                      'feed_a_kg_h': 12.0, 'feed_b_kg_h': 8.0, 'method': 'exact-addition',
                      'product_target_kg_h': 20.0, 'solver_tolerance': 1e-6, 'software_version': 'SYN-1'}
        self.input_ref = write_json(root / 'input.json', self.input)
        self.basis = {'synthetic': True, 'analysis_target': 'synthetic_arithmetic_logic',
                      'method': self.input['method'], 'boundary': 'Two feeds and one outlet, fixed mass-flow basis.',
                      'goal': {'outlet_kg_h': self.input['product_target_kg_h']},
                      'tolerance': {'balance_kg_h': self.input['solver_tolerance']},
                      'version': self.input['software_version']}
        self.basis_ref = write_json(root / 'basis.json', self.basis)
        # Quantity fact comes from arithmetic on the frozen input, not proposed rule text.
        total = self.input['feed_a_kg_h'] + self.input['feed_b_kg_h']
        self.old = {'schema': 'evolution-observation-v1', 'synthetic': True, 'case_id': self.input['case_id'],
                    'input_sha256': self.input_ref['sha256'], 'basis_sha256': self.basis_ref['sha256'],
                    'subject_sha256': ref(self.base)['sha256'],
                    'values': {'outlet_kg_h': total, 'balance_residual_kg_h': total - 20.0,
                               'iterations': 20, 'passed': True}}
        self.new = copy.deepcopy(self.old)
        self.new['values']['iterations'] = 10
        self.oracle = {'schema': 'evolution-json-oracle-v1', 'synthetic': True,
                       'authority': 'Independent arithmetic: outlet = feed_a + feed_b; input target and tolerance frozen.',
                       'hard_requirements': [{'pointer': '/values/outlet_kg_h', 'op': 'eq', 'expected': total},
                                             {'pointer': '/values/balance_residual_kg_h', 'op': 'eq', 'expected': 0.0}],
                       'metrics': [{'pointer': '/values/iterations', 'direction': 'lower'}]}
        if channel == 'prompt_principle':
            # Independent frozen decision facts: one unit supports 40 kg/h,
            # the input requires 20 kg/h and unnecessary units have no benefit.
            self.input['single_unit_capacity_kg_h'] = 40.0
            self.input_ref = write_json(root / 'input.json', self.input)
            expected_action = 'retain_single_unit' if total <= self.input['single_unit_capacity_kg_h'] else 'capacity_review'
            for observation in (self.old, self.new):
                observation['input_sha256'] = self.input_ref['sha256']
            self.old['values'].update(selected_action='add_parallel_units', selected_units=6)
            self.new['values'].update(selected_action=expected_action, selected_units=1)
            self.oracle['hard_requirements'].append({'pointer': '/values/selected_action', 'op': 'eq', 'expected': expected_action})
            self.oracle['metrics'] = []
        self.plan = {'schema': 'evolution-evaluation-plan-v1', 'synthetic': True,
                     'baseline_sha256': ref(self.base)['sha256'], 'development_case_ids': ['DEV-UNSEEN'], 'basis': self.basis_ref,
                     'required_dimensions': ['conservation', 'same-basis'],
                     'cases': [{'id': 'HOLDOUT-1', 'split': 'holdout',
                                'dimensions': ['conservation', 'same-basis'], 'input': self.input_ref}]}
        self.report = {'schema': 'evolution-evaluation-result-v1', 'synthetic': True,
                       'baseline_sha256': ref(self.base)['sha256'], 'candidate_sha256': ref(self.candidate)['sha256'],
                       'cases': [{'id': 'HOLDOUT-1', 'input_sha256': self.input_ref['sha256']}]}
        self.proposal = {'schema': 'chemical-evolution-review-v1', 'synthetic': True, 'learning_channel': channel,
                        'rule_card': {'trigger': 'Compare an iteration-reduction candidate on one frozen basis.',
                         'observation': 'Synthetic paired iteration count differs while arithmetic facts must not.',
                         'mechanism': 'A claimed speedup cannot compensate for changed conditions or failed conservation.',
                         'action': 'Use paired observations only when identities and hard facts match.',
                         'verification': 'Independent input-derived conservation oracle and unchanged tolerance.',
                         'boundary': 'Synthetic test evidence is not an engineering rule or real task closure.',
                         'knowledge_layer': 'L3' if channel == 'prompt_principle' else 'L2',
                         'decision_change': 'Reject incomparable faster outputs instead of promoting them.',
                         'claim_type': 'behavior' if channel == 'prompt_principle' else 'deterministic_method',
                         'valid_for': ['same-input paired synthetic tests'], 'invalid_for': ['changed target or solver basis']},
                        'placement': {'owner': 'synthetic-owner', 'target_path': str(self.base), 'anchor': '## Rule'},
                        'comparison': {'decision': 'specialize', 'reason': 'Bound a previously unchecked comparison.',
                                       'existing_refs': [ref(self.base)]},
                        'baseline': ref(self.base), 'candidate': ref(self.candidate), 'rollback_snapshot': ref(self.rollback)}
        write_json(self.candidate, {'schema': 'chemical-evolution-candidate-v1', 'synthetic': True,
                                   'learning_channel': channel, 'rule_card': copy.deepcopy(self.proposal['rule_card'])})
        self.proposal['candidate'] = ref(self.candidate)
        self.report['candidate_sha256'] = ref(self.candidate)['sha256']
        self.new['subject_sha256'] = ref(self.candidate)['sha256']
        self.lineage = {'synthetic': True, 'boundary': 'Injected result isolates assessor, not real closure proof.',
                        'learning_eligible': True, 'task_closure_verified': True, 'learning_channel': channel,
                        'root_artifact': ref(self.candidate)}

    def save(self):
        oracle_ref = write_json(self.root / 'oracle.json', self.oracle)
        for name, observation in [('baseline', self.old), ('candidate', self.new)]:
            raw_values = getattr(self, 'candidate_raw_values_override', observation['values']) if name == 'candidate' else observation['values']
            observation['raw_evidence'] = write_json(self.root / (name + '_raw_evidence.json'),
                    {'synthetic': True, 'observation_source': 'Independent test-generated factual arithmetic; iteration counts synthetic.',
                     'case_id': observation.get('case_id'), 'basis_sha256': observation.get('basis_sha256'),
                     'values': raw_values})
        old_ref = write_json(self.root / 'baseline_observation.json', self.old)
        new_ref = write_json(self.root / 'candidate_observation.json', self.new)
        self.plan['cases'][0]['oracle'] = oracle_ref
        self.report['cases'][0].update(oracle_sha256=oracle_ref['sha256'],
                baseline_observation=old_ref, candidate_observation=new_ref)
        self.proposal['evaluation_plan'] = write_json(self.root / 'plan.json', self.plan)
        self.report['plan_sha256'] = self.proposal['evaluation_plan']['sha256']
        self.proposal['evaluation_result'] = write_json(self.root / 'report.json', self.report)
        write_json(self.root / 'synthetic_lineage_result.json', self.lineage)
        write_json(self.root / 'proposal.json', self.proposal)

    def changed_basis(self, field, value):
        field = {'solver_tolerance': 'tolerance', 'product_target_kg_h': 'goal',
                 'software_version': 'version'}.get(field, field)
        changed = {**self.basis, field: value}
        self.new['basis_sha256'] = write_json(self.root / 'unpaired_basis.json', changed)['sha256']

    def assess(self):
        self.save()
        before = {p.name: ref(p)['sha256'] for p in self.root.iterdir() if p.is_file()}
        result = assessor.assess(self.proposal, base_dir=self.root, lineage_result=self.lineage)
        after = {p.name: ref(p)['sha256'] for p in self.root.iterdir() if p.is_file()}
        assert before == after, 'Assessor mutated evidence or owner'
        write_json(self.root / 'actual_assessment.json', result)
        assert result['canonical_write_authorized'] is False
        assert result['default_retrieval_eligible'] is False
        return result


class ForwardTests(unittest.TestCase):
    def fixture(self, channel='data_pattern'):
        return Scenario(RUN_ROOT / case_directory_name(self._testMethodName), channel)

    def rejected(self, scenario):
        result = scenario.assess()
        self.assertFalse(result['candidate_review_ready'], result)
        return result

    def test_fact_based_comparable_data_is_review_only(self):
        result = self.fixture().assess()
        self.assertTrue(result['candidate_review_ready'], result)

    def test_macro_prompt_l3_is_review_only(self):
        result = self.fixture('prompt_principle').assess()
        self.assertTrue(result['candidate_review_ready'], result)

    def test_open_task_stays_audit_only(self):
        s = self.fixture(); s.lineage['task_closure_verified'] = False
        self.assertEqual(self.rejected(s)['decision'], 'audit_only')

    def test_missing_closure_stays_audit_only(self):
        s = self.fixture(); s.lineage.pop('task_closure_verified')
        self.rejected(s)

    def test_relaxed_lineage_stays_audit_only(self):
        s = self.fixture(); s.lineage['learning_eligible'] = False
        self.rejected(s)

    def test_channel_cannot_change_after_admission(self):
        s = self.fixture(); s.lineage['learning_channel'] = 'prompt_principle'
        self.rejected(s)

    def test_prompt_parameter_l1_is_not_macro(self):
        s = self.fixture('prompt_principle'); s.proposal['rule_card']['knowledge_layer'] = 'L1'
        self.rejected(s)

    def test_raw_l0_does_not_promote(self):
        s = self.fixture(); s.proposal['rule_card']['knowledge_layer'] = 'L0'
        self.rejected(s)

    def test_root_candidate_drift(self):
        s = self.fixture(); s.lineage['root_artifact']['sha256'] = 'F' * 64
        self.rejected(s)

    def test_current_owner_drift(self):
        s = self.fixture(); s.base.write_text('Changed by user\n## Rule\n', encoding='utf-8')
        self.rejected(s)

    def test_missing_rollback(self):
        s = self.fixture(); s.proposal.pop('rollback_snapshot')
        self.rejected(s)

    def test_rollback_same_file_is_not_independent(self):
        s = self.fixture(); s.proposal['rollback_snapshot'] = ref(s.base)
        self.rejected(s)

    def test_no_measurable_gain(self):
        s = self.fixture(); s.new['values']['iterations'] = s.old['values']['iterations']
        self.assertEqual(self.rejected(s)['decision'], 'not_improved')

    def test_no_change_is_valid_no_update(self):
        s = self.fixture(); s.proposal['comparison']['decision'] = 'no_change'
        self.assertEqual(self.rejected(s)['decision'], 'not_improved')

    def test_speed_cannot_compensate_conservation_failure(self):
        s = self.fixture(); s.new['values']['outlet_kg_h'] = 19.0
        self.rejected(s)

    def test_metric_regression_is_not_gain(self):
        s = self.fixture(); s.new['values']['iterations'] = 21
        self.rejected(s)

    def test_no_heldout_evidence(self):
        s = self.fixture(); s.plan['cases'][0]['split'] = 'development'
        self.rejected(s)

    def test_used_development_id_is_not_holdout(self):
        s = self.fixture(); s.plan['development_case_ids'] = ['HOLDOUT-1']
        self.rejected(s)

    def test_self_reported_passed_flag_is_not_fact_oracle(self):
        s = self.fixture()
        s.oracle['hard_requirements'] = [{'pointer': '/values/passed', 'op': 'eq', 'expected': True}]
        s.new['values']['outlet_kg_h'] = -10.0  # impossible result hidden by a self-report flag
        self.rejected(s)

    def test_candidate_observation_other_case_is_not_same_case(self):
        s = self.fixture(); s.new['case_id'] = 'OTHER-CASE'
        self.rejected(s)

    def test_candidate_observation_wrong_input_hash(self):
        s = self.fixture(); s.new['input_sha256'] = 'E' * 64
        self.rejected(s)

    def test_faster_result_at_relaxed_tolerance_is_not_improvement(self):
        s = self.fixture(); s.changed_basis('solver_tolerance', 1.0)
        self.rejected(s)

    def test_faster_result_at_different_target_is_not_improvement(self):
        s = self.fixture(); s.changed_basis('product_target_kg_h', 2.0)
        self.rejected(s)

    def test_faster_result_with_changed_method_is_not_paired(self):
        s = self.fixture(); s.changed_basis('method', 'different-formula')
        self.rejected(s)

    def test_faster_result_with_changed_version_is_not_paired(self):
        s = self.fixture(); s.changed_basis('software_version', 'SYN-2')
        self.rejected(s)

    def test_deleted_observation_identity_is_not_same_case(self):
        s = self.fixture(); s.new.pop('case_id')
        self.rejected(s)

    def test_scope_booleans_are_not_an_applicability_domain(self):
        s = self.fixture(); s.proposal['rule_card'].update(valid_for=True, invalid_for=True)
        self.rejected(s)

    def test_candidate_cannot_borrow_other_proposal_review(self):
        s = self.fixture(); s.proposal['rule_card']['action'] = 'Replace with an unrelated unconditional rule.'
        self.rejected(s)

    def test_observation_cannot_borrow_other_subject(self):
        s = self.fixture(); s.new['subject_sha256'] = ref(s.base)['sha256']
        self.rejected(s)

    def test_correct_raw_hash_cannot_support_opposite_observed_values(self):
        s = self.fixture()
        s.candidate_raw_values_override = {**s.new['values'], 'outlet_kg_h': -10.0, 'iterations': 30}
        self.rejected(s)


class CliForwardTests(unittest.TestCase):
    """Real executables, synthetic task/closure; existing real offline code receipt."""
    def build(self, channel='data_pattern'):
        s = Scenario(RUN_ROOT / case_directory_name(self._testMethodName), channel)
        s.save()
        closure = {'schema': 'user-task-closure-event-v1', 'synthetic': True,
                   'actor': 'user', 'event_type': 'close_task', 'task_id': 'SYN-CLI-TASK', 'task_revision': 1,
                   'user_quote': '\u6211\u786e\u8ba4\u672c\u4efb\u52a1\u5df2\u7ecf\u7ed3\u675f\u3002',
                   'source_locator': 'synthetic-fixture://independent-forward/closure',
                   'source_message_id': 'SYNTHETIC-NOT-A-REAL-USER-MESSAGE', 'contains_change_request': False}
        closure_ref = write_json(s.root / 'synthetic_closure_event.json', closure)
        receipt_path = current_parser_receipt()
        receipt_ref = ref(receipt_path)
        standard_ref = ref(SCRIPTS.parent / 'references/STRICT_ACCEPTANCE_AND_LEARNING.md')
        common = {'relaxation_applied': False, 'relaxations': [], 'origin_scope': 'shared_source',
                  'provenance_state': 'qualified'}
        verification = {'passed': True, 'standard_sha256': standard_ref['sha256'],
                        'required_checks': {'unit_tests': True, 'legacy_probes': True, 'real_formats': True},
                        'receipt': receipt_ref}
        manifest = {'schema': 'strict-learning-lineage-v1', 'synthetic': True,
                    'boundary': 'Synthetic user closure and proposed facts test wiring only; real receipt covers offline parser code, not synthetic chemical truth.',
                    'lineage_complete': True, 'strict_standard': standard_ref, 'root_id': 'candidate',
                    'task_id': 'SYN-CLI-TASK', 'task_revision': 1, 'task_state': 'closed', 'reopened_after_closure': False,
                    'learning_channel': s.channel, 'task_closure': {'evidence': closure_ref},
                    'records': [
                        {'id': 'source', 'kind': 'source', 'acceptance_mode': 'source_only',
                         'parents': [], 'artifact': ref(s.base), **common},
                        {'id': 'code', 'kind': 'code_result', 'acceptance_mode': 'strict',
                         'parents': ['source'], 'artifact': receipt_ref, 'strict_verification': copy.deepcopy(verification), **common},
                        {'id': 'candidate', 'kind': 'rule_candidate', 'acceptance_mode': 'strict',
                         'parents': ['code'], 'artifact': ref(s.candidate), 'strict_verification': copy.deepcopy(verification), **common}]}
        return s, manifest

    def build_source_only(self):
        s, manifest = self.build('prompt_principle')
        manifest['boundary'] = 'Synthetic closed task with user behavioral source only; no parser/engineering PASS is borrowed.'
        instruction = {'schema': 'user-instruction-source-v1', 'synthetic': True, 'actor': 'user',
                       'user_quote': 'When one unit meets the frozen duty, do not add units merely to improve catalog distance without a whole-system benefit.',
                       'source_locator': 'synthetic-fixture://independent-forward/behavior',
                       'source_message_id': 'SYNTHETIC-BEHAVIOR-SOURCE-NOT-USER-AUTHORIZATION'}
        instruction_ref = write_json(s.root / 'synthetic_user_instruction.json', instruction)
        common = {'relaxation_applied': False, 'relaxations': [], 'origin_scope': 'shared_source',
                  'provenance_state': 'source_verified', 'acceptance_mode': 'source_only'}
        manifest['records'] = [{'id': 'user-source', 'kind': 'user_instruction', 'parents': [],
                                'artifact': instruction_ref, **common},
                               {'id': 'candidate', 'kind': 'rule_candidate', 'parents': ['user-source'],
                                'artifact': ref(s.candidate), **common}]
        return s, manifest

    def refresh_candidate(self, s, manifest):
        write_json(s.candidate, {'schema': 'chemical-evolution-candidate-v1', 'synthetic': True,
                                'learning_channel': s.proposal['learning_channel'],
                                'rule_card': s.proposal['rule_card']})
        candidate_ref = ref(s.candidate)
        s.proposal['candidate'] = candidate_ref
        s.report['candidate_sha256'] = candidate_ref['sha256']
        s.new['subject_sha256'] = candidate_ref['sha256']
        manifest['records'][-1]['artifact'] = candidate_ref
        s.save()

    def execute(self, s, manifest):
        manifest_path = s.root / 'synthetic_cli_manifest.json'
        write_json(manifest_path, manifest)
        lineage_command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'evaluate_learning_eligibility.py'), str(manifest_path)]
        lineage_run = subprocess.run(lineage_command, capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=30)
        (s.root / 'lineage_cli_stdout.json').write_text(lineage_run.stdout, encoding='utf-8')
        (s.root / 'lineage_cli_stderr.txt').write_text(lineage_run.stderr, encoding='utf-8')
        self.last_lineage_result = json.loads(lineage_run.stdout)
        command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'assess_evolution_candidate.py'),
                   str(s.root / 'proposal.json'), '--lineage-manifest', str(manifest_path)]
        run = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=30)
        (s.root / 'cli_stdout.json').write_text(run.stdout, encoding='utf-8')
        (s.root / 'cli_stderr.txt').write_text(run.stderr, encoding='utf-8')
        result = json.loads(run.stdout)
        write_json(s.root / 'cli_invocation.json', {'command': command, 'returncode': run.returncode,
                   'lineage_command': lineage_command, 'lineage_returncode': lineage_run.returncode,
                   'synthetic': True, 'aspen_started': False, 'lineage_checker': ref(SCRIPTS / 'evaluate_learning_eligibility.py')})
        self.assertFalse(result['canonical_write_authorized'])
        return run.returncode, result

    def test_cli_closed_fixture_reaches_review_only(self):
        s, manifest = self.build()
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 0, result)
        self.assertTrue(result['candidate_review_ready'])

    def test_cli_open_task_does_not_start_evolution(self):
        s, manifest = self.build(); manifest['task_state'] = 'working'
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertEqual(result['decision'], 'audit_only')

    def test_cli_old_closure_cannot_close_new_revision(self):
        s, manifest = self.build(); manifest['task_revision'] = 2
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertEqual(result['decision'], 'audit_only')

    def test_cli_closed_task_cannot_cleanse_relaxed_ancestor(self):
        s, manifest = self.build(); manifest['records'][0]['relaxation_applied'] = True
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertEqual(result['decision'], 'audit_only')

    def test_cli_offline_code_receipt_cannot_prove_simulator_convergence(self):
        s, manifest = self.build()
        s.basis['analysis_target'] = 'simulator_convergence'
        s.basis_ref = write_json(s.root / 'basis.json', s.basis)
        s.plan['basis'] = s.basis_ref
        for observation in (s.old, s.new):
            observation['basis_sha256'] = s.basis_ref['sha256']
        s.save()
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertFalse(result['candidate_review_ready'])

    def test_cli_user_macro_source_only_needs_no_unrelated_parser_pass(self):
        s, manifest = self.build_source_only()
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 0, result)
        self.assertTrue(result['candidate_review_ready'])
        self.assertEqual(self.last_lineage_result['verified_evidence_kinds'], ['user_instruction_only'])
        self.assertFalse(self.last_lineage_result['canonical_write_authorized'])

    def test_cli_user_behavior_cannot_establish_data_pattern(self):
        s, manifest = self.build_source_only()
        s.proposal['learning_channel'] = manifest['learning_channel'] = 'data_pattern'
        self.refresh_candidate(s, manifest)
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertFalse(result['candidate_review_ready'])

    def test_cli_technical_threshold_cannot_disguise_as_behavior(self):
        s, manifest = self.build_source_only()
        s.proposal['rule_card']['action'] = '\u538b\u6bd4 10 \u65f6\u56fa\u5b9a\u91c7\u7528\u4e24\u7ea7\u538b\u7f29'
        self.refresh_candidate(s, manifest)
        code, result = self.execute(s, manifest)
        self.assertEqual(code, 2)
        self.assertFalse(result['candidate_review_ready'])


if __name__ == '__main__':
    RUN_ROOT.mkdir(parents=True, exist_ok=False)
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ForwardTests)
    if '--with-cli' in sys.argv:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(CliForwardTests))
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (RUN_ROOT / 'unittest_output.txt').write_text(stream.getvalue(), encoding='utf-8')
    report = {'schema': 'independent-evolution-forward-audit-v1', 'synthetic': True,
              'new_aspen_runs': 0, 'canonical_writes': 0,
              'lineage_gate': 'Real CLI for CliForwardTests; synthetic injected gate for ForwardTests. All task closures are synthetic, never user authorization.',
              'assessor': ref(SCRIPTS / 'assess_evolution_candidate.py'), 'tests': ref(Path(__file__)),
              'run': result.testsRun, 'failures': [{'test': t.id(), 'traceback': x} for t, x in result.failures],
              'errors': [{'test': t.id(), 'traceback': x} for t, x in result.errors], 'passed': result.wasSuccessful(),
              'oracle_basis': 'Arithmetic on frozen input quantities, hard physical/identity constraints, and explicit task-governance requirements; never proposed rule text.',
              'boundary': 'Mock iteration observations test the admission logic only, not real convergence or chemical truth.'}
    path = RUN_ROOT / 'FORWARD_REPORT.json'
    write_json(path, report)
    print(json.dumps({'report': str(path), 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors)}, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
