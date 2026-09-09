"""Resolve a logical knowledge owner without inventing an installed plugins tree."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OWNERS={
    'chemical-engineering-expert': ['SKILL.md','references/ERROR_MEMORY.md','references/EVOLUTION_LOOP.md','references/STRICT_ACCEPTANCE_AND_LEARNING.md'],
    'equipment-design-app': ['SKILL.md','references/ERROR_MEMORY.md'],
    'chemical-equipment-selection-audit': ['SKILL.md','references/ERROR_MEMORY.md'],
}


def resolve_knowledge_owner(owner_id: str, *, skills_root: Path | None=None,
                            workspace_root: Path | None=None, knowledge_root: Path=ROOT) -> dict:
    if owner_id not in OWNERS: raise ValueError('Unknown logical owner')
    product=knowledge_root.resolve().parent
    route_path=None
    if skills_root is None:
        bundled=product/'plugins/chemical-engineering-skills/skills'
        if bundled.is_dir(): skills_root=bundled
        else:
            workspace=workspace_root.resolve() if workspace_root else product.parent
            route_path=workspace/'LOCAL_KNOWLEDGE_GRAPH_LINKS.md'
            if route_path.is_file():
                match=re.search(r'安装后的技能根为\s*`([^`]+)`',route_path.read_text(encoding='utf-8'))
                if match and '{' not in match.group(1) and Path(match.group(1)).is_absolute():
                    skills_root=Path(match.group(1))
    if skills_root is None:
        return {'status':'explicit_skills_root_required','owner_id':owner_id,'files':{},
                'next_action':'Pass --skills-root for the installed Skill root; no second plugins tree is assumed.'}
    if not Path(skills_root).is_absolute(): raise ValueError('skills_root must be explicit absolute path')
    skill=(Path(skills_root)/owner_id).resolve()
    paths={rel:(skill/rel).resolve() for rel in OWNERS[owner_id]}
    if any(not path.is_relative_to(skill) for path in paths.values()): raise ValueError('Owner path escape')
    missing=[rel for rel,path in paths.items() if not path.is_file()]
    return {'status':'resolved' if not missing else 'owner_incomplete','owner_id':owner_id,
            'skills_root':str(Path(skills_root).resolve()),'files':{k:str(v) for k,v in paths.items()},
            'missing':missing,'workspace_route':str(route_path) if route_path and route_path.is_file() else None,
            'read_only':True,'duplicate_owner_created':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner',required=True,choices=sorted(OWNERS))
    parser.add_argument('--skills-root',type=Path)
    parser.add_argument('--workspace-root',type=Path)
    args=parser.parse_args()
    try:
        result=resolve_knowledge_owner(args.owner,skills_root=args.skills_root,workspace_root=args.workspace_root)
    except (ValueError,OSError) as exc:
        result={'status':'not_resolved','reason':str(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status']=='resolved' else 2


if __name__=='__main__':raise SystemExit(main())
