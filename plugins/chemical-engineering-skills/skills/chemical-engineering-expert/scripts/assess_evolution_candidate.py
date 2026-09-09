"""Assess a bounded evolution proposal; never write skills or run supplied code.

Lineage admission is separate from improvement. Frozen JSON oracles compare
actual artifact fields; a self-reported `passed` flag is not an oracle. This
still requires human review of evidence authenticity and engineering scope.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = 'chemical-evolution-review-v1'
RULE_FIELDS = ('trigger', 'observation', 'mechanism', 'action', 'verification', 'boundary')

def reference(ref, base_dir):
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise ValueError('Reference needs path and SHA256')
    path = Path(ref['path']); path = path if path.is_absolute() else base_dir/path
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest().upper()
    if digest != str(ref.get('sha256', '')).upper():
        raise ValueError('Reference identity mismatch: '+str(path))
    return path.resolve(), data, digest

def json_ref(ref, base_dir):
    path, data, digest = reference(ref, base_dir)
    return path, json.loads(data.decode('utf-8-sig')), digest

def pointer(value, path):
    if path == '': return value
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Use a JSON pointer')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        value=value[int(part)] if isinstance(value,list) else value[part]
    return value

def numeric(value):
    try:return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)
    except OverflowError:return False

def satisfies(actual, assertion):
    try:
        value=pointer(actual,assertion['pointer']); expected=assertion.get('expected'); op=assertion['op']
        if op=='eq': return type(value) is type(expected) and value==expected
        if op=='ne': return type(value) is not type(expected) or value!=expected
        if op=='finite': return numeric(value)
        if op in {'gte','lte'}:
            return numeric(value) and numeric(expected) and (value>=expected if op=='gte' else value<=expected)
        if op=='contains': return isinstance(value,(list,str)) and expected in value
    except (KeyError,TypeError,ValueError,IndexError): pass
    return False

def assess(proposal: dict, *, base_dir: Path, lineage_result: dict) -> dict:
    result={'schema':'chemical-evolution-assessment-v1','decision':'audit_only',
        'candidate_review_ready':False,'canonical_write_authorized':False,
        'default_retrieval_eligible':False,'missing_fields':[],'reasons':[], 'next_actions':[],
        'boundary':'Review readiness only, not engineering truth or publication authority. No supplied code is executed.'}
    if lineage_result.get('learning_eligible') is not True or lineage_result.get('task_closure_verified') is not True:
        result['reasons']=['LINEAGE_NOT_ELIGIBLE'];result['next_actions']=['Resolve source/lineage evidence; retain only project audit. Never relabel a relaxed ancestor.']
        return result
    result['decision']='needs_review_fields'
    if not isinstance(proposal,dict) or proposal.get('schema')!=SCHEMA:
        result['missing_fields']=['chemical-evolution-review-v1 proposal'];return result
    missing=result['missing_fields']
    channel=proposal.get('learning_channel')
    if channel not in {'prompt_principle','data_pattern'}:missing.append('learning_channel')
    if channel!=lineage_result.get('learning_channel'):missing.append('learning_channel must match the admitted final task')
    card=proposal.get('rule_card',{})
    if not isinstance(card,dict):card={}
    for field in RULE_FIELDS:
        if not isinstance(card.get(field),str) or not card[field].strip():missing.append('rule_card.'+field)
    if card.get('knowledge_layer') not in {'L3','L2','L1'}:missing.append('rule_card.knowledge_layer (raw L0 stays source evidence)')
    if channel=='prompt_principle' and card.get('knowledge_layer')!='L3':missing.append('prompt_principle must be macro L3; parameters stay in data_pattern/lower references')
    if not isinstance(card.get('decision_change'),str) or not card['decision_change'].strip():missing.append('rule_card.decision_change (observable change in judgment)')
    if card.get('claim_type') not in {'behavior','deterministic_method','engineering_heuristic','software_rule'}:missing.append('rule_card.claim_type')
    for field in ('valid_for','invalid_for'):
        values=card.get(field)
        if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v.strip() for v in values):
            missing.append('rule_card.'+field+' must be a nonempty list of scope statements')
    placement=proposal.get('placement',{})
    if not isinstance(placement,dict):placement={}
    for field in ('owner','target_path','anchor'):
        if not isinstance(placement.get(field),str) or not placement[field].strip():missing.append('placement.'+field)
    comparison=proposal.get('comparison',{})
    if not isinstance(comparison,dict):comparison={}
    if comparison.get('decision') not in {'new_gap','add','merge','specialize','replace','retract','no_change'}:missing.append('comparison.decision')
    if not comparison.get('reason') or not isinstance(comparison.get('existing_refs'),list) or not comparison['existing_refs']:missing.append('comparison with at least the existing owner/reference')
    if missing:
        result['next_actions']=['Complete only the named atomic rule/scope/owner fields; do not add generic reminders.'];return result
    try:
        baseline_path,baseline,baseline_sha=reference(proposal.get('baseline'),base_dir)
        candidate_path,candidate,candidate_sha=reference(proposal.get('candidate'),base_dir)
        candidate_record=json.loads(candidate.decode('utf-8-sig'))
        if not isinstance(candidate_record,dict) or candidate_record.get('rule_card')!=card or candidate_record.get('learning_channel')!=channel:
            raise ValueError('Rule card/channel differ from the exact admitted candidate JSON')
        root=lineage_result.get('root_artifact',{})
        if root.get('sha256','').upper()!=candidate_sha or Path(root.get('path','')).resolve()!=candidate_path:
            raise ValueError('Candidate differs from lineage-admitted root')
        target=Path(placement['target_path']);target=target if target.is_absolute() else base_dir/target
        if target.resolve()!=baseline_path:raise ValueError('Single target must be the current baseline owner file')
        if placement['anchor'] not in baseline.decode('utf-8-sig'):raise ValueError('Target anchor no longer exists')
        for ref in comparison['existing_refs']:reference(ref,base_dir)
        rollback_path,rollback,rollback_sha=reference(proposal.get('rollback_snapshot'),base_dir)
        if rollback_sha!=baseline_sha or rollback_path==baseline_path:raise ValueError('Independent exact baseline rollback snapshot required')
    except (OSError,ValueError,TypeError,KeyError,UnicodeError) as exc:
        result['reasons']=['TARGET_BINDING_OR_ROLLBACK_UNVERIFIED'];result['next_actions']=[str(exc)];return result
    if baseline==candidate or comparison['decision']=='no_change':
        result['decision']='not_improved';result['reasons']=['NO_CHANGE_NEEDED'];return result
    result['decision']='needs_validation'
    if not proposal.get('evaluation_plan') or not proposal.get('evaluation_result'):
        result['missing_fields']=['evaluation_plan','evaluation_result'];result['next_actions']=['Freeze relevant held-out/control inputs and independent JSON oracles, then compare current owner and exact candidate.'];return result
    try:
        plan_path,plan,plan_sha=json_ref(proposal['evaluation_plan'],base_dir)
        report_path,report,report_sha=json_ref(proposal['evaluation_result'],base_dir)
        if plan.get('schema')!='evolution-evaluation-plan-v1' or report.get('schema')!='evolution-evaluation-result-v1':raise ValueError('Unsupported evaluation schema')
        _,basis,basis_sha=json_ref(plan.get('basis'),plan_path.parent)
        if not isinstance(basis,dict) or not all(basis.get(k) for k in ('method','boundary','goal','tolerance','version')):
            raise ValueError('Frozen method/boundary/goal/tolerance/version basis required')
        if basis.get('analysis_target')=='simulator_convergence' and 'simulation_result' not in lineage_result.get('verified_evidence_kinds',[]):
            raise ValueError('Offline code verification cannot establish simulator-convergence learning')
        if plan.get('baseline_sha256','').upper()!=baseline_sha:raise ValueError('Evaluation baseline drifted')
        if report.get('plan_sha256','').upper()!=plan_sha or report.get('baseline_sha256','').upper()!=baseline_sha or report.get('candidate_sha256','').upper()!=candidate_sha:raise ValueError('Evaluation artifact identities differ')
        cases=plan.get('cases',[]);rows=report.get('cases',[])
        if not cases or not isinstance(cases,list) or not isinstance(rows,list):raise ValueError('No evaluation cases')
        ids=[c['id'] for c in cases];by_id={r['id']:r for r in rows}
        if len(set(ids))!=len(ids) or len(by_id)!=len(rows) or set(ids)!=set(by_id):raise ValueError('Duplicate/missing/unplanned evaluation cases')
        generation=set(plan.get('development_case_ids',[]))
        holdout={c['id'] for c in cases if c.get('split')=='holdout'}
        if not holdout or generation & holdout:raise ValueError('No uncontaminated held-out cases')
        required=plan.get('required_dimensions',[])
        covered={d for c in cases for d in c.get('dimensions',[])}
        if not required or not set(required)<=covered:raise ValueError('Frozen coverage incomplete')
        evaluations=[];improved=False;hard_regression=False
        for case in cases:
            row=by_id[case['id']]
            _,_,input_sha=reference(case['input'],plan_path.parent)
            _,oracle,oracle_sha=json_ref(case['oracle'],plan_path.parent)
            if row.get('input_sha256','').upper()!=input_sha or row.get('oracle_sha256','').upper()!=oracle_sha:raise ValueError('Input/oracle identity mismatch')
            _,old,_=json_ref(row['baseline_observation'],report_path.parent)
            _,new,_=json_ref(row['candidate_observation'],report_path.parent)
            for observation,subject_sha in ((old,baseline_sha),(new,candidate_sha)):
                if not isinstance(observation,dict) or observation.get('schema')!='evolution-observation-v1':
                    raise ValueError('Explicit observation envelope required')
                expected={'case_id':case['id'],'input_sha256':input_sha,'basis_sha256':basis_sha,'subject_sha256':subject_sha}
                if any(observation.get(key)!=value for key,value in expected.items()):
                    raise ValueError('Observation belongs to another case, input, method/basis or subject')
                if not isinstance(observation.get('values'),dict):raise ValueError('Observed values missing')
                _,raw_observation,_=json_ref(observation.get('raw_evidence'),report_path.parent)
                values_pointer=observation.get('values_pointer','/values')
                if pointer(raw_observation,values_pointer)!=observation['values']:
                    raise ValueError('Observation values differ from the hash-bound raw output/extraction')
            assertions=oracle.get('hard_requirements',[])
            if oracle.get('schema')!='evolution-json-oracle-v1' or not assertions:raise ValueError('Independent explicit oracle required; passed flags alone are not evidence')
            for assertion in assertions:
                ptr=assertion.get('pointer','')
                terminal=ptr.rsplit('/',1)[-1].casefold()
                if not ptr.startswith('/values/') or terminal in {'passed','ok','success','valid','accepted','approved','compliant','hard_pass','simulation_clean','delivery_verified'}:
                    raise ValueError('Oracle must inspect actual numeric/action fields, not self-reported pass flags')
                for observation in (old,new):
                    try:value=pointer(observation,ptr)
                    except (KeyError,IndexError,TypeError,ValueError):continue
                    if isinstance(value,bool):raise ValueError('Boolean self-assessment is not an independent observation oracle')
            old_ok=all(satisfies(old,a) for a in assertions);new_ok=all(satisfies(new,a) for a in assertions)
            hard_regression |= not new_ok
            case_gain=new_ok and not old_ok
            metric_rows=[]
            for metric in oracle.get('metrics',[]):
                before=pointer(old,metric['pointer']);after=pointer(new,metric['pointer']);direction=metric['direction']
                if not numeric(before) or not numeric(after) or direction not in {'lower','higher'}:raise ValueError('Invalid frozen quantitative metric')
                gain=(before-after) if direction=='lower' else (after-before)
                # No compensating a worse metric by improving a different one.
                hard_regression |= gain<0
                case_gain |= gain>0
                metric_rows.append({'pointer':metric['pointer'],'baseline':before,'candidate':after,'gain':gain})
            improved |= case_gain
            evaluations.append({'id':case['id'],'baseline_hard_pass':old_ok,'candidate_hard_pass':new_ok,'observed_improvement':case_gain,'metrics':metric_rows})
        result.update(evaluation={'plan_sha256':plan_sha,'report_sha256':report_sha,'cases':evaluations,'improved':improved,'regression':hard_regression})
        if hard_regression or not improved:
            result['decision']='not_improved';result['reasons']=['HARD_OR_METRIC_REGRESSION' if hard_regression else 'NO_OBSERVABLE_INCREMENT'];return result
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,IndexError) as exc:
        result['reasons']=['EVALUATION_NOT_VERIFIED'];result['next_actions']=[str(exc)];return result
    result['decision']='ready_for_manual_review';result['candidate_review_ready']=True
    result['next_actions']=['Independent reviewer checks mechanism, source authenticity, generalization bounds, conflicts, and current user authority before any canonical edit. Preserve exact before/after identities and affected-consumer rollback list.']
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proposal',type=Path);parser.add_argument('--lineage-manifest',type=Path,required=True)
    args=parser.parse_args()
    from evaluate_learning_eligibility import evaluate
    lineage=evaluate(json.loads(args.lineage_manifest.read_text(encoding='utf-8-sig')),base_dir=args.lineage_manifest.resolve().parent)
    proposal=json.loads(args.proposal.read_text(encoding='utf-8-sig'))
    result=assess(proposal,base_dir=args.proposal.resolve().parent,lineage_result=lineage)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['candidate_review_ready'] else 2

if __name__=='__main__':raise SystemExit(main())
