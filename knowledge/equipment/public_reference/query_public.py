"""Search the bundled public catalog, which runs without a local graph database."""

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata


REFERENCES = Path(__file__).resolve().parents[1] / 'references'
CATALOGS = {
    'standard': ('设备设计结果要求', 'public_standards.json'),
    'book': ('设计过程参考书目', 'public_books.json'),
    'method': ('公开方法索引', 'public_methods.json'),
}
OVERVIEW = 'PUBLIC_CATALOG.md'


def catalog(kind, references=REFERENCES):
    kinds = CATALOGS if kind == 'all' else (kind,)
    for category in kinds:
        _, filename = CATALOGS[category]
        for entry in json.loads((references / filename).read_text(encoding='utf-8')):
            yield {'kind': category, **entry}


def search_key(text):
    normalized = unicodedata.normalize('NFKC', text).casefold()
    return re.sub(r'[\W_]+', '', normalized)


def matches(entry, query):
    fields = [entry['id'], entry['title'], *entry['topics'], entry['coverage']]
    for location in entry['locations']:
        fields.extend([location['anchor'], location['note']])
    keys = [search_key(field) for field in fields]
    query = unicodedata.normalize('NFKC', query)
    words = [key for word in query.split() if (key := search_key(word))]
    if not words:
        return True
    return (any(search_key(query) in key for key in keys)
            or all(any(word in key for key in keys) for word in words))


def lookup(query, kind='all', limit=30, references=REFERENCES, record_id=None):
    hits = [entry for entry in catalog(kind, references)
            if (search_key(entry['id']) == search_key(record_id) if record_id else matches(entry, query))]
    return {'query': query, 'kind': kind, 'total': len(hits), 'hits': hits[:limit]}


def render_catalog():
    lines = [
        '# 化工设备知识图谱公开资料索引',
        '',
        '可用浏览器查找标准号、表号或主题。标准编号与定位信息指向相应版次，',
        '项目使用时请在官方入口核对现行性和适用范围。公开书目和方法供设计过程参考。',
        '公开索引提供来源、位置与查阅链接。原件及本地图谱按各自许可使用。',
        '',
        '安装「化工设计专家工作库」后，可用 `query_graph.py public "GB/T 150.2-2024 表C.2"`',
        '或 `query_graph.py public NPSH --kind method` 检索本页；命令用法见[查询说明](query.md)。',
    ]
    for kind, (label, filename) in CATALOGS.items():
        lines.extend(['', f'## {label}', '', f'[机器可读索引]({filename})'])
        for entry in catalog(kind):
            title = entry['title']
            heading = f"{entry['id']} {title}" if kind == 'standard' else title
            lines.extend(['', f'### {heading}', '', entry['coverage'], ''])
            lines.append('检索词　' + '、'.join(entry['topics']))
            if entry['locations']:
                lines.append('')
                for location in entry['locations']:
                    lines.append(f"- **{location['anchor']}**　{location['note']}")
            lines.extend(['', ' · '.join(f"[{link['label']}]({link['url']})" for link in entry['links'])])
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='检索化工设备知识图谱公开索引')
    parser.add_argument('query', nargs='?', default='', help='标准号、表号、书名或主题')
    parser.add_argument('--kind', choices=['all', *CATALOGS], default='all')
    parser.add_argument('--limit', type=int, default=30)
    parser.add_argument('--markdown', action='store_true', help=f'输出 {OVERVIEW} 的完整 Markdown')
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error('--limit 须为正整数')
    if args.markdown:
        print(render_catalog(), end='')
        return 0
    print(json.dumps(lookup(args.query, args.kind, args.limit), ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
