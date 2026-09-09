from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


TYPE_INFO = {
    "RADFRAC": (
        "塔设备",
        "精馏塔/回收塔（RadFrac严格塔，一览表级；塔内件后续水力学校核）",
        "塔径、级数、压力、回流比、热负荷、塔内件需后续Column Internals/厂家或报告补证",
    ),
    "HEATER": (
        "换热设备",
        "加热器/冷却器/冷凝器（Heater简化换热单元，工程上按管壳式换热器或公用工程换热器候选）",
        "用于一览表列换热设备；面积、U、压降需EDR或详细换热计算补证",
    ),
    "HEATX": (
        "换热设备",
        "两股物流换热器（HeatX，优先按管壳式/BEM类候选）",
        "已有冷热物流连接；面积、U、压降和结构需EDR补证",
    ),
    "PUMP": (
        "泵",
        "工艺离心泵/流程泵候选（按流量、扬程、介质再细化）",
        "一览表级列泵；NPSH、效率和厂家曲线后续补证",
    ),
    "COMPR": (
        "压缩机",
        "工艺气压缩机（按流量、压比、气体性质在离心/螺杆/液环间细化）",
        "一览表级列压缩机；MW、k、Z、效率和厂家曲线后续补证",
    ),
    "RPLUG": (
        "反应器",
        "管式/列管式固定床反应器候选（RPlug）",
        "适合连续催化/管式反应；动力学、床层压降、传热和强度需专项补证",
    ),
    "RSTOIC": (
        "反应器",
        "转化反应器/化学计量反应器占位（RStoic）",
        "流程反应功能已明确；正式设备型式需按反应相态、热效应和停留时间另行定型",
    ),
    "FLASH2": (
        "分离器",
        "闪蒸罐/气液分离器（非储罐）",
        "用于相分离/冷凝后气液分离；K值、液滴粒径、停留时间和SW6后续补证",
    ),
    "SEP2": (
        "选择性分离单元",
        "组分分离器/选择性分离单元（膜、吸附或简化分离占位）",
        "Aspen SEP2为分离功能占位；正式膜/吸附/分离设备需另行补选",
    ),
    "VALVE": (
        "阀门",
        "节流阀/减压阀",
        "按压降、相态和材质列入管道阀件；不作为储罐",
    ),
    "MIXER": (
        "混合器",
        "管道混合器/静态混合器或混合节点",
        "一览表级列混合设备；压降、混合均匀度和厂家型号后续补证",
    ),
    "FSPLIT": (
        "分流器",
        "分流器/分配阀组",
        "用于物流分配和回流/排放比例控制；阀组与控制方式后续细化",
    ),
}


REASON_SPECS = [
    (
        "RADFRAC",
        "塔设备",
        "精馏塔/回收塔",
        "RadFrac用于严格汽液平衡分离，说明流程中存在明确的塔分离任务。设备一览表可先列为精馏塔/回收塔；塔板或填料型式后续按塔径、压降、真空程度和液泛率确定。",
        "级数、进料板、塔顶/塔底压力、回流比、冷凝/再沸负荷、气液负荷。",
        "塔径、液泛、压降和塔内件需Column Internals或厂家资料。",
    ),
    (
        "HEATER",
        "换热设备",
        "加热器/冷却器/冷凝器",
        "Heater模块承担升温、冷却、冷凝、相态调整等换热任务。一览表级可按换热设备列入，具体按冷热源和热负荷细化为加热器、冷却器或冷凝器。",
        "入口/出口温度压力、热负荷、相态、公用工程、允许压降。",
        "面积、U值、压降和结构需EDR或详细换热计算。",
    ),
    (
        "HEATX",
        "换热设备",
        "两股物流管壳式换热器/BEM候选",
        "HeatX已有冷热两股物流，适合列为过程物流换热器；管壳式/BEM类便于承压、制造和后续EDR/SW6接力。",
        "冷热侧T/P/流量/相态、热负荷、LMTD、允许压降。",
        "最终面积、U、Re、压降、管束/管板需EDR/SW6。",
    ),
    (
        "PUMP",
        "泵",
        "工艺离心泵/流程泵候选",
        "BKP中的Pump承担液体升压输送，设备一览表先按工艺泵列入；离心泵作为常规清洁或中等流量液体的首选候选。",
        "流量、入口/出口压力、密度、黏度、蒸气压、扬程。",
        "NPSH、效率、BEP和厂家曲线后续补证。",
    ),
    (
        "COMPR",
        "压缩机",
        "工艺气压缩机",
        "Compr模块承担气体升压或热泵压缩功能。选型先按气量和压比确定离心、螺杆、液环或多级压缩方案。",
        "入口/出口T/P、体积流量、MW、k、Z、压比、效率、是否含湿。",
        "功率、出口温度、级间冷却和厂家曲线后续补证。",
    ),
    (
        "RPLUG",
        "反应器",
        "管式/列管固定床反应器",
        "RPlug表示沿程反应模型，适合连续管式或固定床反应器的一览表表达，尤其适合需要床层、压降和传热描述的反应段。",
        "反应相态、动力学、催化剂量、管径/管长、热负荷、压降。",
        "动力学冻结链、床层压降、传热、管板和强度需专项补证。",
    ),
    (
        "RSTOIC",
        "反应器",
        "转化反应器/化学计量反应器",
        "RStoic在流程层面给出反应转化关系；一览表可先列为反应器，但不能仅凭RStoic确定最终设备结构。",
        "反应式、转化率/收率、T/P、相态、停留时间、反应热。",
        "正式反应器型式、体积、换热和动力学需另行定型。",
    ),
    (
        "FLASH2",
        "分离器",
        "闪蒸罐/气液分离器",
        "Flash2用于两相闪蒸或冷凝后气液分离；可列为气液分离器/闪蒸分离器，不按储罐处理。",
        "进料相分率、气液流量、密度、温压、液滴粒径/夹带要求。",
        "K值、停留时间、除沫器和SW6后续补证。",
    ),
    (
        "SEP2",
        "选择性分离单元",
        "膜/吸附/组分分离占位",
        "Sep2代表按组分分离的功能块，可用于CO2回收、干燥或选择性分离的一览表占位。",
        "目标组分、回收率、压差、通量/吸附容量或分离效率。",
        "必须后续明确膜、吸附、洗涤或其他物理设备。",
    ),
    (
        "VALVE",
        "阀门",
        "节流阀/减压阀",
        "Valve承担减压、节流或压力匹配任务，是管道系统关键设备；按阀门列入，不作为储罐。",
        "入口/出口压力、相态、流量、允许压降、材质。",
        "阀型、Cv、闪蒸/空化和材质后续补证。",
    ),
    (
        "MIXER",
        "混合器",
        "管道混合器/静态混合器",
        "Mixer用于多股物流混合，工程上可按管道混合器或混合节点列入，复杂混合再选静态混合器。",
        "各入口流量、密度、黏度、相态、允许压降、混合均匀度。",
        "压降、混合元件数和厂家型号后续补证。",
    ),
    (
        "FSPLIT",
        "分流器",
        "分流阀组/分配器",
        "FSplit用于物流分配、回流和排放比例控制，工程上可列为分流器或调节阀组。",
        "分流比、流量、T/P、控制目标。",
        "控制阀组、调节范围和控制方式后续细化。",
    ),
]


def section_of(block_id: str, section_names: dict[str, str] | None = None) -> str:
    # Labels are explicit project input, not a transferable flowsheet authority.
    match = re.search(r"(\d{2})\d{3}", block_id)
    if not match:
        return "跨段/辅助"
    sec = match.group(1)
    names = section_names or {}
    return names.get(sec, f"{sec}段")


def parse_stream_list(tail: str, name: str) -> list[str]:
    match = re.search(r"\b" + name + r"\s*=\s*\((.*?)\)", tail)
    if not match:
        return []
    tokens = match.group(1).split()
    return [t for t in tokens if not re.match(r"^[A-Z]?\d+-\d+$", t)]


def evidence_level(block_type: str) -> str:
    if block_type in {"RADFRAC", "HEATX", "RPLUG"}:
        return "一览表级；后续需软件/专项校核"
    return "一览表级；后续按厂家/软件/设计条件补证"


def md_table(headers: list[str], data: list[dict[str, object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in data:
        vals = [str(row.get(h, "")).replace("\n", " ").replace("|", "/") for h in headers]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build source-only equipment overview tables.")
    parser.add_argument("bkp", type=Path)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--section-names", type=Path,
                        help="Optional UTF-8 JSON object mapping two-digit section IDs to project labels; no labels are inferred.")
    args = parser.parse_args()
    section_names: dict[str, str] = {}
    if args.section_names is not None:
        try:
            section_names = json.loads(args.section_names.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            parser.error(f"Cannot read section names: {exc}")
        if not isinstance(section_names, dict) or any(
            not isinstance(key, str) or re.fullmatch(r"\d{2}", key) is None
            or not isinstance(value, str) or not value.strip()
            for key, value in section_names.items()
        ):
            parser.error("section names must be a JSON object of two-digit IDs and nonempty string labels")
    bkp = args.bkp
    outdir = args.outdir
    text = bkp.read_text(encoding="latin-1")
    start = text.find("FLOWSHEET GLOBAL")
    end = text.find('"DEF-STREAM"', start)
    if start < 0 or end < 0:
        raise SystemExit("Cannot find FLOWSHEET GLOBAL / DEF-STREAM boundary")

    flow = " ".join(text[start:end].replace("\r", " ").replace("\n", " ").split())
    pattern = re.compile(
        r"BLOCK\s+BLKID\s*=\s*([A-Za-z0-9_]+)\s+"
        r"BLKTYPE\s*=\s*\"?([A-Z0-9]+)\"?\s+"
        r"MDLTYPE\s*=\s*\"?([A-Za-z0-9]+)\"?(.*?)"
        r"(?=\\\s+\\\s+BLOCK\s+BLKID\s*=|\\\s+\"DEF-STREAM\"|$)",
        re.S,
    )

    rows: list[dict[str, object]] = []
    for i, match in enumerate(pattern.finditer(flow), start=1):
        block_id, block_type, model_type, tail = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )
        family, selection, boundary = TYPE_INFO.get(
            block_type, ("其他单元", f"{model_type}单元", "需人工复核")
        )
        rows.append(
            {
                "序号": i,
                "工段": section_of(block_id, section_names),
                "位号": block_id,
                "Aspen模型": block_type,
                "设备族": family,
                "一览表拟列设备型式": selection,
                "入口流股": ", ".join(parse_stream_list(tail, "IN")),
                "出口流股": ", ".join(parse_stream_list(tail, "OUT")),
                "当前选型精度/边界": evidence_level(block_type),
                "备注": boundary,
            }
        )

    by_type: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_type[str(row["Aspen模型"])].append(str(row["位号"]))

    reason_rows: list[dict[str, object]] = []
    for block_type, family, selection, reason, params, boundary in REASON_SPECS:
        block_ids = by_type.get(block_type, [])
        if not block_ids:
            continue
        reason_rows.append(
            {
                "设备族": family,
                "覆盖Aspen模型": block_type,
                "覆盖位号": ", ".join(block_ids),
                "一览表拟选型式": selection,
                "选择理由": reason,
                "一览表级需要参数/筛选项": params,
                "后续边界": boundary,
            }
        )

    counts = Counter(str(row["Aspen模型"]) for row in rows)
    summary_rows = [
        {"Aspen模型": key, "数量": value, "设备族": TYPE_INFO.get(key, ("其他", "", ""))[0]}
        for key, value in sorted(counts.items())
    ]

    # The date suffix is a legacy interface filename, never this run's timestamp.
    csv_overview = outdir / "全流程模拟_设备选型一览表_不含储罐_20260622.csv"
    csv_reason = outdir / "全流程模拟_设备选择理由表_不含储罐_20260622.csv"
    md_path = outdir / "全流程模拟_设备选型一览表与选择理由_不含储罐_20260622.md"

    write_csv(csv_overview, rows)
    write_csv(csv_reason, reason_rows)
    md_path.write_text(
        "# 全流程模拟设备选型一览表与选择理由（不含储罐）\n\n"
        f"- 来源BKP：`{bkp}`\n"
        "- 文件名兼容：`20260622` 仅为历史接口文件名后缀，不代表本次运行日期。\n"
        f"- 抽取方式：静态解析 `FLOWSHEET GLOBAL` 中的 {len(rows)} 个 Aspen block 及其进出口流股；未打开或修改 Aspen 文件。\n"
        "- 精度口径：设备选型一览表级别，够列位号、设备族、拟列型式、入口/出口流股和后续边界；不替代 EDR、SW6、Column Internals 或厂家最终选型书。\n"
        "- 储罐处理：本表不选择原料罐、产品罐、缓冲罐、回流罐等储罐类设备；后续需按库存时间、装填系数、密度、蒸气压和安全附件另行添加。设备按当前解析模型识别，不依位号前缀认作储罐。\n\n"
        "## 1. Aspen Block 统计\n\n"
        + md_table(["Aspen模型", "数量", "设备族"], summary_rows)
        + "\n\n## 2. 设备选型一览表\n\n"
        + md_table(
            [
                "序号",
                "工段",
                "位号",
                "Aspen模型",
                "设备族",
                "一览表拟列设备型式",
                "入口流股",
                "出口流股",
                "当前选型精度/边界",
                "备注",
            ],
            rows,
        )
        + "\n\n## 3. 选择理由表\n\n"
        + md_table(
            [
                "设备族",
                "覆盖Aspen模型",
                "覆盖位号",
                "一览表拟选型式",
                "选择理由",
                "一览表级需要参数/筛选项",
                "后续边界",
            ],
            reason_rows,
        )
        + "\n",
        encoding="utf-8",
    )

    print(md_path)
    print(csv_overview)
    print(csv_reason)
    print(f"rows={len(rows)} reason_rows={len(reason_rows)} counts={dict(counts)}")


if __name__ == "__main__":
    main()
