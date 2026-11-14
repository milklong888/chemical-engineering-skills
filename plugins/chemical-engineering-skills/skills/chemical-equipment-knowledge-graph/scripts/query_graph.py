"""Query an active graph or an unpacked snapshot without changing stored paths."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import subprocess
import sys


ORIGINAL_ROOT = PureWindowsPath('E:/设备设计')
QUERIES = {
    'design': 'query_design.py',
    'increment': 'query_increment.py',
    'image-ocr': 'query_image_ocr.py',
}
SOURCE_TREES = ('教材手册', '设备设计')


def local_copy(value, root, source_root):
    path = PureWindowsPath(value)
    if not path.is_relative_to(ORIGINAL_ROOT):
        return None
    relative = path.relative_to(ORIGINAL_ROOT)
    if len(relative.parts) < 2 or '..' in relative.parts or any(':' in part for part in relative.parts):
        return None
    if relative.parts[0] in SOURCE_TREES:
        target_root = source_root
    elif relative.parts[0] == '知识图谱':
        target_root = root
    else:
        return None
    target = target_root.joinpath(*relative.parts)
    if target.is_file() and target.resolve().is_relative_to(target_root):
        return target
    return None


def collect_paths(value, root, source_root, resolved):
    if isinstance(value, dict):
        for child in value.values():
            collect_paths(child, root, source_root, resolved)
    elif isinstance(value, list):
        for child in value:
            collect_paths(child, root, source_root, resolved)
    elif isinstance(value, str) and value[:3] in ('E:\\', 'E:/', 'e:\\', 'e:/') and '\n' not in value:
        target = local_copy(value, root, source_root)
        if target and str(target) != value:
            resolved[value] = str(target)


def lookup_source(database, query, root, source_root):
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute('''
            SELECT id AS source_id, path, physical_path, parent AS parent_source_id,
                   size, sha256, license
            FROM sources WHERE id=? OR replace(path, char(92), '/')=? ORDER BY id
        ''', (query, query.replace('\\', '/'))).fetchall()
    results = []
    for row in rows:
        record = dict(row)
        target = local_copy(row['physical_path'], root, source_root)
        record['local_path'] = str(target) if target else None
        results.append(record)
    return {'query': query, 'sources': results}


def print_json(result):
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='查询化工设备活动图谱或解包后的成果快照')
    parser.add_argument('--root', type=Path, help='包含知识图谱的根目录。也可设置 CHEMICAL_KG_ROOT 或从库内运行')
    parser.add_argument('--source-root', type=Path, help='另行迁移的教材手册及设备设计原件所在根路径')
    parser.add_argument('query_type', choices=[*QUERIES, 'source'])
    parser.add_argument('query_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    configured_root = args.root or os.environ.get('CHEMICAL_KG_ROOT')
    root = Path(configured_root).resolve() if configured_root else next(
        (directory for directory in (Path.cwd(), *Path.cwd().parents)
         if (directory / '知识图谱' / 'knowledge.sqlite').is_file()), None)
    if root is None:
        parser.error('请用 --root 或 CHEMICAL_KG_ROOT 指定知识图谱所在根目录')
    source_root = (args.source_root or root).resolve()
    graph = root / '知识图谱'
    if args.query_type == 'source':
        if len(args.query_args) != 1:
            parser.error('source 需要一个来源 ID 或精确相对路径')
        database = graph / 'knowledge.sqlite'
        if not database.is_file():
            parser.error(f'所选工作区缺少 {database}')
        result = lookup_source(database, args.query_args[0], root, source_root)
        print_json(result)
        return 0 if result['sources'] else 1
    script = graph / 'scripts' / QUERIES[args.query_type]
    required = (script, graph / 'knowledge.sqlite', graph / 'increment.sqlite')
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        parser.error('所选工作区缺少 ' + '、'.join(missing))
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    child = subprocess.run([sys.executable, '-B', str(script), *args.query_args], cwd=root,
                           env=env, capture_output=True, encoding='utf-8')
    if child.stderr:
        sys.stderr.write(child.stderr)
    if child.returncode:
        if child.stdout:
            sys.stdout.write(child.stdout)
        return child.returncode
    if args.query_args and args.query_args[0] in ('-h', '--help'):
        sys.stdout.write(child.stdout)
        return 0
    result = json.loads(child.stdout)
    resolved = {}
    collect_paths(result, root, source_root, resolved)
    if resolved:
        result['path_resolution'] = resolved
    print_json(result)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
