# -*- coding: utf-8 -*-
"""Build a chapter-level knowledge graph from the Aspen Plus V10 user guide.

The generated graph is intentionally chapter-scoped:
- one source extract per PDF outline chapter
- one knowledge node per chapter
- operation-skill routing indexes that point to the chapter nodes

It does not generate page-level extracts, so source text is not duplicated.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "source" / "source_user_manual.pdf"
CHAPTER_EXTRACT_DIR = ROOT / "chapter_extracts"
GRAPH_DIR = ROOT / "knowledge_graph"
NODE_DIR = GRAPH_DIR / "chapter_nodes"
DETAIL_DIR = GRAPH_DIR / "chapter_detail_indexes"
DETAIL_RECORDS_PATH = GRAPH_DIR / "operation_detail_records.json"
MANIFEST_PATH = ROOT / "manifest.json"
GENERATED_MARKER = "<!-- generated: aspen_user_guide_v10 -->"


SLUGS = {
    0: "ch00_preface",
    1: "ch01_user_interface",
    2: "ch02_build_simulation_model",
    3: "ch03_aspen_help",
    4: "ch04_define_flowsheet",
    5: "ch05_global_information",
    6: "ch06_components",
    7: "ch07_property_methods",
    8: "ch08_property_parameters_data",
    9: "ch09_streams",
    10: "ch10_unit_operation_models",
    11: "ch11_run_simulation",
    12: "ch12_results_reports",
    13: "ch13_plots",
    14: "ch14_flowsheet_annotations",
    15: "ch15_file_management",
    16: "ch16_customize_environment",
    17: "ch17_convergence",
    18: "ch18_access_flowsheet_variables",
    19: "ch19_fortran_blocks_inline_fortran",
    20: "ch20_sensitivity_analysis",
    21: "ch21_design_specs_feedback_control",
    22: "ch22_optimization",
    23: "ch23_data_fit",
    24: "ch24_transfer_information",
    25: "ch25_balance_blocks",
    26: "ch26_case_studies",
    27: "ch27_reactions_chemistry",
    28: "ch28_property_sets",
    29: "ch29_property_analysis",
    30: "ch30_property_parameter_estimation",
    31: "ch31_property_data_regression",
    32: "ch32_petroleum_pseudocomponents",
    33: "ch33_relief_calculation",
    34: "ch34_insert",
    35: "ch35_stream_library",
    36: "ch36_stream_summary_format",
    37: "ch37_windows_programs",
    38: "ch38_activex_automation",
}


ROUTES = {
    0: ["manual-source-boundary"],
    1: ["case-io", "block-stream", "run-export"],
    2: ["case-io", "component-property", "block-stream", "equipment-card", "run-export"],
    3: ["manual-lookup"],
    4: ["block-stream"],
    5: ["case-io", "run-export"],
    6: ["component-property"],
    7: ["component-property"],
    8: ["component-property", "optimization-regression"],
    9: ["block-stream", "component-property"],
    10: ["equipment-card", "reaction-card", "block-stream"],
    11: ["run-export"],
    12: ["run-export", "delivery-qa"],
    13: ["run-export", "delivery-qa"],
    14: ["delivery-qa", "block-stream"],
    15: ["case-io", "delivery-qa"],
    16: ["case-io"],
    17: ["run-export", "sensitivity", "design-spec"],
    18: ["calculator", "sensitivity", "design-spec", "optimization-regression"],
    19: ["calculator", "reaction-card", "delivery-qa"],
    20: ["sensitivity"],
    21: ["design-spec"],
    22: ["optimization-regression"],
    23: ["optimization-regression", "component-property"],
    24: ["calculator", "block-stream"],
    25: ["calculator", "block-stream"],
    26: ["sensitivity", "run-export"],
    27: ["reaction-card", "component-property"],
    28: ["component-property", "run-export"],
    29: ["component-property", "run-export"],
    30: ["component-property", "optimization-regression"],
    31: ["optimization-regression", "component-property"],
    32: ["component-property", "equipment-card"],
    33: ["equipment-card", "delivery-qa"],
    34: ["block-stream", "delivery-qa"],
    35: ["case-io", "block-stream"],
    36: ["run-export", "delivery-qa"],
    37: ["case-io", "delivery-qa"],
    38: ["case-io", "block-stream", "equipment-card", "run-export"],
}


TRIGGERS = {
    0: ["manual scope", "volume", "support", "手册范围", "技术支持"],
    1: ["UI", "Data Browser", "Next", "Control Panel", "主窗口", "数据浏览器", "快捷键"],
    2: ["new simulation", "template", "components", "property method", "stream input", "run", "新建模拟", "模板", "物流输入"],
    3: ["help", "context help", "search", "帮助", "上下文帮助", "在线帮助"],
    4: ["flowsheet", "model library", "ports", "stream connect", "流程", "模型库", "物流连接"],
    5: ["setup", "global", "units", "diagnostics", "report options", "全局信息", "单位集", "诊断"],
    6: ["component", "databank", "formula", "CAS", "组分", "数据库", "别名"],
    7: ["property method", "base method", "NRTL", "SRK", "物性方法", "热力学模型"],
    8: ["binary parameter", "databank", "property data", "parameter", "二元参数", "物性参数"],
    9: ["stream", "flash specification", "composition", "物流", "温度", "压力", "组成"],
    10: ["unit operation", "block", "heater", "column", "reactor", "单元操作", "模块", "反应器", "塔"],
    11: ["run", "sequence", "control panel", "运行", "计算顺序", "控制面板"],
    12: ["results", "report", "history", "结果", "报告", "流股表"],
    13: ["plot", "curve", "graph", "操作曲线", "绘图", "曲线图"],
    14: ["annotation", "PFD", "text", "注解", "标注", "流程图"],
    15: ["file", "backup", "archive", "APW", "BKP", "文件", "备份", "归档"],
    16: ["customize", "toolbar", "preferences", "environment", "定制", "工具条", "环境"],
    17: ["convergence", "tear", "sequence", "Broyden", "Wegstein", "收敛", "断裂物流", "迭代"],
    18: ["flowsheet variable", "variable explorer", "access variables", "流程变量", "变量访问"],
    19: ["Fortran", "inline Fortran", "user model", "FORTRAN块", "内嵌FORTRAN"],
    20: ["Sensitivity", "vary", "tabulate", "灵敏度", "变量扫描"],
    21: ["Design Spec", "feedback control", "vary", "设计规定", "反馈控制"],
    22: ["Optimization", "objective", "constraint", "优化", "目标函数", "约束"],
    23: ["data fit", "model fit", "parameter fit", "数据拟合", "模型拟合"],
    24: ["transfer", "information", "calculator", "传递信息", "模块间信息"],
    25: ["balance", "mass balance", "energy balance", "平衡模块", "物料平衡", "能量平衡"],
    26: ["case study", "scenario", "工况研究", "多工况"],
    27: ["reaction", "chemistry", "stoichiometry", "kinetics", "反应", "化学", "动力学"],
    28: ["property set", "stream property", "物性集", "结果变量"],
    29: ["property analysis", "phase envelope", "binary analysis", "物性分析", "相图"],
    30: ["estimate property", "PCES", "group contribution", "估计物性参数"],
    31: ["property regression", "data regression", "物性数据回归"],
    32: ["petroleum", "assay", "pseudocomponent", "石油分析", "虚拟组分"],
    33: ["relief", "safety valve", "泄压", "安全阀"],
    34: ["insert", "object", "OLE", "插入", "对象"],
    35: ["stream library", "物流库"],
    36: ["stream summary", "format", "物流汇总", "格式"],
    37: ["Windows", "Excel", "OLE", "clipboard", "Windows程序", "协同工作"],
    38: ["ActiveX", "automation", "COM", "自动控制服务器", "脚本"],
}


ROUTE_PURPOSES = {
    "case-io": "open, create, save, import, export, archive, and automate case files",
    "component-property": "component IDs, databanks, physical-property methods, property data, and pseudocomponents",
    "block-stream": "flowsheet drawing, block/stream objects, stream connection, and information transfer",
    "reaction-card": "reaction sets, stoichiometry, chemistry, kinetic/card boundaries, and user models",
    "equipment-card": "unit-operation model selection and equipment/block input context",
    "calculator": "flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic",
    "sensitivity": "variable scans, convergence bracketing, and case studies",
    "design-spec": "feedback-control style target/vary operations",
    "optimization-regression": "optimization, model/data fitting, and property-parameter regression",
    "run-export": "run sequence, control panel, results, reports, plots, and stream summaries",
    "delivery-qa": "reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks",
    "manual-lookup": "how to use Aspen help as a source before guessing paths or fields",
    "manual-source-boundary": "manual scope and source hierarchy for this graph",
}


@dataclass
class Chapter:
    number: int
    node_id: str
    title: str
    slug: str
    start_page: int
    end_page: int
    routes: list[str]
    triggers: list[str]
    extract_file: Path
    node_file: Path
    headings: list[str]


OPERATION_VERBS = [
    "单击",
    "点击",
    "选择",
    "输入",
    "指定",
    "打开",
    "关闭",
    "显示",
    "浏览",
    "编辑",
    "运行",
    "存储",
    "保存",
    "删除",
    "清除",
    "重命名",
    "连接",
    "定义",
    "建立",
    "创建",
    "检查",
    "查看",
    "生成",
    "打印",
    "导入",
    "导出",
    "复制",
    "粘贴",
    "拖放",
    "设置",
    "规定",
    "调用",
    "插入",
    "激活",
    "切换",
    "返回",
    "退出",
    "改变",
    "增加",
    "移去",
    "展开",
    "折叠",
    "键入",
    "选定",
    "按",
    "click",
    "select",
    "enter",
    "open",
    "run",
    "save",
    "choose",
    "define",
    "specify",
    "display",
    "view",
    "delete",
    "rename",
    "export",
    "import",
]

UI_TERMS = [
    "menu",
    "button",
    "dialog",
    "form",
    "sheet",
    "page",
    "folder",
    "toolbar",
    "Data Browser",
    "Control Panel",
    "Next",
    "Run",
    "File",
    "Data",
    "Tools",
    "Blocks",
    "Streams",
    "Reactions",
    "Properties",
    "Setup",
    "Results",
    "菜单",
    "按钮",
    "对话框",
    "页面",
    "表页",
    "工具条",
    "文件夹",
    "数据浏览器",
    "控制面板",
    "状态",
    "窗口",
    "字段",
]

RULE_TERMS = [
    "必须",
    "不能",
    "不得",
    "不要",
    "只",
    "至少",
    "要求",
    "缺省",
    "默认",
    "有效",
    "警告",
    "错误",
    "完成",
    "未完成",
    "warning",
    "error",
    "required",
]

FILE_TERMS = ["APW", "BKP", "backup", "archive", "file", "文件", "备份", "归档", "导入", "导出"]
AUTOMATION_TERMS = ["ActiveX", "COM", "Automation", "Fortran", "Excel", "OLE", "自动", "脚本"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def flatten_outline(reader: PdfReader) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []

    def walk(items: Iterable[object]) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            title = getattr(item, "title", str(item)).strip()
            try:
                page = reader.get_destination_page_number(item) + 1
            except Exception:
                continue
            entries.append((page, title))

    walk(reader.outline)
    seen: set[tuple[int, str]] = set()
    unique: list[tuple[int, str]] = []
    for page, title in sorted(entries, key=lambda x: (x[0], x[1])):
        key = (page, title)
        if key not in seen:
            unique.append(key)
            seen.add(key)
    return unique


def chapter_number(title: str, fallback: int) -> int:
    if "前言" in title:
        return 0
    match = re.search(r"第\s*(\d+)\s*章", title)
    if match:
        return int(match.group(1))
    return fallback


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def extract_headings(text: str, title: str, limit: int = 22) -> list[str]:
    skip_fragments = [
        "ASPEN PLUS 10",
        "ASPEN PLUS 用户指南",
        "ASPEN PLUS用户指南",
        title,
    ]
    headings: list[str] = []
    for raw in text.splitlines():
        line = raw.strip(" \t·•-–—")
        if not line:
            continue
        if any(fragment in line for fragment in skip_fragments):
            continue
        if line.startswith(("l ", "Ø", "如果", "当你", "若", "提示", "注 ")):
            continue
        if re.match(r"^[-+]?\d+(\.\d+)?\s*$", line):
            continue
        if len(line) > 34:
            continue
        if len(line) < 3:
            continue
        if line.count(" ") > 5 and not re.search(r"[\u4e00-\u9fff]", line):
            continue
        if line not in headings:
            headings.append(line)
        if len(headings) >= limit:
            break
    return headings


def rel(path: Path, base: Path = ROOT) -> str:
    return path.relative_to(base).as_posix()


def clean_generated_files() -> None:
    for directory in [CHAPTER_EXTRACT_DIR, NODE_DIR, DETAIL_DIR, GRAPH_DIR]:
        if not directory.exists():
            continue
        for path in directory.glob("*.md"):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if text.startswith(GENERATED_MARKER):
                path.unlink()
    if DETAIL_RECORDS_PATH.exists():
        DETAIL_RECORDS_PATH.unlink()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def route_lines(routes: list[str]) -> str:
    return "\n".join(f"- `{route}`: {ROUTE_PURPOSES.get(route, 'operation-skill route')}" for route in routes)


def line_is_noise(line: str, chapter_title: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("--- PDF Page"):
        return True
    if stripped == chapter_title:
        return True
    if re.search(r"ASPEN PLUS\s*10\s*版\s*用户指南", stripped):
        return True
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", stripped):
        return True
    return False


def classify_detail(text: str) -> list[str]:
    lower = text.casefold()
    kinds: list[str] = []
    if re.match(r"^\s*\d+\s*[.．、]?\s+", text):
        kinds.append("numbered-step")
    if any(term.casefold() in lower for term in OPERATION_VERBS):
        kinds.append("operation-action")
    if any(term.casefold() in lower for term in UI_TERMS):
        kinds.append("ui-path-or-field")
    if any(term.casefold() in lower for term in RULE_TERMS):
        kinds.append("rule-or-diagnostic")
    if any(term.casefold() in lower for term in FILE_TERMS):
        kinds.append("file-io")
    if any(term.casefold() in lower for term in AUTOMATION_TERMS):
        kinds.append("automation")
    if re.search(r"\b(Design Spec|Sensitivity|Optimization|Calculator|Vary|Define)\b", text, re.I):
        kinds.append("solve-fit-tool")
    if re.search(r"\b(Run|Results|Report|Plot|Stream Summary)\b|结果|报告|作图|运行", text, re.I):
        kinds.append("run-result-report")
    return list(dict.fromkeys(kinds))


def extract_keywords(text: str, limit: int = 24) -> list[str]:
    english = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,24}", text)
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,10}", text)
    candidates = english + chinese_terms
    stop = {
        "ASPEN",
        "PLUS",
        "PDF",
        "Page",
        "用户指南",
        "可以",
        "一个",
        "这个",
        "如果",
        "或者",
        "有关",
        "使用",
        "进行",
        "出现",
        "选择",
    }
    keywords: list[str] = []
    for item in candidates:
        if item in stop:
            continue
        if item.casefold() in {k.casefold() for k in keywords}:
            continue
        keywords.append(item)
        if len(keywords) >= limit:
            break
    return keywords


def continuation_allowed(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^\s*\d+\s*[.．、]?\s+", stripped):
        return False
    if stripped.startswith(("l ", "Ø")):
        return False
    return len(stripped) <= 180


def build_detail_records(chapters: list[Chapter], page_texts: dict[int, str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    seen: set[str] = set()

    for chapter in chapters:
        chapter_records: list[dict[str, object]] = []
        detail_counter = 1
        for page_no in range(chapter.start_page, chapter.end_page + 1):
            page_text = page_texts.get(page_no, "")
            page_id = f"{chapter.node_id}-P{page_no:03d}"
            page_record = {
                "node_id": page_id,
                "chapter_node_id": chapter.node_id,
                "chapter_title": chapter.title,
                "page": page_no,
                "kind": ["page-source-fallback"],
                "routes": chapter.routes,
                "keywords": extract_keywords(page_text, 36),
                "text": page_text,
                "source_extract": rel(chapter.extract_file),
                "detail_index": f"knowledge_graph/chapter_detail_indexes/{chapter.node_id}_details.md",
            }
            records.append(page_record)

            raw_lines = [line.strip() for line in page_text.splitlines()]
            lines = [line for line in raw_lines if not line_is_noise(line, chapter.title)]
            i = 0
            while i < len(lines):
                line = lines[i]
                kinds = classify_detail(line)
                if not kinds:
                    i += 1
                    continue

                segment_lines = [line]
                if "numbered-step" in kinds or line.endswith((":", "：")) or "若" in line[:4] or "如果" in line[:6]:
                    j = i + 1
                    while j < len(lines) and len(" ".join(segment_lines)) < 720 and continuation_allowed(lines[j]):
                        next_line = lines[j]
                        next_kinds = classify_detail(next_line)
                        if next_kinds and "numbered-step" not in next_kinds and len(" ".join(segment_lines)) > 220:
                            break
                        segment_lines.append(next_line)
                        j += 1
                    i = j
                else:
                    i += 1

                text = re.sub(r"\s+", " ", " ".join(segment_lines)).strip()
                if len(text) < 12:
                    continue
                dedupe_key = f"{chapter.node_id}|{page_no}|{','.join(kinds)}|{normalize_for_dedupe(text)[:260]}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                detail_id = f"{chapter.node_id}-D{detail_counter:03d}"
                detail_counter += 1
                record = {
                    "node_id": detail_id,
                    "chapter_node_id": chapter.node_id,
                    "chapter_title": chapter.title,
                    "page": page_no,
                    "kind": kinds,
                    "routes": chapter.routes,
                    "keywords": extract_keywords(text),
                    "text": text,
                    "source_extract": rel(chapter.extract_file),
                    "detail_index": f"knowledge_graph/chapter_detail_indexes/{chapter.node_id}_details.md",
                }
                records.append(record)
                chapter_records.append(record)

        write_chapter_detail_index(chapter, chapter_records)

    return records


def normalize_for_dedupe(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def write_chapter_detail_index(chapter: Chapter, chapter_records: list[dict[str, object]]) -> None:
    by_page: dict[int, list[dict[str, object]]] = {}
    for record in chapter_records:
        by_page.setdefault(int(record["page"]), []).append(record)

    page_lines = [
        f"- `{chapter.node_id}-P{page_no:03d}`: source fallback page {page_no}, see `../../{rel(chapter.extract_file)}`"
        for page_no in range(chapter.start_page, chapter.end_page + 1)
    ]

    sections: list[str] = []
    for page_no in range(chapter.start_page, chapter.end_page + 1):
        records = by_page.get(page_no, [])
        if not records:
            continue
        sections.append(f"## PDF Page {page_no}")
        for record in records:
            kinds = ", ".join(f"`{kind}`" for kind in record["kind"])
            keywords = ", ".join(f"`{keyword}`" for keyword in record["keywords"][:12])
            text = str(record["text"])
            sections.append(
                f"### {record['node_id']}\n\n"
                f"- Kinds: {kinds}\n"
                f"- Routes: {', '.join(f'`{route}`' for route in record['routes'])}\n"
                f"- Keywords: {keywords}\n"
                f"- Source: `../../{rel(chapter.extract_file)}` page {page_no}\n\n"
                f"{text}\n"
            )

    content = f"""{GENERATED_MARKER}
# {chapter.node_id} Detail Operation Index - {chapter.title}

Source extract: `../../{rel(chapter.extract_file)}`

PDF pages: {chapter.start_page}-{chapter.end_page}

Routes: {", ".join(f"`{route}`" for route in chapter.routes)}

## Search Contract

This file stores detected operation details for the chapter: numbered steps,
menu/button/dialog/form actions, field or status rules, file operations,
automation references, and run/result/report instructions.

Every page also has a page fallback node so full source text remains searchable
through `operation_detail_records.json` even if the automatic detector misses an
operation sentence.

## Page Fallback Nodes

{chr(10).join(page_lines)}

{chr(10).join(sections)}
"""
    write_text(DETAIL_DIR / f"{chapter.node_id}_details.md", content)


def write_chapter_extract(chapter: Chapter, text: str) -> None:
    content = f"""{GENERATED_MARKER}
# {chapter.title}

Source PDF: `source/source_user_manual.pdf`

Node ID: `{chapter.node_id}`

PDF pages: {chapter.start_page}-{chapter.end_page}

Operation routes: {", ".join(f"`{route}`" for route in chapter.routes)}

Authority boundary:
- This extract is source text for Aspen Plus V10 user-guide workflow and UI behavior.
- It may provide Aspen paths, meanings, workflow order, and checklist prompts.
- It must not provide transferable process values, kinetic constants, tower specifications, or equipment defaults for a project unless the active project source independently supplies the same value, unit, and basis.

## Extracted Text

{text}
"""
    write_text(chapter.extract_file, content)


def write_chapter_node(chapter: Chapter, previous_node: str | None, next_node: str | None) -> None:
    headings = "\n".join(f"- {heading}" for heading in chapter.headings) or "- No stable headings extracted; use the source extract directly."
    triggers = ", ".join(f"`{trigger}`" for trigger in chapter.triggers)
    edges = []
    if previous_node:
        edges.append(f"- previous: `{previous_node}`")
    if next_node:
        edges.append(f"- next: `{next_node}`")
    edges.extend(f"- operation-route: `{route}`" for route in chapter.routes)
    content = f"""{GENERATED_MARKER}
# {chapter.node_id} - {chapter.title}

Source extract: `../../{rel(chapter.extract_file)}`

PDF pages: {chapter.start_page}-{chapter.end_page}

Operation routes:
{route_lines(chapter.routes)}

## Use When

Triggers: {triggers}

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `{chapter.title}`.

## Chapter Topics

{headings}

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `{chapter.node_id}` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

{chr(10).join(edges)}
"""
    write_text(chapter.node_file, content)


def write_index(chapters: list[Chapter], source_hash: str, page_count: int) -> None:
    rows = []
    for ch in chapters:
        rows.append(
            "| `{}` | {} | {}-{} | {} | `{}` | `{}` |".format(
                ch.node_id,
                ch.title.replace("|", "\\|"),
                ch.start_page,
                ch.end_page,
                ", ".join(f"`{route}`" for route in ch.routes),
                rel(ch.node_file, GRAPH_DIR),
                "../" + rel(ch.extract_file),
            )
        )
    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Knowledge Graph Index

Source: `../source/source_user_manual.pdf`

Source SHA256: `{source_hash}`

PDF pages: {page_count}

This index is chapter-level. It complements the existing operation-skill manual graph instead of replacing it:

- Use this graph for Aspen Plus V10 user-guide chapters, workflows, UI paths, help/file/report/plot/convergence/analysis/automation topics.
- Use `{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json` for fragile field-level card filling rules.
- Use `../scripts/query_user_guide_knowledge.py <terms>` for quick chapter lookup.

## Chapters

| Node ID | Chapter | PDF Pages | Operation Routes | Node File | Source Extract |
| --- | --- | --- | --- | --- | --- |
{chr(10).join(rows)}
"""
    write_text(GRAPH_DIR / "user_guide_index.md", content)


def write_operation_router(chapters: list[Chapter]) -> None:
    route_to_chapters: dict[str, list[Chapter]] = {}
    for ch in chapters:
        for route in ch.routes:
            route_to_chapters.setdefault(route, []).append(ch)

    sections = []
    for route in sorted(route_to_chapters):
        lines = [
            f"### `{route}`",
            "",
            ROUTE_PURPOSES.get(route, "Operation route."),
            "",
            "| Chapter Node | Chapter | Pages | Use For |",
            "| --- | --- | --- | --- |",
        ]
        for ch in route_to_chapters[route]:
            trigger_hint = ", ".join(ch.triggers[:5])
            lines.append(f"| `{ch.node_id}` | {ch.title} | {ch.start_page}-{ch.end_page} | {trigger_hint} |")
        sections.append("\n".join(lines))

    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Operation Router

Use this router from `aspen-plus-operations` when a mechanical operation needs manual-backed workflow context from the Aspen Plus V10 user guide.

## Routing Rule

1. Identify the operation node from `aspen-plus-operations/references/operation_graph.md`.
2. Open the matching V10 chapter node below for workflow/UI/report/help context.
3. For high-risk card fields, still query `aspen-plus-operations/references/manual_knowledge_graph.json`.
4. Record both evidence families in the operation report, for example `UG10-CH17` plus `design_spec.define_vary`.

## Duplicate Boundary

- This graph does not duplicate the V14 help graph. It is chapter-level and source-extract backed.
- The V14 help graph remains the structured card-field authority.
- The Sun Lanyi graph remains the textbook/lecture pattern authority.
- Project source ledgers and change-offset tables outrank all manual-derived patterns for project values.

## Operation Routes

{chr(10).join(sections)}
"""
    write_text(GRAPH_DIR / "user_guide_operation_router.md", content)


def write_operation_detail_index(detail_records: list[dict[str, object]]) -> None:
    operation_records = [record for record in detail_records if "page-source-fallback" not in record["kind"]]
    page_records = [record for record in detail_records if "page-source-fallback" in record["kind"]]

    route_map: dict[str, list[dict[str, object]]] = {}
    kind_map: dict[str, int] = {}
    for record in operation_records:
        for route in record["routes"]:
            route_map.setdefault(str(route), []).append(record)
        for kind in record["kind"]:
            kind_map[str(kind)] = kind_map.get(str(kind), 0) + 1

    kind_lines = [f"- `{kind}`: {count}" for kind, count in sorted(kind_map.items())]
    sections: list[str] = []
    for route in sorted(route_map):
        records = route_map[route]
        sections.append(f"## `{route}`")
        sections.append("")
        sections.append(ROUTE_PURPOSES.get(route, "Operation route."))
        sections.append("")
        sections.append("| Detail ID | Chapter | Page | Kinds | Text Preview |")
        sections.append("| --- | --- | --- | --- | --- |")
        for record in records:
            text = str(record["text"]).replace("|", "\\|")
            if len(text) > 140:
                text = text[:137] + "..."
            kinds = ", ".join(f"`{kind}`" for kind in record["kind"])
            sections.append(
                f"| `{record['node_id']}` | `{record['chapter_node_id']}` {record['chapter_title']} | "
                f"{record['page']} | {kinds} | {text} |"
            )
        sections.append("")

    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Detail Operation Index

This is the detailed operation layer under the chapter graph.

Records:

- Detected operation details: {len(operation_records)}
- Page-source fallback records: {len(page_records)}
- Total searchable records: {len(detail_records)}

Machine-readable index:

`operation_detail_records.json`

Query:

```text
python ../scripts/query_user_guide_knowledge.py <terms>
python ../scripts/query_user_guide_knowledge.py <terms> --scope details
python ../scripts/query_user_guide_knowledge.py <terms> --json
```

## Detail Kinds

{chr(10).join(kind_lines)}

## Route Index

{chr(10).join(sections)}
"""
    write_text(GRAPH_DIR / "operation_detail_index.md", content)


def write_skill_bridge(chapters: list[Chapter]) -> None:
    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Skill Bridge

This file connects the project-local Aspen Plus V10 user-guide graph to the `aspen-plus-operations` skill.

## Entry Points

- Index: `user_guide_index.md`
- Operation router: `user_guide_operation_router.md`
- Detail operation index: `operation_detail_index.md`
- Unknown router: `unknowns_router.md`
- Query script: `../scripts/query_user_guide_knowledge.py`
- Structured manifest: `../manifest.json`
- Search records: `operation_detail_records.json`

## Operation-Skill Use

Before a mechanical Aspen operation, keep value authority and card-mechanics authority separate:

- Project report, taskbook, change-offset table, and source-freeze ledgers decide project values.
- `aspen-plus-operations/references/manual_knowledge_graph.json` decides fragile card-field meanings where seeded.
- This V10 user-guide graph supplies chapter-level workflow, UI path, file/report/help/convergence/analysis/automation context.

Recommended note format:

```text
User-guide node(s): UG10-CHxx and/or UG10-CHxx-Dnnn
Operation graph node(s): case-io / block-stream / ...
Card manual node(s): reaction.powerlaw.overview / ...
Source value authority: <project ledger or blocked>
```

## Query Examples

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py convergence tear
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py ActiveX COM --ids
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py 物性 方法
```

## Non-Duplication Rule

Do not copy nodes from this graph into the operation skill's `manual_knowledge_graph.json` unless a recurring field-level card rule has been independently verified against current Aspen help/exported cards. For ordinary chapter and detailed-operation routing, link to `UG10-CHxx` or `UG10-CHxx-Dnnn` instead.

## Current Coverage

Chapter nodes generated: {len(chapters)}
"""
    write_text(GRAPH_DIR / "user_guide_skill_bridge.md", content)


def write_unknowns_router(chapters: list[Chapter]) -> None:
    rows = []
    families = [
        ("Cannot find a menu/path/help topic", ["manual-lookup", "case-io"], "Open `UG10-CH03`, then query by UI term."),
        ("Creating or opening a model", ["case-io"], "Start with `UG10-CH02`, `UG10-CH15`, and operation graph `case-io`."),
        ("Component/property setup", ["component-property"], "Start with `UG10-CH06`-`UG10-CH08`; then use card graph for field rules."),
        ("Flowsheet drawing or connection", ["block-stream"], "Start with `UG10-CH04` and `UG10-CH09`."),
        ("Unit-operation model choice", ["equipment-card"], "Start with `UG10-CH10`; for reactors also open `UG10-CH27`."),
        ("Run failed or results look stale", ["run-export"], "Start with `UG10-CH11`, `UG10-CH12`, and `UG10-CH17`."),
        ("Need variable automation", ["calculator", "design-spec", "sensitivity", "optimization-regression"], "Open `UG10-CH18`-`UG10-CH22`."),
        ("Need Fortran or automation", ["calculator", "case-io"], "Open `UG10-CH19` and `UG10-CH38`; keep USER delivery gates active."),
        ("Report/plot/PFD/delivery output", ["delivery-qa"], "Open `UG10-CH12`-`UG10-CH15`, `UG10-CH36`, and `UG10-CH37`."),
    ]
    by_route: dict[str, list[str]] = {}
    for ch in chapters:
        for route in ch.routes:
            by_route.setdefault(route, []).append(ch.node_id)
    for family, routes, action in families:
        node_ids = []
        for route in routes:
            node_ids.extend(by_route.get(route, []))
        deduped = []
        for node_id in node_ids:
            if node_id not in deduped:
                deduped.append(node_id)
        rows.append(f"| {family} | {', '.join(f'`{n}`' for n in deduped[:8])} | {action} |")
    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Unknowns Router

Use this when the operation family is unclear.

| Unknown Family | First Nodes | Next Action |
| --- | --- | --- |
{chr(10).join(rows)}

If no row matches, run:

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms>
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --scope details
```
"""
    write_text(GRAPH_DIR / "unknowns_router.md", content)


def write_readme(chapters: list[Chapter], source_hash: str, page_count: int, detail_count: int = 0) -> None:
    content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Knowledge Graph

This graph is built from the local PDF source:

`source/source_user_manual.pdf`

Source SHA256: `{source_hash}`

PDF pages: {page_count}

## Purpose

The graph splits the Aspen Plus 10 user guide by PDF outline chapter and connects each chapter to the `aspen-plus-operations` operation graph.

It is a chapter-level operation/navigation graph. It does not replace:

- the project source/change-offset ledgers that decide project values;
- the operation skill's V14 help-backed `manual_knowledge_graph.json` for fragile card field rules;
- the Sun Lanyi textbook graph for lecture/case patterns.

## V14 Operation Preservation Guard

Do not overwrite, regenerate, or merge into the Aspen Plus V14 operation manual
graph:

`{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json`

This V10 graph may only be used as workflow/UI/detail-operation retrieval
support. V14 card-field rules remain authoritative for low-level Aspen card
mechanics.

## Entry Order

1. `knowledge_graph/00_ERROR_MEMORY.md`
2. `knowledge_graph/unknowns_router.md`
3. `knowledge_graph/user_guide_operation_router.md`
4. `knowledge_graph/user_guide_index.md`
5. `knowledge_graph/operation_detail_index.md`
6. `knowledge_graph/chapter_detail_indexes/UG10-CHxx_details.md`
7. `knowledge_graph/chapter_nodes/UG10-CHxx_*.md`
8. `chapter_extracts/chxx_*.md` only when source text is needed

Read `knowledge_graph/NEW_KNOWLEDGE.md` only for recent candidate or validated
items that have not yet been promoted by this builder.

## Query

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms>
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --ids
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --json
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --scope details
```

## Vector Search

Local graph-only vector index:

```text
python aspen_user_guide_v10_knowledge/scripts/vectorize_user_guide_graph.py
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_vectors.py <terms>
```

Workspace-wide graph and skill-chain vector index:

```text
python scripts/vectorize_workspace_knowledge.py
python scripts/query_workspace_vectors.py <terms>
```

## Non-Duplication Choices

- No page-level text extracts are generated.
- Each PDF outline entry becomes exactly one source extract and one graph node.
- Detail operation indexes are generated as searchable pointers and short operation records.
- Existing operation-skill manual graph files are linked, not copied.
- Rebuilds overwrite only files marked with the generated marker.

## Coverage

Generated chapter nodes: {len(chapters)}

Searchable detail records: {detail_count}
"""
    write_text(ROOT / "README.md", content)
    graph_content = f"""{GENERATED_MARKER}
# Aspen Plus V10 User Guide Knowledge Graph

Source PDF: `../source/source_user_manual.pdf`

Source SHA256: `{source_hash}`

PDF pages: {page_count}

This is the graph-directory entry point for the chapter-level Aspen Plus V10 user-guide graph.

## Entry Order

1. `00_ERROR_MEMORY.md`
2. `unknowns_router.md`
3. `user_guide_operation_router.md`
4. `operation_detail_index.md`
5. `chapter_detail_indexes/UG10-CHxx_details.md`
6. `user_guide_index.md`
7. `chapter_nodes/UG10-CHxx_*.md`
8. `../chapter_extracts/chxx_*.md` only when source text is needed

Read `NEW_KNOWLEDGE.md` only for recent candidate or validated additions that
have not yet been promoted by the graph builder.

## Operation Skill Bridge

Open `user_guide_skill_bridge.md` when connecting this graph to `aspen-plus-operations`.

Use this graph for workflow, UI path, file/report/help/convergence/analysis/automation chapter context. Continue using `{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json` for field-level Aspen card rules.

Do not overwrite or merge into the V14 operation manual graph. Cite V10
`UG10-*` IDs beside V14 node IDs when useful; do not replace V14 card-rule
nodes with V10 user-guide nodes.

For vector search, use `../vector_index/README.md` for this graph only, or
`../../knowledge_vector_index/README.md` for the whole workspace graph and
skill chain.

## Non-Duplication Choices

- No page-level text extracts are generated.
- Each PDF outline entry becomes exactly one source extract and one graph node.
- Detail operation records are searchable through `operation_detail_records.json`.
- Existing operation-skill manual graph files are linked, not copied.
- Rebuilds overwrite only files marked with the generated marker.

Generated chapter nodes: {len(chapters)}

Searchable detail records: {detail_count}
"""
    write_text(GRAPH_DIR / "README.md", graph_content)


def write_manifest(
    chapters: list[Chapter],
    source_hash: str,
    page_count: int,
    metadata: dict[str, str],
    detail_count: int,
) -> None:
    data = {
        "name": "aspen_user_guide_v10_knowledge",
        "source_pdf": "source/source_user_manual.pdf",
        "source_sha256": source_hash,
        "page_count": page_count,
        "metadata": metadata,
        "generated_marker": GENERATED_MARKER,
        "entrypoints": {
            "readme": "README.md",
            "index": "knowledge_graph/user_guide_index.md",
            "operation_router": "knowledge_graph/user_guide_operation_router.md",
            "detail_index": "knowledge_graph/operation_detail_index.md",
            "detail_records": "knowledge_graph/operation_detail_records.json",
            "skill_bridge": "knowledge_graph/user_guide_skill_bridge.md",
            "unknowns_router": "knowledge_graph/unknowns_router.md",
            "query_script": "scripts/query_user_guide_knowledge.py",
        },
        "detail_record_count": detail_count,
        "chapters": [
            {
                "node_id": ch.node_id,
                "number": ch.number,
                "title": ch.title,
                "slug": ch.slug,
                "start_page": ch.start_page,
                "end_page": ch.end_page,
                "routes": ch.routes,
                "triggers": ch.triggers,
                "headings": ch.headings,
                "extract_file": rel(ch.extract_file),
                "node_file": rel(ch.node_file),
            }
            for ch in chapters
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if not PDF_PATH.exists():
        print(f"Missing source PDF: {PDF_PATH}", file=sys.stderr)
        return 2

    reader = PdfReader(str(PDF_PATH))
    outline = flatten_outline(reader)
    if not outline:
        print("PDF has no outline; chapter splitting would be unsafe.", file=sys.stderr)
        return 3

    source_hash = sha256(PDF_PATH)
    page_count = len(reader.pages)
    clean_generated_files()

    chapters: list[Chapter] = []
    page_texts: dict[int, str] = {}
    for idx, (start_page, title) in enumerate(outline):
        end_page = (outline[idx + 1][0] - 1) if idx + 1 < len(outline) else page_count
        number = chapter_number(title, idx)
        slug = SLUGS.get(number, f"ch{number:02d}")
        node_id = "UG10-CH00" if number == 0 else f"UG10-CH{number:02d}"
        chapter_page_texts = []
        for page_no in range(start_page, end_page + 1):
            if page_no not in page_texts:
                page_texts[page_no] = clean_text(reader.pages[page_no - 1].extract_text() or "")
            chapter_page_texts.append(f"--- PDF Page {page_no} ---\n{page_texts[page_no]}")
        chapter_text = "\n\n".join(chapter_page_texts).strip()
        headings = extract_headings(chapter_text, title)
        extract_file = CHAPTER_EXTRACT_DIR / f"{slug}.md"
        node_file = NODE_DIR / f"{node_id}_{slug}.md"
        chapter = Chapter(
            number=number,
            node_id=node_id,
            title=title,
            slug=slug,
            start_page=start_page,
            end_page=end_page,
            routes=ROUTES.get(number, ["manual-lookup"]),
            triggers=TRIGGERS.get(number, [title]),
            extract_file=extract_file,
            node_file=node_file,
            headings=headings,
        )
        write_chapter_extract(chapter, chapter_text)
        chapters.append(chapter)

    node_ids = [ch.node_id for ch in chapters]
    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError("Duplicate node IDs generated")

    for idx, chapter in enumerate(chapters):
        previous_node = chapters[idx - 1].node_id if idx else None
        next_node = chapters[idx + 1].node_id if idx + 1 < len(chapters) else None
        write_chapter_node(chapter, previous_node, next_node)

    detail_records = build_detail_records(chapters, page_texts)
    write_operation_detail_index(detail_records)
    DETAIL_RECORDS_PATH.write_text(
        json.dumps(detail_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
    write_index(chapters, source_hash, page_count)
    write_operation_router(chapters)
    write_skill_bridge(chapters)
    write_unknowns_router(chapters)
    write_readme(chapters, source_hash, page_count, len(detail_records))
    write_manifest(chapters, source_hash, page_count, metadata, len(detail_records))

    print(f"Built {len(chapters)} chapter nodes from {page_count} pages.")
    print(f"Built {len(detail_records)} searchable detail records.")
    print(f"Source SHA256: {source_hash}")
    print(f"Graph root: {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
