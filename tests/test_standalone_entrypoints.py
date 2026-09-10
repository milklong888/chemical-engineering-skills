"""Real standalone CLI/MCP entrypoints, guarded child processes, synthetic only."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", SOURCE_ROOT)).resolve()

GUARD_SOURCE = r'''
import json, os, socket, sys, time
from pathlib import Path
DIRECTORY=Path(os.environ['ENTRYPOINT_GUARD_DIR'])
FORBIDDEN=[os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ.get('ENTRYPOINT_FORBIDDEN_ROOTS','[]'))]
CONTROL=False
def record(kind,detail=None):
    row={'pid':os.getpid(),'kind':kind,'negative_control':CONTROL,'detail':detail,'time':time.time()}
    with (DIRECTORY/('guard-'+str(os.getpid())+'.jsonl')).open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(row,ensure_ascii=True)+'\n')
def audit(event,args):
    if event in {'open','os.listdir','os.scandir'} and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if any(path==root or path.startswith(root+os.sep) for root in FORBIDDEN):
            record('source_read_blocked',event);raise PermissionError('QA forbids other product/workspace source reads')
    if event=='import' and str(args[0]).split('.')[0] in {'pythoncom','win32com'}:
        record('com_import_blocked',str(args[0]));raise PermissionError('QA forbids COM import/creation')
    if event in {'socket.connect','socket.bind'}:
        frame=sys._getframe(1);trusted=getattr(socket,'_fallback_socketpair',None)
        if trusted is not None and frame.f_code is trusted.__code__:
            address=args[1];listener=frame.f_locals.get('lsock')
            if isinstance(address,tuple) and address[0] in {'127.0.0.1','::1'}:
                if event=='socket.bind' and args[0] is listener and address[1]==0:return
                if event=='socket.connect' and listener is not None and address[:2]==listener.getsockname()[:2] and args[0] is frame.f_locals.get('csock'):return
    if event in {'socket.connect','socket.bind','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','socket.getnameinfo','socket.sendto'}:
        record('network_blocked',event);raise PermissionError('QA forbids network/DNS')
sys.addaudithook(audit)
record('guard_ready')
def negative_controls():
    global CONTROL
    CONTROL=True
    try:
        try:
            with socket.socket() as client:client.connect(('198.51.100.1',9))
        except PermissionError:pass
        else:raise AssertionError('Network guard absent')
        try:__import__('pythoncom')
        except PermissionError:pass
        else:raise AssertionError('COM import guard absent')
        for root in FORBIDDEN:
            try:open(os.path.join(root,'synthetic-nonexistent-probe'),'rb')
            except PermissionError:pass
            else:raise AssertionError('Source-read guard absent')
    finally:CONTROL=False
'''

CHILD_SOURCE = r'''
import hashlib,importlib.util,runpy,sys
from pathlib import Path
guard_path,target=map(Path,sys.argv[1:3]);arguments=sys.argv[3:]
spec=importlib.util.spec_from_file_location('entrypoint_qa_guard',guard_path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.negative_controls()
guard.record('guarded_target',{'target':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
sys.argv=[str(target),*arguments];sys.path.insert(0,str(target.parent));runpy.run_path(str(target),run_name='__main__')
'''

BOOTSTRAP_SOURCE = r'''
import importlib.util,json,runpy,subprocess,sys
from pathlib import Path
root,guard_path,target=map(Path,sys.argv[1:4]);arguments=sys.argv[4:]
spec=importlib.util.spec_from_file_location('entrypoint_host_guard',guard_path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.negative_controls()
sys.path.insert(0,str(root));sys.path.insert(0,str(root/'tools'))
import tools.equipment_gateway as gateway
child_source=(guard_path.parent/'child_source.txt').read_text(encoding='utf-8')
original_command=gateway._command
def command(environment):
    command=original_command(environment)
    assert Path(command[-2]).resolve()==gateway.AGENT.resolve() and command[-1]=='--session-jsonl'
    return command[:-2]+['-c',child_source,str(guard_path),str(gateway.AGENT),'--session-jsonl']
gateway._command=command
original_close=gateway.EquipmentSession.close
def close(self,*args,**kwargs):
    result=original_close(self,*args,**kwargs)
    guard.record('gateway_closed',{'worker_pid':self.pid,'returncode':self._process.poll() if self._process else None})
    return result
gateway.EquipmentSession.close=close
original_run=subprocess.run
def run(command,*args,**kwargs):
    if isinstance(command,list) and '-c' not in command:
        for index,value in enumerate(command):
            if str(value)==str(root/'knowledge/scripts/query_knowledge.py'):
                assert kwargs.get('stdin')==subprocess.DEVNULL,'Read-only query must not inherit stdin'
                command=command[:index]+['-c',child_source,str(guard_path),str(value),*command[index+1:]]
                break
    return original_run(command,*args,**kwargs)
subprocess.run=run
sys.argv=[str(target),*arguments];runpy.run_path(str(target),run_name='__main__')
'''

MCP_CLIENT_SOURCE = r'''
import asyncio,hashlib,importlib.util,json,os,sys
from datetime import timedelta
from pathlib import Path
output,root,bootstrap,guard_path=map(Path,sys.argv[1:5])
spec=importlib.util.spec_from_file_location('entrypoint_client_guard',guard_path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);guard.negative_controls()
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
def unpack(result):
    assert not result.isError,result
    if isinstance(result.structuredContent,dict):return result.structuredContent
    for content in result.content:
        if getattr(content,'type','')=='text':
            try:return json.loads(content.text)
            except ValueError:pass
    raise AssertionError('Missing MCP JSON')
def evidence(name,value):
    path=output/name;raw=(json.dumps(value,ensure_ascii=False)+'\n').encode('utf-8');path.write_bytes(raw)
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest().upper()}
def req(operation,payload=None):return {'schema':'equipment-design-agent-request-v1','operation':operation,'payload':payload or {}}
async def main():
    params=StdioServerParameters(command=sys.executable,args=['-B','-X','utf8',str(bootstrap),str(root),str(guard_path),str(root/'tools/expert_mcp.py')],env=dict(os.environ),cwd=str(output))
    calls=[]
    with (output/'mcp_server.stderr.txt').open('w',encoding='utf-8') as errors:
        async with stdio_client(params,errlog=errors) as (reader,writer):
            async with ClientSession(reader,writer,read_timeout_seconds=timedelta(seconds=75)) as session:
                await session.initialize();listed=await session.list_tools()
                expected={'knowledge_search','equipment_calculate','equipment_batch','product_describe','pressure_calculate','process_feedback','process_replay_audit','design_stage_check','aspen_solve_route'}
                assert {tool.name for tool in listed.tools}==expected
                async def call(name,arguments):
                    raw=await session.call_tool(name,arguments);result=unpack(raw)
                    calls.append({'tool':name,'result':result});return result
                description=await call('product_describe',{})
                assert description['standalone_product'] and description['skill']['available']
                solve=await call('aspen_solve_route',{'payload':{'question':'读取当前物流的焓','intents':['read_value']},'evidence_root':str(output)})
                assert solve['native_tools_executed'] is False and solve['engineering_accepted'] is False
                assert solve['routes'][0]['tools'][0]=='EXISTING_OUTPUT_READBACK'
                study_context={'mode':'fixed_controls','varied_variables':['pressure'],'fixed_conditions':['current operating settings']}
                study=await call('aspen_solve_route',{'payload':{'question':'扫描变化规律','intents':['scan_range'],'study_context':study_context},'evidence_root':str(output)})
                assert study['study']['inner_control_policy']=='KEEP_DECLARED_SETTINGS'
                assert study['study']['declaration']==study_context and study['study']['semantic_verified'] is False
                assert study['decision_chain']['execution_proven'] is False
                study_stage=await call('design_stage_check',{'payload':{'stage':'source','question':'扫描变化规律','solve_request':{'intents':['scan_range'],'study_context':study_context}},'evidence_root':str(output)})
                assert study_stage['solve_route']['result']['study']['declaration']==study_context
                assert study_stage['engineering_accepted'] is False and study_stage['stage_advanced'] is False
                stage=await call('design_stage_check',{'payload':{'stage':'source','question':'高温公用工程 预热 压缩'},'evidence_root':str(output)})
                assert stage['engineering_accepted'] is False and stage['stage_advanced'] is False
                assert len(stage['queries'])==2 and stage['queries'][0]['returned_nodes'][0]['node_id']=='L3-03'
                assert any(row['kind']=='equipment_capabilities' and row['status']=='EXECUTED' for row in stage['calls'])
                caps=description['original_backend_capabilities']['response']['result']
                schema_id=caps['schemas'][0]['schema_id']
                schema=await call('product_describe',{'schema_id':schema_id})
                assert schema['response']['result']['schema_id']==schema_id
                area=req('manual_match',{'selection_id':'family:family_fixed_tubesheet_exchanger','values':{'equipment_tag':'SYN-ENTRY-E1','heat_duty_kw':1000,'overall_u_w_m2k':500,'lmtd_k':40,'lmtd_correction_factor':1}})
                equipment=await call('equipment_calculate',{'request':area});assert equipment['backend_exit_code']==0
                assert equipment['response']['result']['result']['derived_parameters']['heat_transfer_area_m2']==50
                worker=equipment['gateway']['worker_pid']
                batch=await call('equipment_batch',{'requests':[req('catalog'),req('manual_match'),req('system.capabilities')]})
                assert [r['backend_exit_code'] for r in batch['results']]==[0,2,0]
                assert {r['gateway']['worker_pid'] for r in batch['results']}=={worker}
                pressure=await call('pressure_calculate',{'method':'series_pressure','inputs':{'inlet_pressure_pa':500000,'losses_pa':[20000,30000]}})
                assert pressure['outlet_pressure_pa']==450000
                knowledge=await call('knowledge_search',{'node_id':'L3-05','corpus':'chemical_principles','detail':True,'full_text':True})
                assert knowledge['knowledge']['results'][0]['node_id']=='L3-05'
                export=evidence('export.json',{'schema':'equipment-process-canonical-export-v1','case_id':'SYN-ENTRY','run_id':'SYN-RUN','synthetic':True,'not_an_aspen_export':True,'equipment':{'SYN-ENTRY-E1':{'family_id':'family_fixed_tubesheet_exchanger','values':{k:v for k,v in area['payload']['values'].items() if k!='equipment_tag'},'units':{'heat_duty_kw':'kW','overall_u_w_m2k':'W/m2/K','lmtd_k':'K','lmtd_correction_factor':'1'}}}})
                authority=evidence('authority.json',{'schema':'equipment-process-authority-v1','case_id':'SYN-ENTRY','run_id':'SYN-RUN','synthetic':True,'not_user_authorization':True,'required_method':'Synthetic protocol test only','acceptance_criteria':['No engineering acceptance from synthetic evidence']})
                context={'case_id':'SYN-ENTRY','run_id':'SYN-RUN','source_export':export,'authority':authority,'constraint_evidence':{}}
                feedback=await call('process_feedback',{'payload':{'selector_request':area,'context':context},'evidence_root':str(output)})
                plan=feedback['plan'];assert plan['engineering_accepted'] is False and plan['flowsheet_modified'] is False
                assert all(row['binding_gaps']==[] and row['revision'] is None for row in plan['equipment'])
                candidate=evidence('candidate.json',{'synthetic':True,'not_an_aspen_model':True})
                replay=await call('process_replay_audit',{'payload':{'plan':plan,'replay':{'case_id':'SYN-ENTRY','run_id':'SYN-RUN','plan_sha256':plan['plan_sha256'],'candidate':candidate,'source_export':export,'gates':{}}},'evidence_root':str(output)})
                assert replay['engineering_accepted'] is False and replay['evidence_chain_complete'] is False
                assert {row['gate'] for row in replay['failed_gates']}==set(plan['required_replay_gates'])
                report={'schema':'standalone-nine-tool-test-v1','tool_names':sorted(expected),'calls':calls,'worker_pid':worker,'engineering_accepted':False}
                (output/'mcp_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
asyncio.run(asyncio.wait_for(main(),timeout=150))
'''


class StandaloneEntrypoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        destination=os.environ.get('STANDALONE_ENTRYPOINT_REPORT_DIR')
        cls.temporary=None
        if destination:
            cls.work=Path(destination).resolve();cls.work.mkdir(parents=True,exist_ok=False)
        else:
            cls.temporary=tempfile.TemporaryDirectory(prefix='standalone-entrypoint-qa-');cls.work=Path(cls.temporary.name)
        cls.guard=cls.work/'qa_guard.py';cls.guard.write_text(GUARD_SOURCE,encoding='utf-8')
        (cls.work/'child_source.txt').write_text(CHILD_SOURCE,encoding='utf-8')
        cls.bootstrap=cls.work/'bootstrap.py';cls.bootstrap.write_text(BOOTSTRAP_SOURCE,encoding='utf-8')
        cls.client=cls.work/'mcp_client.py';cls.client.write_text(MCP_CLIENT_SOURCE,encoding='utf-8')
        forbidden=[]
        if 'STANDALONE_FORBIDDEN_ROOTS' in os.environ:forbidden=json.loads(os.environ['STANDALONE_FORBIDDEN_ROOTS'])
        else:
            for parent in SOURCE_ROOT.parents:
                if (parent/'设备设计选型工作包').is_dir():
                    forbidden=[str(parent/name) for name in ('设备设计选型工作包','external_sources','aspen_sun_lanyi_knowledge','skill_packages')];break
        cls.env={**os.environ,'ENTRYPOINT_GUARD_DIR':str(cls.work),'ENTRYPOINT_FORBIDDEN_ROOTS':json.dumps(forbidden),
                 'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','FASTMCP_CHECK_FOR_UPDATES':'off'}
        cls.sequence=0

    @classmethod
    def tearDownClass(cls):
        if cls.temporary:cls.temporary.cleanup()

    def cli(self,*arguments,input=None,expected=0):
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(self.bootstrap),str(ROOT),str(self.guard),str(ROOT/'tools/expert_cli.py'),*arguments],
            input=input,stdin=None if input is not None else subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',env=self.env,cwd=self.work,timeout=120)
        type(self).sequence+=1
        (self.work/f'cli_{self.sequence}.stdout.txt').write_text(result.stdout,encoding='utf-8')
        (self.work/f'cli_{self.sequence}.stderr.txt').write_text(result.stderr,encoding='utf-8')
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result

    def test_01_cli_discovery_native_schema_and_example_paths(self):
        result=json.loads(self.cli('--describe').stdout)
        self.assertTrue(result['standalone_product']);self.assertTrue(result['skill']['available'],result['skill'])
        self.assertTrue(Path(result['skill']['path']).is_file())
        self.assertEqual(len(result['equipment_gateway']['operations']),18)
        self.assertEqual(len(result['equipment_gateway']['operation_aliases']),16)
        for name in result['examples']:self.assertTrue((ROOT/name).is_file(),name)
        caps=result['original_backend_capabilities']['response']['result']
        policy=result['equipment_gateway']
        self.assertEqual(set(policy['operations'])|{row['operation'] for row in policy['excluded_operations']},set(caps['operations']))
        self.assertTrue(set(policy['operations']).isdisjoint({row['operation'] for row in policy['excluded_operations']}))
        for alias,operation in policy['operation_aliases'].items():self.assertEqual(caps['operation_aliases'][alias],operation)
        schema_id=next(item['schema_id'] for item in caps['schemas'] if 'parameter-package' in item['schema_id'])
        schema=json.loads(self.cli('--schema',schema_id).stdout)
        self.assertEqual(schema['backend_exit_code'],0)
        self.assertEqual(schema['response']['result']['schema_id'],schema_id)
        self.assertEqual(schema['response']['result']['sha256'],next(item['sha256'] for item in caps['schemas'] if item['schema_id']==schema_id))
        self.assertTrue(schema['response']['result']['document'])
        self.assertTrue(json.loads(self.cli('--schema','pressure-methods').stdout)['methods'])

    def test_02_cli_lexical_exact_node_detail_and_full_text(self):
        result=json.loads(self.cli('--query','预热 压缩','--corpus','chemical_principles','--detail','--full-text').stdout)
        self.assertTrue(result['knowledge']['results'])
        node=result['knowledge']['results'][0]['node_id']
        exact=json.loads(self.cli('--node-id',node,'--corpus','chemical_principles','--detail','--full-text').stdout)
        self.assertEqual(exact['knowledge']['results'][0]['node_id'],node)
        self.assertTrue(exact['knowledge']['results'][0]['text'])
        self.assertFalse(exact['knowledge']['current_project_authority'])
        self.cli('--query','synthetic','--node-id','L3-05',expected=2)

    @unittest.skipUnless(importlib.util.find_spec('numpy'),'Vector test requires the bundled offline NumPy environment')
    def test_03_cli_vector_query(self):
        result=json.loads(self.cli('--query','预热 压缩','--corpus','chemical_principles','--vector').stdout)
        self.assertTrue(result['knowledge']['results'])
        self.assertFalse(result['knowledge']['project_value_transfer_allowed'])

    def test_04_cli_resident_failure_continue_same_pid_and_eof(self):
        native=lambda operation,payload:{'schema':'equipment-design-agent-request-v1','operation':operation,'payload':payload}
        requests=[{'operation':'equipment','payload':native('catalog',{})},
                  {'operation':'equipment','payload':native('manual_match',{})},
                  {'operation':'equipment','payload':native('report.render',{'result':{'synthetic_forgery':True}})},
                  {'operation':'equipment','payload':native('system.capabilities',{})}]
        result=self.cli('--session-jsonl',input='\n'.join(json.dumps(row) for row in requests)+'\n')
        rows=[json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([row['backend_exit_code'] for row in rows],[0,2,2,0])
        pid=rows[0]['gateway']['worker_pid'];self.assertEqual({row['gateway']['worker_pid'] for row in rows},{pid})
        self.assertEqual(rows[2]['response']['errors'][0]['code'],'UNEXPECTED_PAYLOAD_FIELDS')
        guards=self.guard_records()
        self.assertTrue(any(row['kind']=='gateway_closed' and row['detail']=={'worker_pid':pid,'returncode':0} for row in guards))
        self.assertTrue(any(row['pid']==pid and row['kind']=='guard_ready' for row in guards))

    @unittest.skipUnless(importlib.util.find_spec('mcp') and importlib.util.find_spec('fastmcp'),'Use the installed offline MCP runtime for nine-tool integration')
    def test_05_real_stdio_mcp_all_nine_tools(self):
        output=self.work/'mcp';output.mkdir()
        result=subprocess.run([sys.executable,'-B','-X','utf8',str(self.client),str(output),str(ROOT),str(self.bootstrap),str(self.guard)],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,encoding='utf-8',cwd=self.work,env=self.env,timeout=180)
        (output/'client.stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'client.stderr.txt').write_text(result.stderr,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads((output/'mcp_result.json').read_text(encoding='utf-8'))
        self.assertEqual(len(report['tool_names']),9)
        self.assertEqual(set(report['tool_names']),{row['tool'] for row in report['calls']})
        pid=report['worker_pid'];guards=self.guard_records()
        self.assertTrue(any(row['pid']==pid and row['kind']=='guard_ready' for row in guards))
        self.assertTrue(any(row['kind']=='gateway_closed' and row['detail']=={'worker_pid':pid,'returncode':0} for row in guards))

    def test_06_installed_skill_receipt_path_not_guessed_home(self):
        sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
        from tools import product_contract
        workspace=self.work/'synthetic_installed_workspace';runtime=workspace/'chemical-engineering-runtime';runtime.mkdir(parents=True)
        skills=self.work/'synthetic_separate_skills';skill=skills/'equipment-design-app/SKILL.md';skill.parent.mkdir(parents=True);skill.write_text('synthetic skill location fixture',encoding='utf-8')
        receipt=workspace/'CHEMICAL_SKILLS_INSTALLATION.json'
        value={'schema':'chemical-skills-installation-paths-v1','runtime_root':str(runtime),'workspace_root':str(workspace),'skills_root':str(skills)}
        receipt.write_text(json.dumps(value),encoding='utf-8')
        with mock.patch.object(product_contract,'ROOT',runtime):
            actual=product_contract.skill_location();self.assertTrue(actual['available']);self.assertEqual(Path(actual['path']),skill)
            value['runtime_root']=str(self.work/'wrong');receipt.write_text(json.dumps(value),encoding='utf-8')
            self.assertFalse(product_contract.skill_location()['available'])

    def guard_records(self):
        return [json.loads(line) for path in self.work.glob('guard-*.jsonl') for line in path.read_text(encoding='utf-8').splitlines()]

    def test_99_guards_active_and_no_unexpected_network_com_or_source_reads(self):
        records=self.guard_records();self.assertTrue(records)
        self.assertTrue(any(row['kind']=='network_blocked' and row['negative_control'] for row in records))
        self.assertTrue(any(row['kind']=='com_import_blocked' and row['negative_control'] for row in records))
        bad=[row for row in records if row['kind'] in {'network_blocked','com_import_blocked','source_read_blocked'} and not row['negative_control']]
        self.assertEqual(bad,[])
        for row in records:
            if row['kind']=='guarded_target':self.assertEqual(len(row['detail']['sha256']),64)


if __name__=='__main__':unittest.main(verbosity=2)
