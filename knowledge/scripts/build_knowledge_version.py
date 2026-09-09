"""Build an isolated knowledge-version candidate from hash-bound reviewed inputs.

This is source maintenance, not automatic promotion. Unreviewed/relaxed changes
remain a complete audit ledger and never enter the default records or vectors.
"""
from __future__ import annotations
import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

from query_knowledge import CORPORA, load_records
from verify_knowledge import verify

ROOT=Path(__file__).resolve().parents[1]
SCRIPT_NAMES=('vectorize_workspace_knowledge.py','query_workspace_vectors.py','retrieval_routes.json','retrieval_eval_set.jsonl')


def windows_long_path_state():
    """Read only; an unavailable system setting keeps a conservative path budget."""
    if sys.platform!='win32':return 'not_windows'
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
            value,_=winreg.QueryValueEx(key,'LongPathsEnabled')
        return 'enabled' if value==1 else 'disabled'
    except (ImportError,OSError,RuntimeError):
        return 'unknown'


def utf16_length(path):
    return len(str(path).encode('utf-16-le'))//2


def windows_path_preflight(root, relative_files, *, phase, requested_output):
    """Check the actual final/staging tree before any payload is copied there."""
    state=windows_long_path_state()
    report={'phase':phase,'windows_long_paths':state,'checked':state in {'disabled','unknown'}}
    if not report['checked']:return report
    files=[(str(relative),root/relative) for relative in relative_files]
    directories={root}
    for _,path in files:
        directories.update(parent for parent in path.parents if parent==root or parent.is_relative_to(root))
    longest_file=max(files,key=lambda pair:utf16_length(pair[1]))
    longest_dir=max(directories,key=utf16_length)
    file_length=utf16_length(longest_file[1]);directory_length=utf16_length(longest_dir)
    report.update(max_file_utf16=file_length,max_directory_utf16=directory_length,
                  file_limit_utf16=259,directory_limit_utf16=247,longest_relative_file=longest_file[0])
    reduction=max(file_length-259,directory_length-247,0)
    if reduction:
        kind='file' if file_length-259>=directory_length-247 else 'directory'
        suggested=str(Path(requested_output.anchor)/'ChemK'/'candidate')
        raise ValueError(f'WINDOWS_PATH_LIMIT_{phase.upper()}: source_payload_verified=true; source_exists=true; '
                         f'limit_type=legacy_MAX_PATH; path_kind={kind}; final_or_staging_root={root}; '
                         f'max_file_utf16={file_length}/259; max_directory_utf16={directory_length}/247; '
                         f'longest_relative_file={longest_file[0]}; shorten --output parent by at least {reduction} UTF-16 units, '
                         f'or use a writable short parent such as {suggested}. This is not missing source data; no candidate was created.')
    return report


def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')


def digest(raw): return hashlib.sha256(raw).hexdigest()


def structured_payload_over_limit(path):
    if path.stat().st_size<=20_000_000:return False
    with path.open('rb') as stream:prefix=stream.read(256).lstrip(b'\xef\xbb\xbf \r\n\t')
    return prefix.startswith((b'{',b'['))


def reference(ref, base):
    if not isinstance(ref,dict) or not isinstance(ref.get('path'),str) or not isinstance(ref.get('sha256'),str):
        raise ValueError('Evidence requires explicit path and SHA256')
    path=Path(ref['path']);path=(path if path.is_absolute() else base/path).resolve()
    if not path.is_file() or digest(path.read_bytes()) != ref['sha256'].lower():
        raise ValueError('Evidence missing or source identity drift: '+path.name)
    return path


def relaxation_reason(value):
    if isinstance(value,dict):
        if value.get('relaxation_applied') is True or value.get('relaxations'):
            return 'RELAXED_LINEAGE_AUDIT_ONLY'
        if any(value.get(k) in {'case_relaxed','relaxed_lineage','case_accepted_with_relaxation'} for k in ('record_scope','provenance_state','effective_status')):
            return 'RELAXED_LINEAGE_AUDIT_ONLY'
        return next((r for item in value.values() if (r:=relaxation_reason(item))),None)
    if isinstance(value,list):return next((r for item in value if (r:=relaxation_reason(item))),None)
    return None


def trusted_learning_owners(base, skills_root):
    """Bind policy/helper bytes to this product before importing any supplied root."""
    from resolve_knowledge_owner import resolve_knowledge_owner
    route=resolve_knowledge_owner('chemical-engineering-expert',skills_root=skills_root,knowledge_root=base)
    if route.get('status')!='resolved':return None
    skills=Path(route['skills_root']).resolve()
    contract=json.loads((base/'learning_owner_contract.json').read_text(encoding='utf-8'))
    if contract.get('schema')!='knowledge-learning-owner-contract-v1':raise ValueError('Unknown learning owner contract')
    paths={}
    for row in contract['files']:
        path=(skills/row['path']).resolve()
        if not path.is_relative_to(skills) or not path.is_file() or digest(path.read_bytes())!=row['sha256']:
            raise ValueError('Trusted learning owner identity mismatch: '+row['path'])
        paths[row['path']]=path
    evaluator=paths['chemical-engineering-expert/scripts/evaluate_learning_eligibility.py']
    helper=paths['aspen-document-driven-flowsheet/scripts/learning_admission.py']
    modules=[]
    for name,path in [('source_intrinsic_owner',evaluator),('existing_knowledge_learning_admission',helper)]:
        spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);modules.append(module)
    return {'evaluator':modules[0],'helper':modules[1],'evidence':[(path,digest(path.read_bytes())) for path in paths.values()]}


def experience_gate(change, directory, owners):
    """Reuse each node's existing closure/lineage/quality gate, never batch-wash."""
    evidence=change.get('experience',{})
    if not evidence.get('lineage_manifest') or not evidence.get('candidate_review'):
        return {'eligible':False,'reasons':['PER_NODE_CLOSURE_LINEAGE_AND_QUALITY_REQUIRED']}
    lineage=reference(evidence['lineage_manifest'],directory)
    review=reference(evidence['candidate_review'],directory)
    if owners is None:return {'eligible':False,'reasons':['EXPLICIT_TRUSTED_SKILLS_ROOT_REQUIRED']}
    module=owners['helper']
    admission=module.lineage_admission(str(lineage))
    admission=module.bind_proposed_rule(admission,[change['record']['text']])
    quality=module.quality_review(str(review),lineage_result=admission,base_dir=directory)
    eligible=admission.get('learning_eligible') is True and admission.get('task_closure_verified') is True and quality.get('candidate_review_ready') is True
    return {'eligible':eligible,'admission':admission,'quality':quality,'canonical_write_authorized':False}


def known_task_artifact(path, evaluator):
    """Route registered actual task records, not words such as 'case' in sources."""
    known=set(evaluator.AUDIT_SCHEMAS)|{evaluator.SCHEMA,'user-task-closure-event-v1',
        'aspen-parser-refactor-validation-v1','aspen_clean_delivery_audit/2',
        'knowledge-candidate-build-v1','knowledge-pending-intake-v1'}
    try:
        with path.open('rb') as stream:prefix=stream.read(256).lstrip(b'\xef\xbb\xbf \r\n\t')
        if not prefix.startswith((b'{',b'[')):return False
        if structured_payload_over_limit(path):return False  # Resource limit is not evidence of task origin.
        text=path.read_text(encoding='utf-8-sig')
        try:obj=json.loads(text)
        except json.JSONDecodeError:obj=[json.loads(line) for line in text.splitlines() if line.strip()]
    except (OSError,UnicodeError,json.JSONDecodeError):return False
    def visit(value):
        if isinstance(value,list):return any(visit(v) for v in value)
        if not isinstance(value,dict):return False
        if '$schema' in value and ('properties' in value or '$defs' in value):return False
        schema=value.get('schema',value.get('schema_version'))
        if isinstance(schema,str) and schema in known:return True
        return any(visit(v) for k,v in value.items() if k not in {'expected','expected_result','expected_output','expected_flags'})
    return visit(obj)


def inspect_intake(base, intake_path, review_path=None, skills_root=None):
    base=base.resolve();intake_path=intake_path.resolve()
    checked=verify(base)
    if checked['status']!='pass':raise ValueError('Base knowledge must verify: '+str(checked['problems']))
    manifest,records=load_records(base)
    raw=intake_path.read_bytes();intake=json.loads(raw)
    if intake.get('schema')!='knowledge-version-intake-v1':raise ValueError('Unknown intake schema')
    if intake.get('base_manifest_sha256')!=digest((base/'manifest.json').read_bytes()):raise ValueError('Base version drift')
    if intake.get('intake_kind') not in {'direct_source','task_experience'}:raise ValueError('Choose source maintenance or task experience')
    if not isinstance(intake.get('proposer_id'),str) or not intake['proposer_id'].strip():raise ValueError('Proposer identity required')
    changes=intake.get('changes')
    if not isinstance(changes,list) or not 1<=len(changes)<=100:raise ValueError('Provide 1..100 atomic changes')
    old={(r['corpus'],r['node_id']):r for r in records};new_ids=set();changed_old=set();hashes=[];evidence=[]
    for change in changes:
        if change.get('operation') not in {'add','supersede'}:raise ValueError('Only add or source-preserving supersede is supported')
        r=change.get('record',{})
        if any(not isinstance(r.get(k),str) or not r[k].strip() for k in ('node_id','title','text','units_basis')):raise ValueError('Node identity, original body and units/basis required')
        if r.get('corpus') not in CORPORA or r.get('knowledge_layer') not in {'L3','L2','L1','L0'}:raise ValueError('Invalid corpus/layer')
        if r.get('evidence_class')!='X' or r.get('authority_scope')!='shared' or r.get('project_value_transfer_allowed') is not False:raise ValueError('Source knowledge must remain shared X, not project authority')
        if any(not isinstance(r.get(k),list) or not r[k] or any(not isinstance(v,str) or not v.strip() for v in r[k]) for k in ('applicability','forbidden_transfer')):raise ValueError('Applicability and exclusions require nonempty text lists')
        identity=(r['corpus'],r['node_id'])
        if identity in old or identity in new_ids:raise ValueError('New record identity collides with preserved node')
        new_ids.add(identity)
        if change['operation']=='supersede':
            previous=change.get('supersedes',{});key=(previous.get('corpus'),previous.get('node_id'))
            if key not in old or key in changed_old or old[key]['text_sha256']!=previous.get('text_sha256'):
                raise ValueError('Superseded node missing, duplicate, or identity drift')
            changed_old.add(key)
        source=change.get('source',{})
        source_path=reference(source,intake_path.parent)
        if not source.get('source_id') or not isinstance(source.get('locator'),str) or not source['locator'].strip():raise ValueError('Source ID and exact locator required')
        license=change.get('license',{})
        if license.get('distribution_scope') not in {'local_only','redistributable'} or not license.get('basis'):raise ValueError('Explicit license scope and basis required')
        if change.get('origin_kind') not in {'external_source','task_experience'}:raise ValueError('Origin classification required')
        if intake['intake_kind']=='direct_source' and change['origin_kind']!='external_source':raise ValueError('Task experience cannot enter the direct-source lane')
        if intake['intake_kind']=='task_experience' and change['origin_kind']!='task_experience':raise ValueError('Mixed intake lanes are not supported')
        hashes.append(digest(encoded(change)));evidence.append((source_path,source['sha256'].lower()))
    batch_sha=digest(encoded(hashes))
    review=None;review_by={};review_problem=None
    if review_path:
        review_path=review_path.resolve();review=json.loads(review_path.read_bytes())
        if review.get('schema')!='knowledge-intake-review-v1' or review.get('intake_sha256')!=digest(raw) or review.get('changes_sha256')!=batch_sha:
            raise ValueError('Review does not bind this exact complete intake')
        reviewed=review.get('changes',[])
        if not isinstance(reviewed,list) or len(reviewed)!=len(hashes) or {x.get('change_sha256') for x in reviewed}!=set(hashes):
            raise ValueError('Review must cover every change exactly once')
        if not review.get('reviewer_id') or review['reviewer_id']==intake['proposer_id']:raise ValueError('Separate review identity required')
        review_by={x['change_sha256']:x for x in reviewed}
    else:review_problem='INDEPENDENT_BATCH_REVIEW_REQUIRED'
    owners=trusted_learning_owners(base,skills_root)
    if owners:evidence.extend(owners['evidence'])
    decisions=[];experience_ids=set()
    for change,key in zip(changes,hashes):
        reasons=[];item=review_by.get(key)
        if (reason:=relaxation_reason(change)) or (reason:=relaxation_reason(intake.get('lineage',{}))):reasons.append(reason)
        if change.get('relaxation_applied') is not False:reasons.append('RELAXATION_STATE_NOT_EXPLICIT')
        if owners is None:reasons.append('TRUSTED_INTRINSIC_POLICY_OWNER_REQUIRED')
        elif structured_payload_over_limit(evidence[hashes.index(key)][0]):reasons.append('SOURCE_STRUCTURED_PAYLOAD_REVIEW_LIMIT')
        elif owners['evaluator'].intrinsic_exclusion(change['source'],intake_path.parent):reasons.append('SOURCE_INTRINSIC_EXCLUSION')
        if owners and intake['intake_kind']=='direct_source' and known_task_artifact(evidence[hashes.index(key)][0],owners['evaluator']):
            reasons.append('TASK_ARTIFACT_REQUIRES_EXPERIENCE_LANE')
        if review_problem:reasons.append(review_problem)
        if item:
            if item.get('decision') not in {'admit_source_candidate','hold'}:raise ValueError('Unknown review decision')
            if item['decision']=='hold':reasons.append('REVIEW_HELD')
            expected={'source_sha256':change['source']['sha256'].lower(),'text_sha256':digest(change['record']['text'].encode()),'knowledge_layer':change['record']['knowledge_layer'],'distribution_scope':change['license']['distribution_scope']}
            if any(item.get(k)!=v for k,v in expected.items()) or not item.get('basis'):raise ValueError('Per-node review binding incomplete')
            proof=reference(item.get('evidence'),review_path.parent)
            evidence.append((proof,item['evidence']['sha256'].lower()))
            if proof==intake_path or proof==evidence[hashes.index(key)][0]:raise ValueError('Review evidence must be separate from intake/source')
            if structured_payload_over_limit(proof):reasons.append('REVIEW_PROOF_STRUCTURED_PAYLOAD_REVIEW_LIMIT')
            elif owners and owners['evaluator'].intrinsic_exclusion(item['evidence'],review_path.parent):reasons.append('REVIEW_EVIDENCE_INTRINSIC_EXCLUSION')
        gate=None
        if intake['intake_kind']=='task_experience':
            experience=change.get('experience',{})
            pair=(experience.get('lineage_manifest',{}).get('sha256'),experience.get('candidate_review',{}).get('sha256'))
            if pair in experience_ids and pair!=(None,None):raise ValueError('Each node needs its own bound experience review, not one root for a batch')
            experience_ids.add(pair)
            gate=experience_gate(change,intake_path.parent,owners)
            if not gate['eligible']:reasons.append('EXISTING_EVOLUTION_GATE_NOT_READY')
        decisions.append({'change_sha256':key,'node_id':change['record']['node_id'],'corpus':change['record']['corpus'],'admitted':not reasons,'reasons':reasons,'experience_gate':gate})
    return {'manifest':manifest,'records':records,'intake':intake,'intake_sha256':digest(raw),'changes_sha256':batch_sha,'decisions':decisions,'evidence':evidence,
            'review_sha256':digest(review_path.read_bytes()) if review_path else None}


def write_manifest(root, template, records, extra_metadata=None):
    """Internal seal of the explicitly isolated candidate tree, not promotion."""
    old={item['path']:item for item in template['files']}
    manifest=copy.deepcopy(template);manifest['records']=len(records)
    manifest['corpus_record_counts']={c:sum(r['corpus']==c for r in records) for c in CORPORA}
    manifest['layer_record_counts']={c:dict(Counter(r['knowledge_layer'] for r in records if r['corpus']==c)) for c in CORPORA}
    manifest['files']=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path==root/'manifest.json' or '__pycache__' in path.parts or path.suffix=='.pyc':continue
        rel=path.relative_to(root).as_posix();raw=path.read_bytes()
        item={**old.get(rel,{'kind':'isolated_knowledge_candidate_artifact'}),'path':rel,'bytes':len(raw),'sha256':digest(raw)}
        manifest['files'].append(item)
    manifest.update(extra_metadata or {})
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return manifest


def build_version(base, intake_path, output, review_path=None, skills_root=None):
    base=base.resolve();output=output.absolute()
    if output.exists() or not output.parent.is_dir():raise ValueError('Output must not exist and its parent must already exist')
    output=output.resolve()
    if output.is_relative_to(base.parent) or base.parent.is_relative_to(output):raise ValueError('Output must be disjoint from the active product')
    from resolve_knowledge_owner import resolve_knowledge_owner
    owner=resolve_knowledge_owner('chemical-engineering-expert',skills_root=skills_root,knowledge_root=base)
    if owner.get('skills_root'):
        active_skills=Path(owner['skills_root']).resolve()
        if output.is_relative_to(active_skills) or active_skills.is_relative_to(output):raise ValueError('Output must be disjoint from active Skills')
    inspected=inspect_intake(base,intake_path,review_path,skills_root)
    scripts=base.parent/'workspace/scripts'
    for name in SCRIPT_NAMES:
        if not (scripts/name).is_file():raise ValueError('Current product algorithm dependency missing: '+name)
    import vector_adapter
    if scripts.resolve()!=vector_adapter.WORKSPACE_SCRIPTS.resolve():raise ValueError('Base must belong to the same explicit product as this builder')
    dependencies={name:digest((scripts/name).read_bytes()) for name in SCRIPT_NAMES}
    records=copy.deepcopy(inspected['records']);lookup={(r['corpus'],r['node_id']):r for r in records}
    pending=[];new_payloads={}
    for change,decision in zip(inspected['intake']['changes'],inspected['decisions']):
        if not decision['admitted']:
            pending.append({'change':change,'decision':decision,'default_retrieval_eligible':False,'learning_eligible':False});continue
        supplied=change['record'];key=decision['change_sha256'];rel='intake/nodes/'+key+'.json'
        r={**supplied,'text_sha256':digest(supplied['text'].encode()),'knowledge_status':'source_reviewed_candidate_version','public_path':rel,
           'source':{'source_id':change['source']['source_id'],'relative_path':Path(change['source']['path']).name,'sha256':change['source']['sha256'].lower(),'locator':change['source']['locator']},
           'source_payload_available':False,'content_available':True,'retrieval_eligible':True,'current_project_authority':False,
           'license':change['license'],'candidate_release_only':True,'canonical_write_authorized':False}
        if change['operation']=='supersede':
            previous=change['supersedes'];prior=lookup[(previous['corpus'],previous['node_id'])]
            prior['retrieval_eligible']=False;prior['knowledge_status']='superseded';prior['superseded_by']=r['node_id']
            r['supersedes']=previous
        records.append(r);new_payloads[rel]=encoded(r)
    receipt={'schema':'knowledge-candidate-build-v1','status':'candidate_release_review_only','base_manifest_sha256':digest((base/'manifest.json').read_bytes()),
             'intake_sha256':inspected['intake_sha256'],'changes_sha256':inspected['changes_sha256'],'review_sha256':inspected['review_sha256'],
             'admitted_count':sum(x['admitted'] for x in inspected['decisions']),'pending_count':len(pending),'decisions':inspected['decisions'],
             'record_scope':'candidate_review_only','default_retrieval_eligible':False,'learning_eligible':False,
             'default_active_library_updated':False,'canonical_write_authorized':False,'engineering_acceptance_verified':False,'publication_authorized':False}
    relative_files=sorted({'knowledge/'+entry['path'] for entry in inspected['manifest']['files']}
                          | {'knowledge/'+path for path in new_payloads}
                          | {'knowledge/manifest.json','knowledge/records.jsonl','knowledge/candidate_intake.json','knowledge/VERSION_REVIEW.json'}
                          | {'workspace/scripts/'+name for name in SCRIPT_NAMES})
    final_budget=windows_path_preflight(output,relative_files,phase='final',requested_output=output)
    # Source drift, admission and full batch coverage are decided before mkdir/copy.
    for path,expected in inspected['evidence']:
        if digest(path.read_bytes())!=expected:raise ValueError('Source changed during preflight')
    with tempfile.TemporaryDirectory(prefix='.kc-',dir=output.parent) as temporary:
        stage=Path(temporary)/'v'
        stage_budget=windows_path_preflight(stage,relative_files,phase='staging',requested_output=output)
        receipt['path_preflight']={'final':final_budget,'staging':stage_budget,'system_configuration_changed':False}
        target=stage/'knowledge';target.mkdir(parents=True)
        for entry in inspected['manifest']['files']:
            source=base/entry['path'];dest=target/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            if digest(source.read_bytes())!=entry['sha256']:raise ValueError('Base changed after validation')
            shutil.copyfile(source,dest)
        for rel,raw in new_payloads.items():
            dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        (target/'records.jsonl').write_bytes(b''.join(json.dumps(r,ensure_ascii=False).encode()+b'\n' for r in records))
        (target/'candidate_intake.json').write_bytes(encoded({'schema':'knowledge-pending-intake-v1','default_retrieval_eligible':False,'learning_eligible':False,'pending':pending}))
        (target/'VERSION_REVIEW.json').write_bytes(encoded(receipt))
        output_scripts=stage/'workspace/scripts';output_scripts.mkdir(parents=True)
        for name in SCRIPT_NAMES:shutil.copyfile(scripts/name,output_scripts/name)
        write_manifest(target,inspected['manifest'],records,{'candidate_version':receipt})
        vector_adapter.build(root=target)
        write_manifest(target,inspected['manifest'],records,{'candidate_version':receipt})
        result=verify(target)
        if result['status']!='pass':raise ValueError('Candidate failed verification: '+str(result['problems']))
        for name,expected in dependencies.items():
            if digest((scripts/name).read_bytes())!=expected or digest((output_scripts/name).read_bytes())!=expected:raise ValueError('Algorithm dependency changed')
        for path,expected in inspected['evidence']:
            if digest(path.read_bytes())!=expected:raise ValueError('Source changed during candidate build')
        stage.rename(output)
    return {**receipt,'output':str(output),'knowledge_manifest_sha256':digest((output/'knowledge/manifest.json').read_bytes()),'verification':result}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT)
    parser.add_argument('--intake',type=Path,required=True)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--skills-root',type=Path)
    parser.add_argument('--inspect',action='store_true',help='Print exact change hashes and admission; do not write a candidate')
    args=parser.parse_args()
    try:
        if args.inspect:
            checked=inspect_intake(args.base,args.intake,args.review,args.skills_root)
            result={k:checked[k] for k in ('intake_sha256','changes_sha256','decisions')}
        else:
            if args.output is None:raise ValueError('--output is required for candidate construction')
            result=build_version(args.base,args.intake,args.output,args.review,args.skills_root)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 0 if all(d['admitted'] for d in result['decisions']) else 2
    except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps({'status':'not_built','reason':str(exc)},ensure_ascii=False));return 2


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
