"""Source-maintenance candidates and package-local query; no active library writes."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]
BASE=REPO/'knowledge'
sys.path.insert(0,str(BASE/'scripts'))
import build_knowledge_version as build
import query_knowledge as query
import vector_adapter
from verify_knowledge import verify
from resolve_knowledge_owner import resolve_knowledge_owner


def write_json(path,value):path.write_bytes(build.encoded(value));return path
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class StandaloneKnowledge(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='knowledge-lifecycle-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'synthetic_source.txt';self.source.write_text('Synthetic source: identity and dimension checks before reuse.',encoding='utf-8')
        self.proof=self.root/'independent_source_review.txt';self.proof.write_text('Independent synthetic review of section 1, source identity and local-only scope.',encoding='utf-8')
        self.record={'node_id':'L2-STANDALONE-SYNTHETIC','corpus':'chemical_principles','title':'Standalone synthetic source method',
                     'text':'STANDALONE_ADDED_METHOD: inspect the stated basis before applying this synthetic relation.',
                     'knowledge_layer':'L2','evidence_class':'X','authority_scope':'shared','project_value_transfer_allowed':False,
                     'units_basis':'Synthetic qualitative statement; no numerical design claim',
                     'applicability':['synthetic interface verification only'],'forbidden_transfer':['not actual engineering data']}
        self.change={'operation':'add','origin_kind':'external_source','relaxation_applied':False,'record':self.record,
                     'source':{'path':self.source.name,'sha256':sha(self.source),'source_id':'SYNTHETIC-SOURCE-1','locator':'section 1'},
                     'license':{'distribution_scope':'local_only','basis':'Synthetic test text authored for this fixture'}}
        self.intake={'schema':'knowledge-version-intake-v1','base_manifest_sha256':sha(BASE/'manifest.json'),
                     'intake_kind':'direct_source','proposer_id':'synthetic_proposer','changes':[self.change]}
        self.intake_path=self.root/'intake.json';self.review_path=self.root/'review.json'
        self.output=self.root/'candidate'
        self.refresh()

    def refresh(self):
        write_json(self.intake_path,self.intake)
        hashes=[build.digest(build.encoded(c)) for c in self.intake['changes']]
        review={'schema':'knowledge-intake-review-v1','intake_sha256':sha(self.intake_path),'changes_sha256':build.digest(build.encoded(hashes)),
                'reviewer_id':'separate_synthetic_reviewer','changes':[]}
        for c,h in zip(self.intake['changes'],hashes):
            review['changes'].append({'change_sha256':h,'decision':'admit_source_candidate','source_sha256':c['source']['sha256'],
                                      'text_sha256':build.digest(c['record']['text'].encode()),'knowledge_layer':c['record']['knowledge_layer'],
                                      'distribution_scope':c['license'].get('distribution_scope'),'basis':'Independent source/locator/unit/scope cross-check fixture',
                                      'evidence':{'path':self.proof.name,'sha256':sha(self.proof)}})
        write_json(self.review_path,review)

    def cli(self,*,review=True,inspect=False,expected=0):
        args=[sys.executable,'-B',str(BASE/'scripts/build_knowledge_version.py'),'--base',str(BASE),'--intake',str(self.intake_path)]
        if review:args+=['--review',str(self.review_path)]
        args+=['--inspect'] if inspect else ['--output',str(self.output)]
        process=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'},timeout=120)
        self.assertEqual(process.returncode,expected,process.stdout+process.stderr)
        return json.loads(process.stdout)

    def test_01_lexical_vector_same_intent(self):
        text='预热 压缩机功率计算'
        self.assertEqual(query.search(text,corpus='chemical_principles',limit=1)['mode'],'detail')
        self.assertEqual(vector_adapter.query(text,corpus='chemical_principles',limit=1)['mode'],'detail')
        self.assertEqual(query.determine_mode('流程合理性'),'macro_first')

    def test_02_source_candidate_actual_cli_and_preservation(self):
        before=sha(BASE/'records.jsonl');result=self.cli()
        self.assertEqual(result['admitted_count'],1);self.assertFalse(result['canonical_write_authorized'])
        self.assertFalse(result['engineering_acceptance_verified'])
        target=self.output/'knowledge'
        self.assertEqual(verify(target)['status'],'pass')
        self.assertEqual(sha(BASE/'records.jsonl'),before)
        self.assertTrue((target/'records.jsonl').read_bytes().startswith((BASE/'records.jsonl').read_bytes()))
        process=subprocess.run([sys.executable,'-B',str(target/'scripts/query_knowledge.py'),'--node-id',self.record['node_id'],'--json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(json.loads(process.stdout)['results'][0]['text'],self.record['text'])
        process=subprocess.run([sys.executable,'-B',str(target/'scripts/query_knowledge.py'),'--query','STANDALONE_ADDED_METHOD','--vector','--json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertIn(self.record['node_id'],[r['node_id'] for r in json.loads(process.stdout)['results']])

    def test_03_unreviewed_preserved_but_not_indexed(self):
        _,baseline_records=query.load_records(BASE)
        baseline_vectors=(BASE/'vectors/records.jsonl').read_bytes()
        baseline_config=json.loads((BASE/'vectors/config.json').read_text(encoding='utf-8'))
        result=self.cli(review=False,expected=2)
        self.assertEqual(result['pending_count'],1);self.assertEqual(result['admitted_count'],0)
        target=self.output/'knowledge';_,records=query.load_records(target)
        self.assertEqual(records,baseline_records)
        self.assertNotIn(self.record['node_id'],{r['node_id'] for r in records})
        pending=json.loads((target/'candidate_intake.json').read_text(encoding='utf-8'))
        self.assertEqual(pending['pending'][0]['change']['record']['text'],self.record['text'])
        self.assertFalse(pending['default_retrieval_eligible'])
        config=json.loads((target/'vectors/config.json').read_text(encoding='utf-8'))
        self.assertEqual(config['record_count'],baseline_config['record_count'])
        self.assertEqual((target/'vectors/records.jsonl').read_bytes(),baseline_vectors)

    def test_04_source_drift_no_output(self):
        self.source.write_text('Changed source',encoding='utf-8')
        result=self.cli(expected=2)
        self.assertIn('identity drift',result['reason']);self.assertFalse(self.output.exists())

    def test_05_relaxed_ancestor_never_admitted(self):
        self.change['lineage']={'parents':[{'artifact_id':'historical-parent','relaxation_applied':True}]};self.refresh()
        result=self.cli(inspect=True,expected=2)
        self.assertFalse(result['decisions'][0]['admitted'])
        self.assertIn('RELAXED_LINEAGE_AUDIT_ONLY',result['decisions'][0]['reasons'])
        self.assertFalse(self.output.exists())

    def test_06_review_requires_exact_full_batch(self):
        second=copy.deepcopy(self.change);second['record']['node_id']='L2-OTHER-SYNTHETIC';self.intake['changes'].append(second);self.refresh()
        review=json.loads(self.review_path.read_text());review['changes'].pop();write_json(self.review_path,review)
        result=self.cli(expected=2);self.assertIn('every change',result['reason']);self.assertFalse(self.output.exists())

    def test_07_existing_node_cannot_be_overwritten(self):
        self.record['node_id']='L3-05';self.refresh()
        result=self.cli(expected=2);self.assertIn('collides',result['reason']);self.assertFalse(self.output.exists())

    def test_08_review_boolean_is_not_admission(self):
        write_json(self.review_path,{'approved':True})
        result=self.cli(expected=2);self.assertIn('exact complete intake',result['reason'])

    def test_09_task_experience_needs_existing_gate(self):
        self.intake['intake_kind']='task_experience';self.change['origin_kind']='task_experience';self.refresh()
        result=self.cli(inspect=True,expected=2)
        self.assertIn('EXISTING_EVOLUTION_GATE_NOT_READY',result['decisions'][0]['reasons'])
        self.assertFalse(self.output.exists())

    def test_10_source_lane_cannot_hide_task_experience(self):
        self.change['origin_kind']='task_experience';self.refresh()
        result=self.cli(expected=2);self.assertIn('cannot enter',result['reason'])

    def test_11_installed_owner_uses_disjoint_skill_root(self):
        skills=self.root/'installed-skills';owner=skills/'equipment-design-app'
        (owner/'references').mkdir(parents=True)
        (owner/'SKILL.md').write_text('synthetic owner',encoding='utf-8');(owner/'references/ERROR_MEMORY.md').write_text('synthetic memory',encoding='utf-8')
        knowledge=self.root/'workspace/chemical-engineering-runtime/knowledge';knowledge.mkdir(parents=True)
        result=resolve_knowledge_owner('equipment-design-app',skills_root=skills,knowledge_root=knowledge)
        self.assertEqual(result['status'],'resolved');self.assertFalse(result['duplicate_owner_created'])
        self.assertTrue(all(Path(p).is_relative_to(skills) for p in result['files'].values()))

    def test_12_installed_owner_reads_explicit_workspace_route(self):
        skills=self.root/'installed-skills';owner=skills/'equipment-design-app';(owner/'references').mkdir(parents=True)
        (owner/'SKILL.md').write_text('owner');(owner/'references/ERROR_MEMORY.md').write_text('memory')
        workspace=self.root/'workspace';knowledge=workspace/'chemical-engineering-runtime/knowledge';knowledge.mkdir(parents=True)
        (workspace/'LOCAL_KNOWLEDGE_GRAPH_LINKS.md').write_text('安装后的技能根为`'+skills.as_posix()+'`。',encoding='utf-8')
        result=resolve_knowledge_owner('equipment-design-app',knowledge_root=knowledge)
        self.assertEqual(result['status'],'resolved')

    def test_13_undeclared_file_is_rejected(self):
        # Hash-validation tree copied only within the owned fixture.
        target=self.root/'copy';shutil.copytree(BASE,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (target/'extra.json').write_text('{}')
        self.assertIn('unmanifested file: extra.json',verify(target)['problems'])

    def test_14_invalid_layer_and_licensing_rejected(self):
        self.record['knowledge_layer']='L9';self.refresh();self.assertIn('Invalid corpus/layer',self.cli(expected=2)['reason'])
        self.record['knowledge_layer']='L2';self.change['license']={};self.refresh()
        self.assertIn('license scope',self.cli(expected=2)['reason'])

    def test_15_review_source_identity_cannot_float(self):
        review=json.loads(self.review_path.read_text());review['changes'][0]['source_sha256']='0'*64;write_json(self.review_path,review)
        self.assertIn('Per-node review binding',self.cli(expected=2)['reason'])

    def test_16_output_collision_is_non_destructive(self):
        self.output.mkdir();marker=self.output/'user.txt';marker.write_text('keep')
        self.cli(expected=2);self.assertEqual(marker.read_text(),'keep')

    def test_17_supersede_retains_original_identity_and_body(self):
        _,old=query.load_records(BASE);previous=next(r for r in old if r['corpus']=='chemical_principles' and r['node_id']=='L3-05')
        self.change['operation']='supersede';self.change['supersedes']={k:previous[k] for k in ('corpus','node_id','text_sha256')};self.refresh()
        self.cli();target=self.output/'knowledge';_,records=query.load_records(target)
        retained=next(r for r in records if r['corpus']==previous['corpus'] and r['node_id']==previous['node_id'])
        self.assertEqual(retained['text'],previous['text']);self.assertEqual(retained['source'],previous['source'])
        self.assertFalse(retained['retrieval_eligible']);self.assertEqual(retained['knowledge_status'],'superseded')
        self.assertEqual((target/previous['public_path']).read_bytes(),(BASE/previous['public_path']).read_bytes())
        self.assertEqual(len(records),len(old)+1)

    def test_18_intrinsic_relaxed_json_cannot_be_relabelled(self):
        write_json(self.source,{'schema':'aspen-case-audit-event-v2','record_scope':'case_audit_only','learning_eligible':False,'relaxation_applied':True})
        self.change['source']['sha256']=sha(self.source);self.refresh()
        result=self.cli(inspect=True,expected=2)
        self.assertIn('SOURCE_INTRINSIC_EXCLUSION',result['decisions'][0]['reasons'])

    def test_19_strict_actual_task_receipt_still_requires_closure(self):
        write_json(self.source,{'schema':'aspen_clean_delivery_audit/2','passed':True,'relaxation_applied':False})
        self.change['source']['sha256']=sha(self.source);self.refresh()
        result=self.cli(inspect=True,expected=2)
        self.assertIn('TASK_ARTIFACT_REQUIRES_EXPERIENCE_LANE',result['decisions'][0]['reasons'])

    def test_20_external_schema_definition_is_not_a_task_record(self):
        write_json(self.source,{'$schema':'https://json-schema.org/draft/2020-12/schema','properties':{'example':{'const':{'schema':'aspen_clean_delivery_audit/2','relaxation_applied':True}}}})
        self.change['source']['sha256']=sha(self.source);self.refresh()
        result=self.cli(inspect=True)
        self.assertTrue(result['decisions'][0]['admitted'])

    def test_21_fake_learning_helper_rejected_before_import(self):
        skills=self.root/'fake-skills';source=REPO/'plugins/chemical-engineering-skills/skills'
        contract=json.loads((BASE/'learning_owner_contract.json').read_text())
        required=[r['path'] for r in contract['files']]+['chemical-engineering-expert/SKILL.md','chemical-engineering-expert/references/ERROR_MEMORY.md','chemical-engineering-expert/references/EVOLUTION_LOOP.md']
        for rel in required:
            p=skills/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,p)
        (skills/'aspen-document-driven-flowsheet/scripts/learning_admission.py').write_text('raise RuntimeError("UNTRUSTED_EXECUTED")\n')
        with self.assertRaisesRegex(ValueError,'Trusted learning owner identity mismatch'):
            build.inspect_intake(BASE,self.intake_path,self.review_path,skills)

    def test_22_large_standard_json_is_resource_gap_not_task_origin(self):
        self.source.write_bytes(b'{"standard_rows":"'+b'x'*20_000_001+b'"}')
        self.change['source']['sha256']=sha(self.source);self.refresh()
        result=self.cli(inspect=True,expected=2)
        reasons=result['decisions'][0]['reasons']
        self.assertIn('SOURCE_STRUCTURED_PAYLOAD_REVIEW_LIMIT',reasons)
        self.assertNotIn('TASK_ARTIFACT_REQUIRES_EXPERIENCE_LANE',reasons)
        self.assertNotIn('SOURCE_INTRINSIC_EXCLUSION',reasons)
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(os.name=='nt','Windows MAX_PATH regression')
    def test_23_deep_final_path_builds_and_queries_its_own_payload(self):
        manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
        longest=max(('knowledge/'+r['path'] for r in manifest['files']),key=len)
        padding=249-len(str(self.root))-len(longest)-len('candidate')-3
        self.assertGreater(padding,0)
        parent=self.root/('d'*padding);parent.mkdir();self.output=parent/'candidate'
        self.assertEqual(len(str(self.output/longest)),249)
        old_stage=parent/'.knowledge-candidate-12345678/version'
        self.assertGreaterEqual(len(str(old_stage/longest)),260)
        result=self.cli()
        self.assertEqual(result['admitted_count'],1)
        target=self.output/'knowledge'
        self.assertEqual(verify(target)['status'],'pass')
        for entry in manifest['files']:
            self.assertTrue((target/entry['path']).is_file(),entry['path'])
        for options in (['--node-id',self.record['node_id']],['--query','STANDALONE_ADDED_METHOD','--vector']):
            process=subprocess.run([sys.executable,'-B',str(target/'scripts/query_knowledge.py'),*options,'--json'],capture_output=True,text=True,encoding='utf-8',timeout=45)
            self.assertEqual(process.returncode,0,process.stderr+process.stdout)
            self.assertIn(self.record['node_id'],[r['node_id'] for r in json.loads(process.stdout)['results']])

    @unittest.skipUnless(os.name=='nt','Windows MAX_PATH regression')
    def test_24_over_limit_output_gets_actionable_preflight_without_candidate(self):
        if build.windows_long_path_state()=='enabled':self.skipTest('Legacy Windows path budget not active on this host')
        manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
        longest=max(('knowledge/'+r['path'] for r in manifest['files']),key=len)
        padding=281-len(str(self.root))-len(longest)-len('candidate')-3
        parent=self.root/('d'*padding);parent.mkdir();self.output=parent/'candidate'
        result=self.cli(expected=2)
        self.assertIn('WINDOWS_PATH_LIMIT_FINAL',result['reason'])
        self.assertIn('source_payload_verified=true',result['reason'])
        self.assertIn('shorten',result['reason'])
        self.assertFalse(self.output.exists())
        self.assertEqual(list(parent.iterdir()),[])

    @unittest.skipUnless(os.name=='nt','Windows MAX_PATH regression')
    def test_25_staging_only_limit_cleans_its_owned_empty_temporary(self):
        if build.windows_long_path_state()=='enabled':self.skipTest('Legacy Windows path budget not active on this host')
        manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
        longest=max(('knowledge/'+r['path'] for r in manifest['files']),key=len)
        padding=258-len(str(self.root))-len(longest)-len('candidate')-3
        parent=self.root/('d'*padding);parent.mkdir();self.output=parent/'candidate'
        self.assertLess(len(str(self.output/longest)),260)
        result=self.cli(expected=2)
        self.assertIn('WINDOWS_PATH_LIMIT_STAGING',result['reason'])
        self.assertIn('source_payload_verified=true',result['reason'])
        self.assertFalse(self.output.exists())
        self.assertEqual(list(parent.iterdir()),[])


if __name__=='__main__':unittest.main(verbosity=2)
