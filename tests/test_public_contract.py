"""Self-contained governance and source-table tests; no commercial software runs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'plugins/chemical-engineering-skills/skills'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

gate=load('public_learning_gate',SKILLS/'chemical-engineering-expert/scripts/evaluate_learning_eligibility.py')
evidence=load('public_aspen_evidence',SKILLS/'aspen-plus-operations/scripts/aspen_evidence.py')

def ref(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest().upper()}
def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return ref(path)

class PublicContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='synthetic-public-contract-')
        self.addCleanup(self.temp.cleanup);self.directory=Path(self.temp.name)
        user={'schema':'user-instruction-source-v1','actor':'user','user_quote':'先确定系统边界，再组织详细计算。',
              'source_locator':'synthetic-test-message','source_message_id':'synthetic-instruction-1'}
        self.source=write(self.directory/'instruction.json',user)
        self.close={'schema':'user-task-closure-event-v1','actor':'user','event_type':'close_task',
                    'task_id':'synthetic-task','task_revision':1,'user_quote':'任务完成，不用再修改。',
                    'source_locator':'synthetic-test-message','source_message_id':'synthetic-close-1','contains_change_request':False}
        self.close_ref=write(self.directory/'closure.json',self.close)
        self.card={'claim_type':'behavior','knowledge_layer':'L3','trigger':'开始设计任务',
                   'observation':'任务包含多个相互影响的单元','mechanism':'边界决定输入输出和验收范围',
                   'action':'先列出系统边界及设计基准','verification':'核对后续计算与已确定的边界一致',
                   'boundary':'不把行为顺序作为物性或设备参数证据'}
        self.root_payload={'learning_channel':'prompt_principle','rule_card':self.card,'candidate_rule':user['user_quote']}
        self.candidate=write(self.directory/'candidate.json',self.root_payload)
        def node(identity,kind,artifact,parents):
            return {'id':identity,'kind':kind,'artifact':artifact,'parents':parents,'acceptance_mode':'source_only',
                    'provenance_state':'source_verified','origin_scope':'shared_source','relaxation_applied':False,'relaxations':[]}
        self.manifest={'schema':'strict-learning-lineage-v1','task_id':'synthetic-task','task_revision':1,
                       'task_state':'closed','reopened_after_closure':False,'task_closure':{'evidence':self.close_ref},
                       'learning_channel':'prompt_principle','lineage_complete':True,'root_id':'candidate',
                       'strict_standard':ref(gate.ACTIVE_STANDARD),
                       'records':[node('instruction','user_instruction',self.source,[]),node('candidate','rule_candidate',self.candidate,['instruction'])]}

    def evaluate(self):return gate.evaluate(self.manifest,base_dir=self.directory)

    def test_user_principle_is_only_a_review_candidate(self):
        result=self.evaluate()
        self.assertTrue(result['learning_eligible'],result)
        self.assertEqual(result['verified_evidence_kinds'],['user_instruction_only'])
        self.assertFalse(result['canonical_write_authorized'])
        self.assertFalse(result['default_retrieval_eligible'])

    def test_working_task_does_not_start_review(self):
        self.manifest['task_state']='working'
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_old_revision_is_not_current_closure(self):
        self.manifest['task_revision']=2
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_acknowledgement_is_not_closure(self):
        self.close['user_quote']='收到了'
        self.manifest['task_closure']['evidence']=write(self.directory/'closure.json',self.close)
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_relaxed_parent_remains_excluded(self):
        self.manifest['records'][0]['relaxation_applied']=True
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_changed_source_hash_is_rejected(self):
        (self.directory/'instruction.json').write_text('{}',encoding='utf-8')
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_user_authority_does_not_establish_data_pattern(self):
        self.manifest['learning_channel']='data_pattern'
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_technical_threshold_is_not_pure_behavior(self):
        self.card['action']='所有流程压力固定为5 MPa'
        self.manifest['records'][-1]['artifact']=write(self.directory/'candidate.json',self.root_payload)
        self.assertFalse(self.evaluate()['learning_eligible'])

    def test_original_summary_fragments_are_nonzero(self):
        fixtures=SKILLS/'aspen-plus-operations/references/fixtures'
        for name,total in [('native_summary_warning.txt',23),('native_summary_errors.txt',152)]:
            with self.subTest(name=name):
                result=evidence.parse_summary_counts((fixtures/name).read_text(encoding='utf-8'))
                self.assertTrue(result['complete'])
                self.assertEqual(result['columns'],['Physical Property','System','Simulation'])
                self.assertEqual(result['total'],total)
                self.assertFalse(result['all_zero'])

    def test_success_text_is_not_a_summary(self):
        result=evidence.parse_summary_counts('NO ERRORS OR WARNINGS GENERATED')
        self.assertFalse(result['found'])
        self.assertFalse(result['all_zero'])

if __name__=='__main__':unittest.main(verbosity=2)
