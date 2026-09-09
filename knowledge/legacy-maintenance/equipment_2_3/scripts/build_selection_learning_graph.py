from __future__ import annotations
import csv
import argparse
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
from pypdf import PdfReader
ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
STANDARDS_ROOT = WORKSPACE / '设计标准（反应器、塔、换热器、容器等）'
TABLE_DIR = ROOT / 'data' / 'tables'
KG = ROOT / 'knowledge_graph'
OUT = None
UNPACK_DIR = None

@dataclass
class GraphNode:
    node_id: str
    node_type: str
    label: str
    family: str
    source: str
    evidence_class: str
    summary: str

@dataclass
class GraphEdge:
    source: str
    relation: str
    target: str
    note: str

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def read_rows(path: Path) -> list[list[str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return [[cell.strip() for cell in row] for row in csv.reader(f)]

def sanitize_id(text: str) -> str:
    text = re.sub('\\s+', '_', text.strip())
    text = re.sub('[^0-9A-Za-z_\\-\\u4e00-\\u9fff]+', '_', text)
    return text.strip('_')[:80] or 'node'

def standard_family(path: Path) -> str:
    rel = path.relative_to(STANDARDS_ROOT)
    top = rel.parts[0] if rel.parts else ''
    if '反应器' in top:
        return 'fixed_bed_or_stirred_reactor'
    if '塔' in top:
        return 'tower_and_tower_vessel'
    if '换热器' in top:
        return 'heat_exchanger'
    if '容器' in top:
        return 'pressure_vessel_or_storage'
    return 'general'

def source_nature(name: str) -> str:
    if re.search('GB|HG|JB|NB|SH|T\\d', name, flags=re.I):
        return 'standard'
    if '手册' in name:
        return 'handbook'
    if '课程设计' in name or '毕业设计' in name:
        return 'case_forbidden_transfer'
    if '全书' in name or '设备' in name or 'Reactor Design' in name:
        return 'method_book'
    return 'reference'

def evidence_class(nature: str) -> str:
    return {'standard': 'S1-S2_entry; S3 only after exact table/page verification', 'handbook': 'S0-S1_method_only', 'method_book': 'S0-S1_method_only', 'case_forbidden_transfer': 'S0-S1_method_example; values forbidden_transfer'}.get(nature, 'S0_identity')

def pdf_info(path: Path) -> dict[str, str | int | bool]:
    info: dict[str, str | int | bool] = {'file': str(path.relative_to(WORKSPACE)), 'family': standard_family(path), 'source_nature': source_nature(path.name), 'evidence_class': evidence_class(source_nature(path.name)), 'header_status': 'not_checked', 'pages': '', 'encrypted': '', 'metadata_title': '', 'text_probe': 'not_checked'}
    try:
        with path.open('rb') as f:
            head = f.read(8)
        info['header_status'] = 'valid_pdf_header' if head.startswith(b'%PDF') else f"nonstandard_header:{head.hex(' ')}"
    except Exception as exc:
        info['header_status'] = f'header_error:{type(exc).__name__}'
    try:
        reader = PdfReader(str(path))
        info['encrypted'] = bool(reader.is_encrypted)
        info['pages'] = len(reader.pages)
        meta = reader.metadata or {}
        info['metadata_title'] = str(meta.get('/Title', '') or '')
        if not reader.is_encrypted and reader.pages:
            sample = ''
            for page in reader.pages[:min(2, len(reader.pages))]:
                try:
                    sample += page.extract_text() or ''
                except Exception:
                    pass
            sample = ' '.join(sample.split())
            info['text_probe'] = 'text_available' if len(sample) >= 40 else 'scanned_or_weak_text'
    except Exception as exc:
        info['text_probe'] = f'read_error:{type(exc).__name__}'
    return info

def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fields = list(rows[0].keys())
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def markdown_table(headers: list[str], rows: Iterable[Iterable[object]]) -> str:
    lines = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |']
    for row in rows:
        cells = [str(x).replace('\n', ' ').replace('|', '/') for x in row]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)

def table_path(doc: str, name: str) -> Path:
    target = (TABLE_DIR / doc / name).resolve()
    if not target.is_relative_to(TABLE_DIR.resolve()):
        raise ValueError('Table path escapes source root')
    return target

def build_selection_nodes(*, profile=None) -> tuple[list[GraphNode], list[GraphEdge], list[dict[str, str]]]:
    require_profile(profile)
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    reasoning: list[dict[str, str]] = []

    def add_reason(family: str, type_or_model: str, benefits: str, suitable_for: str, cautions: str, source: str, evidence: str=literal(profile, 'build_selection_nodes', 'v000')) -> None:
        node_id = joined(profile, 'build_selection_nodes', 's000', [sanitize_id(family), sanitize_id(type_or_model)])
        nodes.append(GraphNode(node_id=node_id, node_type=literal(profile, 'build_selection_nodes', 'v001'), label=type_or_model, family=family, source=source, evidence_class=evidence, summary=joined(profile, 'build_selection_nodes', 's001', [benefits, suitable_for, cautions])))
        edges.append(GraphEdge(family, literal(profile, 'build_selection_nodes', 'v002'), node_id, source))
        reasoning.append({literal(profile, 'build_selection_nodes', 'v003'): family, literal(profile, 'build_selection_nodes', 'v004'): type_or_model, literal(profile, 'build_selection_nodes', 'v005'): benefits, literal(profile, 'build_selection_nodes', 'v006'): suitable_for, literal(profile, 'build_selection_nodes', 'v007'): cautions, literal(profile, 'build_selection_nodes', 'v008'): source, literal(profile, 'build_selection_nodes', 'v009'): evidence})
    for row in read_csv(table_path(literal(profile, 'build_selection_nodes', 'v010'), literal(profile, 'build_selection_nodes', 'v011'))):
        add_reason(literal(profile, 'build_selection_nodes', 'v012'), row.get(literal(profile, 'build_selection_nodes', 'v013'), literal(profile, 'build_selection_nodes', 'v014')), row.get(literal(profile, 'build_selection_nodes', 'v015'), literal(profile, 'build_selection_nodes', 'v016')), row.get(literal(profile, 'build_selection_nodes', 'v017'), literal(profile, 'build_selection_nodes', 'v018')), row.get(literal(profile, 'build_selection_nodes', 'v019'), literal(profile, 'build_selection_nodes', 'v020')) + literal(profile, 'build_selection_nodes', 'v021'), literal(profile, 'build_selection_nodes', 'v022'))
    for row in read_csv(table_path(literal(profile, 'build_selection_nodes', 'v023'), literal(profile, 'build_selection_nodes', 'v024'))):
        add_reason(literal(profile, 'build_selection_nodes', 'v025'), row.get(literal(profile, 'build_selection_nodes', 'v026'), literal(profile, 'build_selection_nodes', 'v027')), joined(profile, 'build_selection_nodes', 's002', [row.get(literal(profile, 'build_selection_nodes', 'v028'), literal(profile, 'build_selection_nodes', 'v029')), row.get(literal(profile, 'build_selection_nodes', 'v030'), literal(profile, 'build_selection_nodes', 'v031'))]), literal(profile, 'build_selection_nodes', 'v032'), literal(profile, 'build_selection_nodes', 'v033'), literal(profile, 'build_selection_nodes', 'v034'))
    add_reason(literal(profile, 'build_selection_nodes', 'v035'), literal(profile, 'build_selection_nodes', 'v036'), literal(profile, 'build_selection_nodes', 'v037'), literal(profile, 'build_selection_nodes', 'v038'), literal(profile, 'build_selection_nodes', 'v039'), literal(profile, 'build_selection_nodes', 'v040'))
    add_reason(literal(profile, 'build_selection_nodes', 'v041'), literal(profile, 'build_selection_nodes', 'v042'), literal(profile, 'build_selection_nodes', 'v043'), literal(profile, 'build_selection_nodes', 'v044'), literal(profile, 'build_selection_nodes', 'v045'), literal(profile, 'build_selection_nodes', 'v046'))
    add_reason(literal(profile, 'build_selection_nodes', 'v047'), literal(profile, 'build_selection_nodes', 'v048'), literal(profile, 'build_selection_nodes', 'v049'), literal(profile, 'build_selection_nodes', 'v050'), literal(profile, 'build_selection_nodes', 'v051'), literal(profile, 'build_selection_nodes', 'v052'), literal(profile, 'build_selection_nodes', 'v053'))
    add_reason(literal(profile, 'build_selection_nodes', 'v054'), literal(profile, 'build_selection_nodes', 'v055'), literal(profile, 'build_selection_nodes', 'v056'), literal(profile, 'build_selection_nodes', 'v057'), literal(profile, 'build_selection_nodes', 'v058'), literal(profile, 'build_selection_nodes', 'v059'), literal(profile, 'build_selection_nodes', 'v060'))
    for row in read_csv(table_path(literal(profile, 'build_selection_nodes', 'v061'), literal(profile, 'build_selection_nodes', 'v062'))):
        add_reason(literal(profile, 'build_selection_nodes', 'v063'), row.get(literal(profile, 'build_selection_nodes', 'v064'), literal(profile, 'build_selection_nodes', 'v065')), row.get(literal(profile, 'build_selection_nodes', 'v066'), literal(profile, 'build_selection_nodes', 'v067')), literal(profile, 'build_selection_nodes', 'v068'), row.get(literal(profile, 'build_selection_nodes', 'v069'), literal(profile, 'build_selection_nodes', 'v070')) + literal(profile, 'build_selection_nodes', 'v071'), literal(profile, 'build_selection_nodes', 'v072'))
    add_reason(literal(profile, 'build_selection_nodes', 'v073'), literal(profile, 'build_selection_nodes', 'v074'), literal(profile, 'build_selection_nodes', 'v075'), literal(profile, 'build_selection_nodes', 'v076'), literal(profile, 'build_selection_nodes', 'v077'), literal(profile, 'build_selection_nodes', 'v078'))
    add_reason(literal(profile, 'build_selection_nodes', 'v079'), literal(profile, 'build_selection_nodes', 'v080'), literal(profile, 'build_selection_nodes', 'v081'), literal(profile, 'build_selection_nodes', 'v082'), literal(profile, 'build_selection_nodes', 'v083'), literal(profile, 'build_selection_nodes', 'v084'), literal(profile, 'build_selection_nodes', 'v085'))
    add_reason(literal(profile, 'build_selection_nodes', 'v086'), literal(profile, 'build_selection_nodes', 'v087'), literal(profile, 'build_selection_nodes', 'v088'), literal(profile, 'build_selection_nodes', 'v089'), literal(profile, 'build_selection_nodes', 'v090'), literal(profile, 'build_selection_nodes', 'v091'))
    add_reason(literal(profile, 'build_selection_nodes', 'v092'), literal(profile, 'build_selection_nodes', 'v093'), literal(profile, 'build_selection_nodes', 'v094'), literal(profile, 'build_selection_nodes', 'v095'), literal(profile, 'build_selection_nodes', 'v096'), literal(profile, 'build_selection_nodes', 'v097'))
    add_reason(literal(profile, 'build_selection_nodes', 'v098'), literal(profile, 'build_selection_nodes', 'v099'), literal(profile, 'build_selection_nodes', 'v100'), literal(profile, 'build_selection_nodes', 'v101'), literal(profile, 'build_selection_nodes', 'v102'), literal(profile, 'build_selection_nodes', 'v103'))
    add_reason(literal(profile, 'build_selection_nodes', 'v104'), literal(profile, 'build_selection_nodes', 'v105'), literal(profile, 'build_selection_nodes', 'v106'), literal(profile, 'build_selection_nodes', 'v107'), literal(profile, 'build_selection_nodes', 'v108'), literal(profile, 'build_selection_nodes', 'v109'))
    add_reason(literal(profile, 'build_selection_nodes', 'v110'), literal(profile, 'build_selection_nodes', 'v111'), literal(profile, 'build_selection_nodes', 'v112'), literal(profile, 'build_selection_nodes', 'v113'), literal(profile, 'build_selection_nodes', 'v114'), literal(profile, 'build_selection_nodes', 'v115'))
    add_reason(literal(profile, 'build_selection_nodes', 'v116'), literal(profile, 'build_selection_nodes', 'v117'), literal(profile, 'build_selection_nodes', 'v118'), literal(profile, 'build_selection_nodes', 'v119'), literal(profile, 'build_selection_nodes', 'v120'), literal(profile, 'build_selection_nodes', 'v121'))
    add_reason(literal(profile, 'build_selection_nodes', 'v122'), literal(profile, 'build_selection_nodes', 'v123'), literal(profile, 'build_selection_nodes', 'v124'), literal(profile, 'build_selection_nodes', 'v125'), literal(profile, 'build_selection_nodes', 'v126'), literal(profile, 'build_selection_nodes', 'v127'))
    add_reason(literal(profile, 'build_selection_nodes', 'v128'), literal(profile, 'build_selection_nodes', 'v129'), literal(profile, 'build_selection_nodes', 'v130'), literal(profile, 'build_selection_nodes', 'v131'), literal(profile, 'build_selection_nodes', 'v132'), literal(profile, 'build_selection_nodes', 'v133'))
    pump_type_notes = {literal(profile, 'build_selection_nodes', 'v134'): (literal(profile, 'build_selection_nodes', 'v141'), literal(profile, 'build_selection_nodes', 'v142')), literal(profile, 'build_selection_nodes', 'v135'): (literal(profile, 'build_selection_nodes', 'v143'), literal(profile, 'build_selection_nodes', 'v144')), literal(profile, 'build_selection_nodes', 'v136'): (literal(profile, 'build_selection_nodes', 'v145'), literal(profile, 'build_selection_nodes', 'v146')), literal(profile, 'build_selection_nodes', 'v137'): (literal(profile, 'build_selection_nodes', 'v147'), literal(profile, 'build_selection_nodes', 'v148')), literal(profile, 'build_selection_nodes', 'v138'): (literal(profile, 'build_selection_nodes', 'v149'), literal(profile, 'build_selection_nodes', 'v150')), literal(profile, 'build_selection_nodes', 'v139'): (literal(profile, 'build_selection_nodes', 'v151'), literal(profile, 'build_selection_nodes', 'v152')), literal(profile, 'build_selection_nodes', 'v140'): (literal(profile, 'build_selection_nodes', 'v153'), literal(profile, 'build_selection_nodes', 'v154'))}
    seen_pumps: set[str] = set()
    for row in read_csv(table_path(literal(profile, 'build_selection_nodes', 'v155'), literal(profile, 'build_selection_nodes', 'v156'))):
        pump_type = row.get(literal(profile, 'build_selection_nodes', 'v157'), literal(profile, 'build_selection_nodes', 'v158'))
        if pump_type and pump_type not in seen_pumps:
            benefit, caution = pump_type_notes.get(pump_type, (literal(profile, 'build_selection_nodes', 'v159'), literal(profile, 'build_selection_nodes', 'v160')))
            add_reason(literal(profile, 'build_selection_nodes', 'v161'), pump_type, benefit, joined(profile, 'build_selection_nodes', 's003', [row.get(literal(profile, 'build_selection_nodes', 'v162'), literal(profile, 'build_selection_nodes', 'v163'))]), caution, literal(profile, 'build_selection_nodes', 'v164'), literal(profile, 'build_selection_nodes', 'v165'))
            seen_pumps.add(pump_type)
    add_reason(literal(profile, 'build_selection_nodes', 'v166'), literal(profile, 'build_selection_nodes', 'v167'), literal(profile, 'build_selection_nodes', 'v168'), literal(profile, 'build_selection_nodes', 'v169'), literal(profile, 'build_selection_nodes', 'v170'), literal(profile, 'build_selection_nodes', 'v171'), literal(profile, 'build_selection_nodes', 'v172'))
    add_reason(literal(profile, 'build_selection_nodes', 'v173'), literal(profile, 'build_selection_nodes', 'v174'), literal(profile, 'build_selection_nodes', 'v175'), literal(profile, 'build_selection_nodes', 'v176'), literal(profile, 'build_selection_nodes', 'v177'), literal(profile, 'build_selection_nodes', 'v178'))
    add_reason(literal(profile, 'build_selection_nodes', 'v179'), literal(profile, 'build_selection_nodes', 'v180'), literal(profile, 'build_selection_nodes', 'v181'), literal(profile, 'build_selection_nodes', 'v182'), literal(profile, 'build_selection_nodes', 'v183'), literal(profile, 'build_selection_nodes', 'v184'))
    matrix_node_id = literal(profile, 'build_selection_nodes', 'v185')
    nodes.append(GraphNode(node_id=matrix_node_id, node_type=literal(profile, 'build_selection_nodes', 'v186'), label=literal(profile, 'build_selection_nodes', 'v187'), family=literal(profile, 'build_selection_nodes', 'v188'), source=literal(profile, 'build_selection_nodes', 'v189'), evidence_class=literal(profile, 'build_selection_nodes', 'v190'), summary=literal(profile, 'build_selection_nodes', 'v191')))
    edges.append(GraphEdge(literal(profile, 'build_selection_nodes', 'v192'), literal(profile, 'build_selection_nodes', 'v193'), matrix_node_id, literal(profile, 'build_selection_nodes', 'v194')))
    return (nodes, edges, reasoning)

def build_zip_audit() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    standard_zips = list(STANDARDS_ROOT.rglob('*.zip')) if STANDARDS_ROOT.exists() else []
    UNPACK_DIR.mkdir(parents=True, exist_ok=True)
    for zpath in standard_zips:
        dest = UNPACK_DIR / sanitize_id(str(zpath.relative_to(STANDARDS_ROOT)))
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as zf:
            members = zf.namelist()
            zf.extractall(dest)
        rows.append({'zip_path': str(zpath.relative_to(WORKSPACE)), 'member_count': len(members), 'extracted_to': str(dest.relative_to(WORKSPACE)), 'status': 'extracted_standard_zip'})
    if not standard_zips:
        rows.append({'zip_path': str(STANDARDS_ROOT.relative_to(WORKSPACE)), 'member_count': 0, 'extracted_to': '', 'status': 'no_zip_found_under_design_standards_current_scan'})
    return rows

def build_standard_inventory() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for pdf in sorted(STANDARDS_ROOT.rglob('*.pdf')):
        rows.append(pdf_info(pdf))
    return rows

def write_outputs(*, profile=None) -> None:
    require_profile(profile)
    OUT.mkdir(parents=True, exist_ok=True)
    standard_rows = build_standard_inventory()
    zip_rows = build_zip_audit()
    nodes, edges, reasoning = build_selection_nodes(profile=profile)
    write_csv(OUT / 'standard_source_inventory.csv', standard_rows)
    write_csv(OUT / 'zip_unpack_audit.csv', zip_rows)
    write_csv(OUT / 'selection_reasoning_table.csv', reasoning)
    graph = {'generated_from': str(ROOT), 'standard_pdf_count_current_scan': len(standard_rows), 'zip_audit': zip_rows, 'nodes': [asdict(n) for n in nodes], 'edges': [asdict(e) for e in edges]}
    (OUT / 'selection_learning_graph.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')
    fam_counts = Counter((row['family'] for row in standard_rows))
    nature_counts = Counter((row['source_nature'] for row in standard_rows))
    (OUT / 'README.md').write_text('\n'.join([literal(profile, 'write_outputs', 'v000'), '', '本目录是本轮设备选型前的学习层，不覆盖原有设备知识图谱。', '', '## 文件', '', '- `equipment_selection_workflow_nodes.md`：设备选型说明书应采用的章节和证据结构。', '- `equipment_selection_parameter_calculation_matrix.md`：按设备族整理“需要什么参数、先算什么、怎么算完再选择、还缺什么正式证据”。', '- `selection_reasoning_nodes.md`：从报告表格反向提取的型号/型式优点、适用场景和证据边界。', '- `standard_source_inventory.md` / `.csv`：当前标准目录 PDF 文件级索引。', '- `zip_unpack_audit.md` / `.csv`：标准目录 zip 解包审计。', '- `selection_learning_graph.json`：机器可读节点和边。', '', '## 当前扫描结论', '', f'- 当前标准目录实扫 PDF：{len(standard_rows)} 份。', f"- 标准目录 zip：{sum((1 for r in zip_rows if r['status'] == 'extracted_standard_zip'))} 份。", literal(profile, 'write_outputs', 'v001'), '- 未发现可自动升级为项目数值默认值的标准示例值；标准/手册优先作为查表入口和方法源。', '- 设备型号/型式选择需分成：项目工况输入、型式理由、公式筛错、软件/厂家边界、正式证据。', '- 每台设备正文应先列输入参数，再列可闭合计算，最后落到型式/型号选择；没有计算和软件/厂家/标准证据时，不写“选型通过”。', '- 当前阶段精度控制到设备选型一览表级别：够说明型式/型号、关键尺寸、操作/设计条件和筛选计算依据即可，不替代施工图、EDR/SW6详细报告或厂家最终选型书。', '', '## 标准族分布', '', markdown_table(['设备族', '文件数'], sorted(fam_counts.items())), '', '## 来源性质分布', '', markdown_table(['来源性质', '文件数'], sorted(nature_counts.items())), '']) + '\n', encoding='utf-8')
    workflow_rows = [('1 设计依据与适用范围', '列出标准、手册、软件、项目 Aspen/文档来源；先说明哪些是方法源、哪些是正式证据。', '避免把教材/毕业设计/其他设备数值当作本项目默认值。'), ('2 工况与物性来源', '写清进出口流股、T/P/流量/相态/介质/腐蚀性/是否真空或高压。', '能从 Aspen 或权威表抽取的，不用泛泛写。'), ('3 型式选择', '比较可选设备型式，说明为什么选填料塔、板式塔、BEM 换热器、离心泵等。', '这一段要反向写出优点和适用性，不能只贴型号。'), ('4 初步计算', '能脚本化的先闭合：接管流速、设计压力、壁厚基础式、泵功率、压比、几何容积等。', '计算只能证明筛错或预选，不能越界替代 EDR/SW6/厂家。'), ('5 软件/厂家校核', '塔走 Column Internals，换热器走 EDR，强度走 SW6，泵/压缩机/膜/混合器走厂家曲线或文献。', '截图/导出/版本/同设备同工况要留证据。'), ('6 结构与材料', '说明材质、封头、筒体、接管、法兰、内件、保温/保护层。', '材料和结构选择要回到介质腐蚀性、温度压力、制造标准。'), ('7 选型小结表', '给设备位号、名称、型式/型号、关键尺寸、设计 T/P、材料、数量、证据状态。', '表后要说明哪些已复算、哪些仍为边界。')]
    (OUT / 'equipment_selection_workflow_nodes.md').write_text('# 设备选型说明书格式与证据节点\n\n' + markdown_table(['节点', '正文应写什么', '控制边界'], workflow_rows) + '\n\n## 总原则\n\n' + '- 先讲工况，再讲型式选择，再讲计算/软件/厂家证据，最后落型号。\n' + '- 目录级型号只说明候选合理性；正式工程结论必须有同设备同工况证据。\n' + '- 公式族可以复用，设备数值、厂家型号和软件输出不得跨设备迁移。\n', encoding='utf-8')
    (OUT / 'selection_reasoning_nodes.md').write_text('# 型号与型式反向理由节点\n\n这些节点从现有设备选型报告表格和可靠性边界中抽取。它们用于写“为什么选这个型式/型号”，不直接升级为正式设计证明。\n\n' + markdown_table(['设备族', '型式/型号', '好处', '适用场景', '边界', '来源'], ([r['family'], r['type_or_model'], r['benefits'], r['suitable_for'], r['cautions'], r['source']] for r in reasoning)) + '\n', encoding='utf-8')
    (OUT / 'standard_source_inventory.md').write_text('# 标准与手册文件级索引\n\n证据等级说明：标准文件默认只是文件身份/标题/范围入口；只有精确到同版本、同条文或同表页，并与项目输入同单位匹配，才可升为直接引用。课程设计、毕业设计和手册示例值一律不得迁移为项目默认值。\n\n' + markdown_table(['文件', '设备族', '来源性质', '证据等级', '页数', '文本可读性'], ([row['file'], row['family'], row['source_nature'], row['evidence_class'], row['pages'], f"{row['text_probe']}; {row['header_status']}"] for row in standard_rows)) + '\n', encoding='utf-8')
    (OUT / 'zip_unpack_audit.md').write_text('# Zip 解包审计\n\n' + markdown_table(['zip路径/扫描范围', '成员数', '解包目录', '状态'], (r.values() for r in zip_rows)) + literal(profile, 'write_outputs', 'v002'), encoding='utf-8')
    print(OUT)
    print(f'standard_pdfs={len(standard_rows)}')
    print(f'reasoning_nodes={len(reasoning)}')
    print(f'zip_rows={len(zip_rows)}')


class VerifiedCaseProfile:
    def __init__(self, data, sha256):
        self.data, self.sha256 = data, sha256

def load_case_profile(path, expected_sha256):
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if not expected_sha256 or actual != expected_sha256.lower():
        raise ValueError("Case profile SHA256 missing or mismatched")
    data = json.loads(raw)
    if data.get("schema") != "selection-maintenance-case-profile-v1":
        raise ValueError("Unknown case profile schema")
    if data.get("learning_eligible") is not False or data.get("default_retrieval_eligible") is not False:
        raise ValueError("Maintenance output must remain case-audit-only")
    return VerifiedCaseProfile(data, actual)

def require_profile(profile):
    if not isinstance(profile, VerifiedCaseProfile):
        raise ValueError("Explicit hash-verified case profile required before any output")
    return profile.data

def literal(profile, function, key):
    return require_profile(profile)["literals"][function][key]

def joined(profile, function, key, values):
    parts=[]
    for part in require_profile(profile)["joined_strings"][function][key]:
        if isinstance(part,str): parts.append(part); continue
        value=values[part["field"]]
        conversion=part["conversion"]
        if conversion == 114: value=repr(value)
        elif conversion == 115: value=str(value)
        elif conversion == 97: value=ascii(value)
        parts.append(format(value, part["format"]))
    return "".join(parts)

def main(argv=None):
    global ROOT, WORKSPACE, STANDARDS_ROOT, TABLE_DIR, KG, OUT, UNPACK_DIR
    parser=argparse.ArgumentParser(description="Case-only source-preserved graph rebuild; never shared learning")
    parser.add_argument("--profile",required=True)
    parser.add_argument("--profile-sha256",required=True)
    parser.add_argument("--source-root",required=True)
    parser.add_argument("--standards-root",required=True)
    parser.add_argument("--output-root",required=True)
    args=parser.parse_args(argv)
    profile=load_case_profile(args.profile,args.profile_sha256)
    ROOT=Path(args.source_root).resolve(); WORKSPACE=ROOT.parent
    STANDARDS_ROOT=Path(args.standards_root).resolve()
    TABLE_DIR=ROOT/"data/tables"; KG=Path(args.output_root).resolve(); OUT=KG
    UNPACK_DIR=OUT/"unpacked_standard_zips"
    if not TABLE_DIR.is_dir() or not STANDARDS_ROOT.is_dir():
        raise ValueError("Source tables and standards directories required")
    if OUT == ROOT or OUT.is_relative_to(ROOT) or ROOT.is_relative_to(OUT) or OUT == STANDARDS_ROOT or OUT.is_relative_to(STANDARDS_ROOT) or STANDARDS_ROOT.is_relative_to(OUT):
        raise ValueError("Output must be disjoint from source roots")
    if OUT.exists() and any(OUT.iterdir()): raise ValueError("Output directory must be empty")
    if any(STANDARDS_ROOT.rglob("*.zip")):
        raise ValueError("Original ZIP extraction is retained for source audit, not admitted by this CLI; supply reviewed extracted files")
    write_outputs(profile=profile)
    (OUT/"CASE_SCOPE.json").write_text(json.dumps({"profile_sha256":profile.sha256,"authority_scope":"case_audit_only","learning_eligible":False,"default_retrieval_eligible":False},indent=2),encoding="utf-8")


if __name__ == "__main__":
    main()
