from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COMPONENT_CN = {
    "TBC": "阻聚剂",
    "DME": "二甲醚",
    "CO": "一氧化碳",
    "MA": "乙酸甲酯",
    "H2": "氢气",
    "CO2": "二氧化碳",
    "H2O": "水",
    "MEOH": "甲醇",
    "ETOH": "乙醇",
    "CH4": "甲烷",
    "N2": "氮气",
    "EB": "乙苯",
    "STYRENE": "苯乙烯",
    "BZ": "苯",
    "TOL": "甲苯",
    "PXYL": "对二甲苯",
    "MXYL": "间二甲苯",
    "OXYL": "邻二甲苯",
    "NHEX": "正己烷",
    "TMB": "三甲苯",
    "ET": "乙烯",
    "ETHANE": "乙烷",
    "PR": "丙烯",
    "PROH": "丙醇",
    "BU1": "丁烯",
    "PDEB": "二乙苯",
    "NBUT": "正丁醇",
}

STANDARD_AREAS = [2.1, 5.4, 11.5, 15.2, 17.1, 19.7, 25.2, 26.0, 35.4, 50.0, 72.2, 90.2, 120.0, 146.5, 198.0, 260.0, 350.0]

PIPE_SIZES = [
    (15, 21.3, 2.77, 3.73),
    (20, 26.9, 2.87, 3.91),
    (25, 33.7, 3.38, 4.55),
    (32, 42.4, 3.56, 4.85),
    (40, 48.3, 3.68, 5.08),
    (50, 60.3, 3.91, 5.54),
    (65, 76.1, 5.16, 7.01),
    (80, 88.9, 5.49, 7.62),
    (100, 114.3, 6.02, 8.56),
    (125, 139.7, 6.55, 9.53),
    (150, 168.3, 7.11, 10.97),
    (200, 219.1, 8.18, 12.70),
    (250, 273.0, 9.27, 15.09),
    (300, 323.9, 10.31, 17.48),
    (350, 355.6, 11.13, 19.05),
    (400, 406.4, 12.70, 21.44),
    (450, 457.0, 14.27, 23.83),
    (500, 508.0, 15.09, 26.19),
    (600, 610.0, 17.48, 30.96),
    (700, 711.0, 17.48, 30.96),
    (800, 813.0, 17.48, 30.96),
    (900, 914.0, 19.05, 34.93),
    (1000, 1016.0, 19.05, 38.10),
    (1200, 1219.0, 22.23, 46.02),
]


@dataclass
class Block:
    tag: str
    btype: str
    mdltype: str
    ins: list[str]
    outs: list[str]


def stamp() -> str:
    return time.strftime("%Y%m%d")


def clean_token(token: str) -> str:
    return token.strip().strip('"').strip("'").upper()


def parse_stream_refs(raw: str) -> list[str]:
    tokens = [clean_token(t) for t in re.split(r"\s+", raw.replace("\\", " "))]
    streams: list[str] = []
    for token in tokens:
        if not token or token.startswith("M") and re.fullmatch(r"M\d+(?:-\d+)?", token):
            continue
        if token in {"IN", "OUT", "=", "(", ")"}:
            continue
        if re.fullmatch(r"[A-Z0-9_][A-Z0-9_+-]*", token):
            streams.append(token)
    return streams


def parse_bkp(path: Path) -> tuple[list[str], list[Block]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    flat = re.sub(r"\s+", " ", text)

    comps: list[str] = []
    comp_match = re.search(r"COMPONENTS\s+(.*?)\s+HENRY-COMPS", flat, re.I)
    if comp_match:
        chunk = comp_match.group(1)
        for m in re.finditer(r"\b([A-Z0-9_-]+)\s+[A-Z0-9().+-]+(?:\s*/|$)", chunk):
            comp = clean_token(m.group(1))
            if comp and comp not in comps:
                comps.append(comp)
    if len(comps) < 5:
        for m in re.finditer(r"\bCID\s*=\s*([A-Z0-9_-]+)\s+ANAME\b", text, re.I):
            comp = clean_token(m.group(1))
            if comp and comp not in comps:
                comps.append(comp)
    if len(comps) < 5:
        comps = list(COMPONENT_CN)

    blocks: list[Block] = []
    pat = re.compile(
        r"BLOCK\s+BLKID\s*=\s*([A-Z0-9_]+)\s+BLKTYPE\s*=\s*\"([A-Z0-9_]+)\"\s+"
        r"MDLTYPE\s*=\s*\"([A-Za-z0-9_]+)\"\s+IN\s*=\s*\((.*?)\)\s+OUT\s*=\s*\((.*?)\)",
        re.I,
    )
    for m in pat.finditer(flat):
        blocks.append(
            Block(
                tag=clean_token(m.group(1)),
                btype=clean_token(m.group(2)),
                mdltype=m.group(3),
                ins=parse_stream_refs(m.group(4)),
                outs=parse_stream_refs(m.group(5)),
            )
        )
    return comps, blocks


def parse_his_heatx_results(his_path: Path) -> dict[str, dict[str, float]]:
    if not his_path.exists():
        return {}
    rows: dict[str, dict[str, float]] = {}
    current: str | None = None
    ttl = 0
    pattern = re.compile(r"(?:GENERATING RESULTS FOR\s+)?UOS BLOCK\s+([A-Z0-9_]+)\s+MODEL:\s+HEATX", re.I)
    with his_path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            m = pattern.search(line)
            if m:
                current = clean_token(m.group(1))
                ttl = 10
                rows.setdefault(current, {})
                continue
            if current and ttl > 0:
                ttl -= 1
                am = re.search(r"AREA=\s*([0-9.Ee+-]+)", line)
                dm = re.search(r"DUTY=\s*([0-9.Ee+-]+)", line)
                fm = re.search(r"FT=\s*([0-9.Ee+-]+)", line)
                if am:
                    rows[current]["AREA"] = float(am.group(1))
                if dm:
                    rows[current]["QCALC"] = float(dm.group(1))
                    rows[current]["QNET"] = float(dm.group(1))
                if fm:
                    rows[current]["FT"] = float(fm.group(1))
                if ttl == 0:
                    current = None
    return rows


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)):
            return None
        return float(value)
    try:
        if str(value).strip() in {"", "None"}:
            return None
        return float(value)
    except Exception:
        return None


def fmt(value: Any, nd: int = 2) -> str:
    x = as_float(value)
    if x is None:
        return ""
    if abs(x) >= 1000:
        return f"{x:.0f}"
    if abs(x) >= 100:
        return f"{x:.1f}"
    return f"{x:.{nd}f}"


def round_up(value: float, choices: list[float]) -> float:
    for choice in choices:
        if value <= choice:
            return choice
    return choices[-1]


class AspenReader:
    def __init__(self, case_path: Path):
        self.case_path = case_path.resolve()
        self.app: Any | None = None
        self.method = ""

    def __enter__(self) -> "AspenReader":
        import pythoncom
        import win32com.client as win32

        pythoncom.CoInitialize()
        errors: list[str] = []
        for progid in ("Apwn.Document.40.0", "Apwn.Document"):
            try:
                self.app = win32.DispatchEx(progid)
                try:
                    self.app.Visible = False
                    self.app.SuppressDialogs = True
                except Exception:
                    pass
                self.method = progid
                break
            except Exception as exc:
                errors.append(f"{progid}: {exc}")
        if self.app is None:
            raise RuntimeError("Aspen COM dispatch failed: " + " | ".join(errors))

        open_errors: list[str] = []
        for label, call in (
            ("InitFromArchive2", lambda: self.app.InitFromArchive2(str(self.case_path))),
            ("InitFromArchive", lambda: self.app.InitFromArchive(str(self.case_path))),
            ("InitFromFile", lambda: self.app.InitFromFile(str(self.case_path))),
            ("InitFromFile2", lambda: self.app.InitFromFile2(str(self.case_path))),
        ):
            try:
                call()
                self.method += f"/{label}"
                return self
            except Exception as exc:
                open_errors.append(f"{label}: {exc}")
        raise RuntimeError("Aspen open failed: " + " | ".join(open_errors))

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            if self.app is not None:
                self.app.Close(False)
        except Exception:
            pass
        try:
            import pythoncom

            pythoncom.CoUninitialize()
        except Exception:
            pass

    def val(self, path: str) -> Any:
        assert self.app is not None
        try:
            node = self.app.Tree.FindNode(path)
            if node is None:
                return None
            return node.Value
        except Exception:
            return None


def stream_value(reader: AspenReader, stream: str, field: str) -> Any:
    for path in (
        rf"\Data\Streams\{stream}\Output\{field}\MIXED",
        rf"\Data\Streams\{stream}\Output\{field}",
        rf"\Data\Streams\{stream}\Input\{field}\MIXED",
        rf"\Data\Streams\{stream}\Input\{field}",
    ):
        v = reader.val(path)
        if v not in (None, ""):
            return v
    return None


def block_value(reader: AspenReader, tag: str, field: str, section: str = "Output") -> Any:
    return reader.val(rf"\Data\Blocks\{tag}\{section}\{field}")


def extract_streams(reader: AspenReader, stream_ids: list[str], components: list[str]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for sid in sorted(set(stream_ids)):
        row = {
            "stream": sid,
            "temp_c": as_float(stream_value(reader, sid, "TEMP_OUT")),
            "pres_bar": as_float(stream_value(reader, sid, "PRES_OUT")),
            "mole_kmol_h": as_float(stream_value(reader, sid, "MOLEFLMX")),
            "mass_kg_h": as_float(stream_value(reader, sid, "MASSFLMX")),
            "vol_m3_h": as_float(stream_value(reader, sid, "VOLFLMX")),
            "vol_gas_m3_h": as_float(stream_value(reader, sid, "VOLFLMX_GAS")),
            "vol_liq_m3_h": as_float(stream_value(reader, sid, "VOLFLMX_LIQ")),
            "rho_kg_m3": None,
            "vfrac": as_float(stream_value(reader, sid, "VFRAC_OUT")),
            "lfrac": as_float(stream_value(reader, sid, "LFRAC")),
            "mw": as_float(stream_value(reader, sid, "MWMX")),
            "comptype": stream_value(reader, sid, "COMPTYPE") or "",
            "dominant": "",
        }
        rho_mass = as_float(stream_value(reader, sid, "RHOMX_MASS"))
        if rho_mass is not None:
            row["rho_kg_m3"] = rho_mass * 1000.0
        fracs: list[tuple[str, float]] = []
        for comp in components:
            frac = as_float(reader.val(rf"\Data\Streams\{sid}\Output\MASSFRAC\MIXED\{comp}"))
            if frac is None:
                cflow = as_float(reader.val(rf"\Data\Streams\{sid}\Output\MASSFLOW3\{comp}"))
                total_mass = as_float(row["mass_kg_h"])
                if cflow is not None and total_mass:
                    frac = cflow / total_mass
            if frac and frac > 0.005:
                fracs.append((comp, frac))
        fracs.sort(key=lambda x: x[1], reverse=True)
        row["dominant"] = "、".join(f"{COMPONENT_CN.get(c, c)}{f*100:.1f}%" for c, f in fracs[:3])
        rows[sid] = row
    return rows


def extract_blocks(reader: AspenReader, blocks: list[Block]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    common_fields = [
        "QCALC",
        "QNET",
        "DUTY_OUT",
        "B_TEMP",
        "B_VFRAC",
        "BAL_MASI_TFL",
        "BAL_MASO_TFL",
        "VFLOW",
        "DELP_CAL",
        "HEAD_CAL",
        "CEFF",
        "BRAKE_POWER",
        "ELEC_POWER",
        "NPSH-AVAIL",
        "PRES_RATIO",
        "POWER_ISEN",
        "POC",
        "TOC",
        "WNET",
        "PDRP",
        "QCALC",
        "AREA",
        "FT",
        "NSTAGE",
        "CONDENSER",
        "REBOILER",
        "FEED_STAGE",
        "PRES1",
    ]
    for b in blocks:
        row: dict[str, Any] = {"tag": b.tag}
        for field in common_fields:
            row[field] = block_value(reader, b.tag, field, "Output")
            if row[field] is None:
                row[field] = block_value(reader, b.tag, field, "Input")
        rows[b.tag] = row
    return rows


def material_for(streams: list[dict[str, Any]], btype: str) -> str:
    text = " ".join(str(s.get("dominant", "")) for s in streams)
    max_t = max([as_float(s.get("temp_c")) or 0.0 for s in streams] + [0.0])
    if "苯乙烯" in text or "阻聚剂" in text:
        return "S31608"
    if any(x in text for x in ["苯", "甲苯", "乙苯", "二甲苯", "三甲苯", "乙酸甲酯", "甲醇", "乙醇"]):
        return "S31608" if max_t > 80 or btype in {"RADFRAC", "RPLUG", "RSTOIC"} else "S30408"
    if any(x in text for x in ["氢气", "一氧化碳", "二氧化碳"]):
        return "S30408"
    return "S30408"


def stream_phase(row: dict[str, Any]) -> str:
    comp = str(row.get("comptype", "") or "").upper()
    vfrac = as_float(row.get("vfrac"))
    lfrac = as_float(row.get("lfrac"))
    vg = as_float(row.get("vol_gas_m3_h")) or 0.0
    vl = as_float(row.get("vol_liq_m3_h")) or 0.0
    if vg > 0 and vl > 0 and vg / max(vg + vl, 1e-9) > 0.1:
        return "气液两相"
    if "VAPOR" in comp or (vfrac is not None and vfrac > 0.8):
        return "气相"
    if "LIQUID" in comp or (lfrac is not None and lfrac > 0.8):
        return "液相"
    if vfrac is not None and 0.05 < vfrac < 0.8:
        return "气液两相"
    return "液相"


def target_pipe_velocity(row: dict[str, Any]) -> float:
    phase = stream_phase(row)
    p = as_float(row.get("pres_bar")) or 1.0
    q = as_float(row.get("vol_m3_h")) or 0.0
    media = str(row.get("dominant", ""))
    if phase == "气相":
        if p < 0.8:
            return 8.0
        if q > 5000:
            return 14.0
        return 12.0
    if phase == "气液两相":
        return 6.0
    if "苯乙烯" in media or "阻聚剂" in media:
        return 1.2
    if q > 200:
        return 2.0
    if q < 1:
        return 0.8
    return 1.5


def pipe_pressure_class(p_bar: float | None) -> str:
    design_bar = max((p_bar or 1.0) * 1.1, 1.6)
    for pn in (16, 25, 40, 63, 100, 160):
        if design_bar <= pn:
            return f"PN{pn}"
    return "PN250"


def select_pipe_size(q_m3_h: float | None, target_v: float, high_pressure: bool = False) -> tuple[int, float, float, float, str]:
    q_m3_s = max(q_m3_h or 0.0, 0.00001) / 3600.0
    req_id_m = math.sqrt(4.0 * q_m3_s / (math.pi * max(target_v, 0.1)))
    req_id_mm = req_id_m * 1000.0
    for dn, od, sch40, sch80 in PIPE_SIZES:
        thick = sch80 if high_pressure else sch40
        inner = max(1.0, od - 2.0 * thick)
        if inner >= req_id_mm:
            area = math.pi * (inner / 1000.0) ** 2 / 4.0
            velocity = q_m3_s / area
            return dn, od, thick, velocity, "Sch80S" if high_pressure else "Sch40S"
    dn, od, sch40, sch80 = PIPE_SIZES[-1]
    thick = sch80 if high_pressure else sch40
    inner = max(1.0, od - 2.0 * thick)
    area = math.pi * (inner / 1000.0) ** 2 / 4.0
    velocity = q_m3_s / area
    return dn, od, thick, velocity, "Sch80S" if high_pressure else "Sch40S"


def insulation_for_pipe(row: dict[str, Any]) -> str:
    t = as_float(row.get("temp_c"))
    media = str(row.get("dominant", ""))
    if t is None:
        return "按现场温度复核"
    if t >= 180:
        return "硅酸铝保温"
    if t >= 80:
        return "岩棉保温"
    if t <= 5:
        return "冷保温"
    if "苯乙烯" in media:
        return "常温段不保温，低温/长距离段防聚合复核"
    return "不保温"


def build_pipe_selection(blocks: list[Block], streams: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    sources: dict[str, list[str]] = {}
    dests: dict[str, list[str]] = {}
    for b in blocks:
        for sid in b.outs:
            sources.setdefault(sid, []).append(b.tag)
        for sid in b.ins:
            dests.setdefault(sid, []).append(b.tag)

    rows: list[dict[str, str]] = []
    for sid, srow in sorted(streams.items()):
        q = as_float(srow.get("vol_m3_h")) or 0.0
        p = as_float(srow.get("pres_bar")) or 1.0
        t = as_float(srow.get("temp_c"))
        phase = stream_phase(srow)
        target_v = target_pipe_velocity(srow)
        high_pressure = p > 25.0 or (t is not None and t > 300)
        dn, od, thick, velocity, schedule = select_pipe_size(q, target_v, high_pressure)
        line_count = 1
        if velocity > target_v * 1.25:
            line_count = max(2, math.ceil(velocity / max(target_v, 0.1)))
            velocity = velocity / line_count
        material = material_for([srow], "PIPE")
        pn = pipe_pressure_class(p)
        prefix = f"{line_count}×" if line_count > 1 else ""
        spec = f"{prefix}DN{dn} φ{od:g}×{thick:g} {schedule}"
        if q <= 0.001:
            spec = f"DN15 φ21.3×2.77 Sch40S"
            dn, velocity, line_count = 15, 0.0, 1
        reason = (
            f"Aspen {phase}，Q={fmt(q)} m3/h，T={fmt(t)} ℃，P={fmt(p)} bar；"
            f"按目标流速{fmt(target_v)} m/s取{prefix}DN{dn}，回算单管流速{fmt(velocity)} m/s。"
        )
        rows.append(
            {
                "管道号": f"PL-{sid}",
                "Aspen流股": sid,
                "起点设备": "、".join(sources.get(sid, ["界区/外部"])) ,
                "终点设备": "、".join(dests.get(sid, ["界区/外部"])) ,
                "主要介质": str(srow.get("dominant", "")),
                "相态": phase,
                "操作温度/℃": fmt(t),
                "操作压力/bar": fmt(p),
                "质量流量/kg·h-1": fmt(srow.get("mass_kg_h")),
                "体积流量/m3·h-1": fmt(q),
                "推荐管径及规格": spec,
                "压力等级": pn,
                "管材": material,
                "保温/伴热": insulation_for_pipe(srow),
                "计算流速/m·s-1": fmt(velocity),
                "选择理由": reason,
                "证据级别": "Aspen流股+流速筛选",
            }
        )
    return rows


def dn_from_flow(vol_m3_h: float | None, gas: bool = False) -> int:
    q = vol_m3_h or 0.0
    if gas:
        if q < 100:
            return 50
        if q < 500:
            return 100
        if q < 1500:
            return 150
        if q < 5000:
            return 250
        return 400
    if q < 1:
        return 25
    if q < 5:
        return 40
    if q < 20:
        return 65
    if q < 60:
        return 100
    if q < 150:
        return 150
    if q < 500:
        return 250
    return 400


def tower_diameter(max_vol: float, vacuum: bool = False) -> int:
    factor = 1.4 if vacuum else 1.0
    q = max_vol * factor
    if q < 20:
        return 600
    if q < 80:
        return 800
    if q < 200:
        return 1000
    if q < 600:
        return 1400
    if q < 1500:
        return 1800
    if q < 3500:
        return 2400
    return 3200


def vessel_diameter(max_gas_vol: float, max_liq_vol: float) -> int:
    basis = max(max_gas_vol / 3.0, max_liq_vol * 2.0)
    if basis < 80:
        return 500
    if basis < 250:
        return 800
    if basis < 700:
        return 1000
    if basis < 1400:
        return 1400
    if basis < 3000:
        return 1800
    return 2400


def select_pump(block: Block, brow: dict[str, Any], sin: dict[str, Any], sout: dict[str, Any]) -> tuple[str, str, str]:
    q = as_float(brow.get("VFLOW")) or as_float(sin.get("vol_m3_h")) or 0.0
    rho = as_float(sin.get("rho_kg_m3")) or 850.0
    dp_bar = as_float(brow.get("DELP_CAL")) or as_float(brow.get("PDRP"))
    if dp_bar is None:
        pin = as_float(sin.get("pres_bar")) or 0.0
        pout = as_float(sout.get("pres_bar")) or 0.0
        dp_bar = max(0.0, pout - pin)
    head = max(0.0, dp_bar * 100000.0 / max(rho, 1.0) / 9.80665)
    power = as_float(brow.get("BRAKE_POWER")) or as_float(brow.get("ELEC_POWER"))
    phase = str(sin.get("comptype", "")).upper()
    media = sin.get("dominant", "")

    if q < 0.2:
        model, ptype = "G10-1", "螺杆泵"
    elif head > 120:
        stages = max(3, min(15, round(head / 12.0)))
        model, ptype = f"25GDL2-12x{stages}", "立式管道多级离心泵"
    elif q > 500:
        model, ptype = "CZ250-315", "CZ化工流程泵"
    elif "苯" in media and head > 25:
        model, ptype = "50AY60", "卧式离心油泵"
    elif "苯乙烯" in media or ("甲醇" in media and q < 5):
        model, ptype = "NMQ40-40-250", "磁力离心泵"
    elif q < 5 and head > 40:
        stages = max(3, min(12, round(head / 12.0)))
        model, ptype = f"25GDL2-12x{stages}", "立式管道多级离心泵"
    elif q < 25 and head < 30:
        model, ptype = "IS65-50-125(2900)", "单级单吸离心泵"
    elif q < 25:
        model, ptype = "IR65-40-200A", "单级热水/化工离心泵"
    elif q < 120:
        model, ptype = "IR100-80-160", "卧式单级单吸离心泵"
    else:
        model, ptype = "IS150-125-250", "大流量单级离心泵"
    reason = f"Aspen入口相态{phase or '液相'}，Q={fmt(q)} m3/h，扬程约{fmt(head)} m，轴功率约{fmt(power)} kW；按连续流程泵并设置1用1备。"
    return model, ptype, reason


def select_compressor(block: Block, brow: dict[str, Any], sin: dict[str, Any], sout: dict[str, Any]) -> tuple[str, str, str]:
    q_m3_h = as_float(brow.get("VFLOW")) or as_float(sin.get("vol_m3_h")) or 0.0
    q_m3_min = q_m3_h / 60.0
    ratio = as_float(brow.get("PRES_RATIO"))
    if ratio is None:
        pin = as_float(sin.get("pres_bar")) or 1.0
        pout = as_float(sout.get("pres_bar")) or as_float(brow.get("POC")) or pin
        ratio = pout / max(pin, 1e-6)
    power = as_float(brow.get("BRAKE_POWER")) or as_float(brow.get("WNET"))
    pin = as_float(sin.get("pres_bar")) or 0.0
    media = sin.get("dominant", "")
    if pin < 0.8 and ratio <= 2.5:
        model, ctype = ("CL-4000" if q_m3_min > 60 else "CL-400"), "液环式真空压缩机"
    elif ratio > 3.0 and q_m3_min < 20:
        model, ctype = "ZLS-60Di", "螺杆式压缩机"
    elif q_m3_min > 100:
        model, ctype = "ZGT1500", "离心式压缩机"
    elif q_m3_min > 30:
        model, ctype = "ZGT800", "离心式压缩机"
    elif "氢气" in media or "一氧化碳" in media:
        model, ctype = "ZLS-60Di", "螺杆式压缩机"
    else:
        model, ctype = "ZGT500", "离心式压缩机"
    reason = f"Aspen吸气量约{fmt(q_m3_min)} m3/min，压比约{fmt(ratio)}，轴功率约{fmt(power)} kW；按气量与压比选{ctype}。"
    return model, ctype, reason


def area_from_duty(qcalc: float | None) -> float:
    if qcalc is None:
        return 11.5
    q_kw = abs(qcalc) / 1000.0 if abs(qcalc) > 5000 else abs(qcalc)
    if q_kw < 120:
        return 2.1
    if q_kw < 300:
        return 5.4
    if q_kw < 650:
        return 11.5
    if q_kw < 900:
        return 15.2
    if q_kw < 1300:
        return 19.7
    if q_kw < 2200:
        return 26.0
    if q_kw < 3500:
        return 35.4
    if q_kw < 7000:
        return 72.2
    if q_kw < 12000:
        return 90.2
    if q_kw < 22000:
        return 146.5
    return 198.0


def hx_model(area: float, p_bar: float, high_temp: bool = False) -> tuple[str, str]:
    area = round_up(area, STANDARD_AREAS)
    if area <= 3:
        dia = 168
    elif area <= 8:
        dia = 219
    elif area <= 18:
        dia = 273
    elif area <= 30:
        dia = 325
    elif area <= 45:
        dia = 377
    elif area <= 100:
        dia = 500
    elif area <= 180:
        dia = 600
    else:
        dia = 700
    p_mpa = max(0.6, math.ceil(max(p_bar, 1.0) * 1.15 / 10.0 * 10) / 10)
    code = "BKU" if high_temp and area >= 90 else "BEM"
    model = f"{code}{dia}-{p_mpa:.1f}/{p_mpa:.1f}-{area:g}-4.5/25-1I"
    typ = "U形管式换热器" if code == "BKU" else "固定管板式换热器"
    return model, typ


def select_heatex(block: Block, brow: dict[str, Any], streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    q = as_float(brow.get("QCALC")) or as_float(brow.get("QNET"))
    area = as_float(brow.get("AREA")) or area_from_duty(q)
    max_p = max([as_float(s.get("pres_bar")) or 1.0 for s in streams] + [1.0])
    max_t = max([as_float(s.get("temp_c")) or 0.0 for s in streams] + [0.0])
    model, typ = hx_model(area, max_p, max_t > 250)
    units = max(1, math.ceil(area / 350.0))
    if units > 1:
        model = f"{model}×{units}台并联"
    duty_kw = abs(q) / 1000.0 if q is not None and abs(q) > 5000 else abs(q or 0.0)
    direction = "加热" if (q or 0.0) > 0 else "冷却"
    parallel = f"，采用{units}台并联" if units > 1 else ""
    reason = f"Aspen热负荷约{fmt(duty_kw)} kW，估算/输出面积{fmt(area)} m2，最高压力约{fmt(max_p)} bar；按{direction}服务选管壳式换热器{parallel}。"
    return model, typ, reason


def select_tower(block: Block, brow: dict[str, Any], streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    nstage = as_float(brow.get("NSTAGE")) or 30.0
    pres = as_float(brow.get("PRES1")) or min([as_float(s.get("pres_bar")) or 999 for s in streams] + [1.0])
    max_vol = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams] + [0.0])
    vacuum = pres < 0.7 or any((as_float(s.get("pres_bar")) or 99) < 0.7 for s in streams)
    media = " ".join(str(s.get("dominant", "")) for s in streams)
    dia = tower_diameter(max_vol, vacuum)
    height = max(8.0, nstage * (0.26 if vacuum or nstage > 60 else 0.18) + 4.0)
    if vacuum or "苯乙烯" in media or nstage > 60:
        internals = "MellapakPlus 252Y规整填料"
        typ = "真空规整填料精馏塔" if vacuum else "规整填料精馏塔"
    elif "二甲苯" in media or "乙苯" in media:
        internals = "MellapakPlus 452Y/252Y规整填料"
        typ = "共沸/萃取规整填料精馏塔"
    else:
        internals = "F1型浮阀塔板"
        typ = "板式精馏塔"
    model = f"Φ{dia}×{int(round(height * 1000))}，{internals}，N={int(round(nstage))}"
    reason = f"Aspen RadFrac理论级数{int(round(nstage))}，操作压力约{fmt(pres)} bar，最大物流体积流量约{fmt(max_vol)} m3/h；按低压降和分离级数选{typ}。"
    return model, typ, reason


def select_separator(block: Block, streams_in: list[dict[str, Any]], streams_out: list[dict[str, Any]]) -> tuple[str, str, str]:
    gas_vol = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams_out if (as_float(s.get("vfrac")) or 0.0) > 0.5 or "VAPOR" in str(s.get("comptype", "")).upper()] + [0.0])
    liq_vol = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams_out if (as_float(s.get("vfrac")) or 0.0) <= 0.5] + [0.0])
    dia = vessel_diameter(gas_vol, liq_vol)
    height = dia * (3 if gas_vol >= liq_vol else 2.8)
    if gas_vol > liq_vol * 5:
        typ = "立式丝网气液分离器"
    elif liq_vol > gas_vol * 2:
        typ = "卧式气液分离器"
    else:
        typ = "立式丝网气液分离器"
    model = f"Φ{dia}×{int(round(height))}"
    reason = f"Aspen闪蒸/分离后气相约{fmt(gas_vol)} m3/h、液相约{fmt(liq_vol)} m3/h；按气液夹带控制选{typ}。"
    return model, typ, reason


def select_valve(block: Block, streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    q = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams] + [0.0])
    gas = any((as_float(s.get("vfrac")) or 0.0) > 0.5 or "VAPOR" in str(s.get("comptype", "")).upper() for s in streams)
    pin = as_float(streams[0].get("pres_bar")) if streams else None
    pout = as_float(streams[-1].get("pres_bar")) if streams else None
    dp = max(0.0, (pin or 0.0) - (pout or 0.0))
    dn = dn_from_flow(q, gas)
    pn = 16 if max(pin or 0, pout or 0) <= 16 else 64
    if dp > 10:
        model, typ = f"ZJHM-{pn}B DN{dn}", "多级降压调节阀"
    else:
        model, typ = f"ZJHP-{pn}C DN{dn}", "气动薄膜调节阀"
    reason = f"Aspen节流压降约{fmt(dp)} bar，流量约{fmt(q)} m3/h；按调压/分压服务选{typ}，不作为储罐。"
    return model, typ, reason


def select_mixer(block: Block, streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    q = sum((as_float(s.get("vol_m3_h")) or 0.0) for s in streams)
    gas = any((as_float(s.get("vfrac")) or 0.0) > 0.5 for s in streams)
    dn = dn_from_flow(q, gas)
    if q > 3000:
        model, typ = f"DJHX-{dn * 10}", "连续式管道混合器"
    else:
        model, typ = f"SV-15~30/{dn}", "静态混合器"
    reason = f"Aspen混合总入口体积流量约{fmt(q)} m3/h；无相变做功，按管道在线混合选{typ}。"
    return model, typ, reason


def select_split(block: Block, streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    q = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams] + [0.0])
    dn = dn_from_flow(q)
    model, typ = f"ZJHP-16C DN{dn}分流阀组", "分流调节阀组"
    reason = f"Aspen为物流按比例分配，入口体积流量约{fmt(q)} m3/h；按分流调节阀组预选。"
    return model, typ, reason


def select_reactor(block: Block, brow: dict[str, Any], streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    mass = max([as_float(s.get("mass_kg_h")) or 0.0 for s in streams] + [0.0])
    max_t = max([as_float(s.get("temp_c")) or 0.0 for s in streams] + [0.0])
    vapor = any((as_float(s.get("vfrac")) or 0.0) > 0.5 for s in streams)
    if block.btype == "RPLUG" or vapor or max_t > 180:
        if mass < 5000:
            dia, length = 1200, 6000
        elif mass < 30000:
            dia, length = 1600, 7500
        elif mass < 100000:
            dia, length = 1900, 9023
        else:
            dia, length = 2400, 10000
        model, typ = f"Φ{dia}×{length}", "列管式固定床反应器"
    else:
        dia, height = (1200, 1950) if mass < 10000 else (1800, 3000)
        model, typ = f"Φ{dia}×{height}", "搅拌釜式反应器"
    reason = f"Aspen反应器入口/出口最大质量流量约{fmt(mass)} kg/h，最高温度约{fmt(max_t)} ℃；按相态与温度选择{typ}。"
    return model, typ, reason


def select_sep2(block: Block, streams: list[dict[str, Any]]) -> tuple[str, str, str]:
    text = " ".join(str(s.get("dominant", "")) for s in streams)
    q = max([as_float(s.get("vol_m3_h")) or 0.0 for s in streams] + [0.0])
    if "水" in text or "乙烯" in text:
        model, typ = "MS-3A-1200×3000", "3A分子筛吸附干燥器"
    else:
        area = max(50, round(q / 20.0) * 10)
        model, typ = f"HF-CO2-{int(area)}", "中空纤维CO2膜分离器"
    reason = f"Aspen SEP2承担选择性组分分离，入口体积流量约{fmt(q)} m3/h；按目标组分选择{typ}，需后续厂家性能补证。"
    return model, typ, reason


def equipment_name(block: Block) -> str:
    if block.btype == "PUMP":
        return f"{block.ins[0] if block.ins else block.tag}升压泵"
    if block.btype == "COMPR":
        return f"{block.ins[0] if block.ins else block.tag}压缩机"
    if block.btype in {"HEATER", "HEATX"}:
        return f"{block.ins[0] if block.ins else block.tag}换热器"
    if block.btype == "RADFRAC":
        return f"{block.ins[0] if block.ins else block.tag}分离塔"
    if block.btype in {"RPLUG", "RSTOIC"}:
        return f"{block.ins[0] if block.ins else block.tag}反应器"
    if block.btype == "FLASH2":
        return f"{block.ins[0] if block.ins else block.tag}气液分离器"
    if block.btype == "VALVE":
        return f"{block.ins[0] if block.ins else block.tag}调节阀"
    if block.btype == "MIXER":
        return f"{block.tag}混合器"
    if block.btype == "FSPLIT":
        return f"{block.tag}分流器"
    if block.btype == "SEP2":
        return f"{block.tag}选择性分离器"
    return block.tag


def build_selection(blocks: list[Block], streams: dict[str, dict[str, Any]], brows: dict[str, dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    equipment_rows: list[dict[str, str]] = []
    reason_rows: list[dict[str, str]] = []
    for b in blocks:
        in_streams = [streams.get(s, {"stream": s}) for s in b.ins]
        out_streams = [streams.get(s, {"stream": s}) for s in b.outs]
        all_streams = in_streams + out_streams
        brow = brows.get(b.tag, {})
        sin = in_streams[0] if in_streams else {}
        sout = out_streams[0] if out_streams else {}

        if b.btype == "PUMP":
            model, typ, reason = select_pump(b, brow, sin, sout)
            qty = "2（1用1备）"
            equip_tag = f"{b.tag}/B"
        elif b.btype == "COMPR":
            model, typ, reason = select_compressor(b, brow, sin, sout)
            qty = "1"
            equip_tag = b.tag
        elif b.btype in {"HEATER", "HEATX"}:
            model, typ, reason = select_heatex(b, brow, all_streams)
            hx_area = as_float(brow.get("AREA")) or area_from_duty(as_float(brow.get("QCALC")) or as_float(brow.get("QNET")))
            hx_units = max(1, math.ceil(hx_area / 350.0))
            qty = str(hx_units)
            equip_tag = b.tag
        elif b.btype == "RADFRAC":
            model, typ, reason = select_tower(b, brow, all_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype == "FLASH2":
            model, typ, reason = select_separator(b, in_streams, out_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype == "VALVE":
            model, typ, reason = select_valve(b, all_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype == "MIXER":
            model, typ, reason = select_mixer(b, in_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype == "FSPLIT":
            model, typ, reason = select_split(b, in_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype in {"RPLUG", "RSTOIC"}:
            model, typ, reason = select_reactor(b, brow, all_streams)
            qty = "1"
            equip_tag = b.tag
        elif b.btype == "SEP2":
            model, typ, reason = select_sep2(b, all_streams)
            qty = "1"
            equip_tag = b.tag
        else:
            model, typ, reason = b.mdltype, b.btype, "Aspen块类型保留，未进入储罐选型。"
            qty = "1"
            equip_tag = b.tag

        material = material_for(all_streams, b.btype)
        in_desc = "、".join(b.ins)
        out_desc = "、".join(b.outs)
        t_in = fmt(sin.get("temp_c")) if sin else ""
        p_in = fmt(sin.get("pres_bar")) if sin else ""
        q_in = fmt(sin.get("vol_m3_h")) if sin else ""
        m_in = fmt(sin.get("mass_kg_h")) if sin else ""
        media = sin.get("dominant", "") if sin else ""

        row = {
            "设备位号": equip_tag,
            "Aspen块": b.tag,
            "名称": equipment_name(b),
            "Aspen类型": b.btype,
            "选用型号/规格": model,
            "设备类型": typ,
            "入口流股": in_desc,
            "出口流股": out_desc,
            "入口T/℃": t_in,
            "入口P/bar": p_in,
            "入口体积流量/m3·h-1": q_in,
            "入口质量流量/kg·h-1": m_in,
            "主要介质": media,
            "材质": material,
            "台数": qty,
            "证据级别": "Aspen参数+目录级预选",
        }
        equipment_rows.append(row)
        reason_rows.append(
            {
                "设备位号": equip_tag,
                "选用型号/规格": model,
                "选择理由": reason,
                "后续需补证": boundary_for_type(b.btype),
            }
        )
    return equipment_rows, reason_rows


def boundary_for_type(btype: str) -> str:
    if btype in {"HEATER", "HEATX"}:
        return "正式传热面积、压降、壳/管程分配需 EDR 或换热器详算校核。"
    if btype == "RADFRAC":
        return "塔径、压降、液泛、持液量和塔内件需 Column Internals/水力学校核。"
    if btype == "PUMP":
        return "需厂家曲线校核NPSHr、效率和电机功率。"
    if btype == "COMPR":
        return "需压缩机厂家曲线、级间冷却和气体k/Z因子校核。"
    if btype in {"FLASH2", "VALVE"}:
        return "需接管、夹带、阀Cv或容器强度校核。"
    if btype in {"RPLUG", "RSTOIC"}:
        return "需反应器机械强度、催化剂装填、压降和传热详算。"
    if btype == "SEP2":
        return "需膜/吸附剂厂家性能或分离效率证据。"
    return "目录级预选，后续按设备详算补证。"


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, str]], max_rows: int | None = None) -> str:
    shown = rows if max_rows is None else rows[:max_rows]
    cols = list(shown[0].keys())
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in shown:
        vals = [str(row.get(c, "")).replace("|", "/") for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    if max_rows is not None and len(rows) > max_rows:
        lines.append(f"\n> 表格仅预览前 {max_rows} 行；完整 {len(rows)} 行见 CSV/XLSX。")
    return "\n".join(lines)


def write_markdown(
    path: Path,
    source: Path,
    equipment_rows: list[dict[str, str]],
    reason_rows: list[dict[str, str]],
    pipe_rows: list[dict[str, str]],
    method: str,
) -> None:
    text = [
        "# 全流程模拟设备选型结果表（不含储罐）",
        "",
        f"- Aspen文件：`{source}`",
        f"- 抽取方式：只读 COM 打开 `{method}`，导出流股与块结果；未保存、未修改 BKP/APW。",
        "- 选型边界：本表为按 Aspen 参数和既有案例目录体系形成的目录级预选型号；储罐、回流罐、缓冲罐未纳入。",
        "",
        "## 设备选型一览表",
        "",
        md_table(equipment_rows),
        "",
        "## 管道选型一览表",
        "",
        md_table(pipe_rows),
        "",
        "## 选择理由表",
        "",
        md_table(reason_rows),
        "",
    ]
    path.write_text("\n".join(text), encoding="utf-8")


def write_xlsx(path: Path, sheets: dict[str, list[dict[str, Any]]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, rows in sheets.items():
        ws = wb.create_sheet(sheet_name[:31])
        if not rows:
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        widths = {h: max(len(str(h)), 8) for h in headers}
        for row in rows[:200]:
            for h in headers:
                widths[h] = min(max(widths[h], len(str(row.get(h, ""))) + 2), 48)
        for idx, h in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = widths[h]
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bkp", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    bkp = args.bkp.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    components, blocks = parse_bkp(bkp)
    stream_ids = sorted({s for b in blocks for s in (b.ins + b.outs)})

    with AspenReader(bkp) as reader:
        stream_rows = extract_streams(reader, stream_ids, components)
        block_rows = extract_blocks(reader, blocks)
        method = reader.method
    his_rows = parse_his_heatx_results(bkp.with_suffix(".his"))
    for tag, values in his_rows.items():
        block_rows.setdefault(tag, {}).update(values)

    equipment_rows, reason_rows = build_selection(blocks, stream_rows, block_rows)
    pipe_rows = build_pipe_selection(blocks, stream_rows)

    day = stamp()
    base = out_dir / f"{bkp.stem}_设备选型结果_含型号_不含储罐_{day}"
    overview_csv = base.with_name(base.name + "_一览表.csv")
    reason_csv = base.with_name(base.name + "_选择理由表.csv")
    pipe_csv = base.with_name(base.name + "_管道选型表.csv")
    md_path = base.with_suffix(".md")
    xlsx_path = base.with_suffix(".xlsx")
    json_path = base.with_suffix(".json")

    write_csv(overview_csv, equipment_rows)
    write_csv(reason_csv, reason_rows)
    write_csv(pipe_csv, pipe_rows)
    stream_export = [
        {
            "stream": k,
            "T_C": fmt(v.get("temp_c")),
            "P_bar": fmt(v.get("pres_bar")),
            "mass_kg_h": fmt(v.get("mass_kg_h")),
            "vol_m3_h": fmt(v.get("vol_m3_h")),
            "vol_gas_m3_h": fmt(v.get("vol_gas_m3_h")),
            "vol_liq_m3_h": fmt(v.get("vol_liq_m3_h")),
            "vfrac": fmt(v.get("vfrac"), 3),
            "dominant": v.get("dominant", ""),
        }
        for k, v in sorted(stream_rows.items())
    ]
    block_export = []
    for b in blocks:
        br = block_rows.get(b.tag, {})
        block_export.append(
            {
                "tag": b.tag,
                "type": b.btype,
                "in": ",".join(b.ins),
                "out": ",".join(b.outs),
                "QCALC": br.get("QCALC"),
                "VFLOW": br.get("VFLOW"),
                "DELP_CAL": br.get("DELP_CAL"),
                "BRAKE_POWER": br.get("BRAKE_POWER"),
                "PRES_RATIO": br.get("PRES_RATIO"),
                "NSTAGE": br.get("NSTAGE"),
            }
        )
    write_markdown(md_path, bkp, equipment_rows, reason_rows, pipe_rows, method)
    write_xlsx(
        xlsx_path,
        {
            "设备选型一览表": equipment_rows,
            "管道选型一览表": pipe_rows,
            "选择理由表": reason_rows,
            "Aspen流股摘录": stream_export,
            "Aspen块摘录": block_export,
        },
    )
    payload = {
        "source": str(bkp),
        "method": method,
        "blocks": len(blocks),
        "streams": len(stream_rows),
        "outputs": {
            "overview_csv": str(overview_csv),
            "reason_csv": str(reason_csv),
            "pipe_csv": str(pipe_csv),
            "markdown": str(md_path),
            "xlsx": str(xlsx_path),
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
