#!/usr/bin/env python3
"""Build the reviewed HG/T 20592~20635 type-option package.

This builder is the only write path.  Runtime selection never opens the PDF,
page images, OCR assets, or the source-layer directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = (
    ROOT.parents[2]
    / "knowledge_graph"
    / "standards_graph"
    / "source_layer"
    / "documents"
    / "std_hg_t_20592_20635_2009"
)
RAW_PAGES = SOURCE_ROOT / "raw_pages.jsonl"
PDF_SHA256 = "7513C49ABF181FF538E4D3A29050DEDD4DDDBEF9DE11B25840EEF21731D64201"
PACKAGE_VERSION = "hgt20592-20635-type-options-1.0.0"


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_csv(name, rows, fields=None):
    path = ROOT / name
    if not fields:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(name, value):
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_pages():
    pages = {}
    with RAW_PAGES.open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            pages[int(record["page_1based"])] = record
    return pages


EVIDENCE_PAGES = {
    14: "编制说明表2-1：垫片类型、结构、范围与温度总览",
    15: "编制说明：聚四氟乙烯包覆垫片A/B/C结构差异与尺寸适用",
    18: "编制说明：紧固件类型、强度等级与螺纹系列",
    19: "编制说明：紧固件材料和适用性说明",
    35: "HG/T 20592第3章：PN系列法兰类型图示",
    36: "HG/T 20592表3.1.1：PN系列法兰类型代号",
    40: "HG/T 20592第3.2节：密封面型式",
    119: "HG/T 20592附录A：PN系列孔板法兰KWT-T/KWN-S型式",
    120: "HG/T 20592附录A：孔板法兰范围与RF密封面",
    128: "HG/T 20592附录B：夹套法兰JPL/JSO/JWN型式与范围",
    162: "HG/T 20606：聚四氟乙烯包覆垫片A/B/C型及推荐",
    178: "HG/T 20610表3.0.1：PN系列缠绕垫A/B/C/D型",
    190: "HG/T 20611表3.1：PN系列齿形组合垫A/B/C型",
    202: "HG/T 20612：PN系列金属环垫椭圆/八角型",
    250: "HG/T 20614表3.0.1第一页：PN系列法兰选用",
    251: "HG/T 20614表3.0.1续页：PN系列法兰选用",
    252: "HG/T 20614表3.0.2第一页：PN系列垫片选用",
    253: "HG/T 20614表3.0.2续页与紧固件总则",
    254: "HG/T 20614表3.0.3-1和表3.0.3-2第一页：PN紧固件",
    255: "HG/T 20614表3.0.3-2续页与法兰接头",
    256: "HG/T 20614附录A表A.0.3：垫片类型选择补充",
    257: "HG/T 20614附录A：p-T边界与包覆垫A/B/C说明",
    270: "HG/T 20615第3章：Class系列法兰类型",
    273: "HG/T 20615第3.2节：Class系列密封面型式",
    334: "HG/T 20623附录A：Class系列孔板法兰KWT-T/KWN-S型式",
    335: "HG/T 20623附录A：孔板法兰范围与RF密封面",
    341: "HG/T 20623大直径法兰类型和范围",
    360: "HG/T 20623大直径WN/BL法兰适用范围",
    361: "HG/T 20623大直径法兰密封面范围",
    416: "HG/T 20631表3.0.1：Class系列缠绕垫A/B/C/D型",
    417: "HG/T 20631：温度材料与高等级内环要求",
    432: "HG/T 20632表3.1：Class系列齿形组合垫A/B/C型",
    433: "HG/T 20632：温度、材料和对中环要求",
    446: "HG/T 20633：Class系列金属环垫椭圆/八角型",
    447: "HG/T 20633表3.3.1：环垫材料与温度",
    490: "HG/T 20635表3.1.1：Class系列法兰选用",
    491: "HG/T 20635第3.2节：垫片硬限制与适用条件",
    492: "HG/T 20635表3.2.11：Class系列垫片选用",
    493: "HG/T 20635表3.3.1：Class系列紧固件型式",
    494: "HG/T 20635表3.3.10：Class系列紧固件材料选择",
    495: "HG/T 20635附录A表A.0.3：垫片类型选择补充",
    496: "HG/T 20635附录A：p-T边界与包覆垫A/B/C说明",
    531: "2012年5月勘误：PN系列包覆垫代码与PN40紧固件修正",
    532: "2012年5月勘误：LWN/NPT/A-B-C/Class300修正",
}


def source_records(pages):
    rows = []
    for page_no, label in EVIDENCE_PAGES.items():
        page = pages[page_no]
        rows.append(
            {
                "evidence_id": f"E_P{page_no:03d}",
                "page_1based": page_no,
                "authority_label": label,
                "bbox_pt_json": compact([0.0, 0.0, page["width_pt"], page["height_pt"]]),
                "source_raw_text": page["primary_text"],
                "source_text_sha256": page["text_sha256"],
                "source_pdf_sha256": page["source_pdf_sha256"],
                "extraction_method": page["primary_method"],
                "qa_status": "PASS_PAGE_VISUAL_REVIEW",
                "terminal_class": "DIRECT_REUSE_EVIDENCE",
                "annotation_class": "SOURCE_RAW_TEXT",
            }
        )
    return rows


def cat(cid, family, series, code, name, group, priority, refs, summary,
        pn_min="", pn_max="", class_min="", class_max="", dn_min="", dn_max="",
        t_min="", t_max="", faces="", terminal=True):
    return {
        "candidate_id": cid,
        "object_family": family,
        "system_series": series,
        "current_code": code,
        "name_zh": name,
        "subtype_group": group,
        "terminal_selectable": str(bool(terminal)).lower(),
        "pn_min": pn_min,
        "pn_max": pn_max,
        "class_min": class_min,
        "class_max": class_max,
        "dn_min_mm": dn_min,
        "dn_max_mm": dn_max,
        "temperature_min_c": t_min,
        "temperature_max_c": t_max,
        "faces_allowed": faces,
        "default_priority": priority,
        "source_refs": refs,
        "source_raw_text": "",
        "normalized_capability_summary": summary,
        "annotation_class": "ENGINEERING_NORMALIZATION",
        "qa_status": "PASS_REVIEWED_TYPE_CATALOG",
    }


CATALOG = [
    # PN flange types
    cat("FL_PN_PL", "flange_type", "PN", "PL", "板式平焊法兰", "general", 35, "E_P035|E_P036|E_P250", "经济型；仅一般工况，严重循环工况排除"),
    cat("FL_PN_SO", "flange_type", "PN", "SO", "带颈平焊法兰", "general", 55, "E_P035|E_P036|E_P250", "一般管道连接；泛用性低于WN"),
    cat("FL_PN_WN", "flange_type", "PN", "WN", "带颈对焊法兰", "general", 100, "E_P035|E_P036|E_P250", "刚性和循环工况适用性较广；无充分条件时的注册默认"),
    cat("FL_PN_IF", "flange_type", "PN", "IF", "整体法兰", "general", 92, "E_P035|E_P036|E_P250", "设备管口或整体结构；刚性高"),
    cat("FL_PN_SW", "flange_type", "PN", "SW", "承插焊法兰", "small_bore", 45, "E_P035|E_P036|E_P250", "小口径、非严重循环；缝隙/严重腐蚀排除"),
    cat("FL_PN_TH", "flange_type", "PN", "Th", "螺纹法兰", "small_bore", 30, "E_P035|E_P036|E_P250|E_P531", "小口径仪表/公用工程；缝隙/严重腐蚀排除"),
    cat("FL_PN_PJ_SE", "flange_type", "PN", "PJ/SE", "对焊环松套法兰", "lined_or_lap", 42, "E_P035|E_P036|E_P250", "衬里或耐蚀环连接；严重循环排除"),
    cat("FL_PN_PJ_RJ", "flange_type", "PN", "PJ/RJ", "平焊环松套法兰", "lined_or_lap", 38, "E_P035|E_P036|E_P250", "衬里或耐蚀环连接；严重循环排除"),
    cat("FL_PN_BL", "flange_type", "PN", "BL", "法兰盖", "closure", 20, "E_P035|E_P036", "盲端封闭专用"),
    cat("FL_PN_BL_S", "flange_type", "PN", "BL(S)", "衬里法兰盖", "closure", 18, "E_P035|E_P036", "衬里盲端封闭专用"),
    cat("FL_PN_KWN_T", "flange_type", "PN", "KWN-T", "NPT测压孔带颈对焊孔板法兰", "orifice", 15, "E_P119|E_P120", "孔板测量专用，测压孔为NPT连接", pn_min=10, pn_max=160, dn_min=25, dn_max=600, faces="RF"),
    cat("FL_PN_KWN_S", "flange_type", "PN", "KWN-S", "承插焊测压孔带颈对焊孔板法兰", "orifice", 16, "E_P119|E_P120", "孔板测量专用，测压孔为承插焊连接", pn_min=10, pn_max=160, dn_min=25, dn_max=600, faces="RF"),
    cat("FL_PN_JPL", "flange_type", "PN", "JPL", "板式平焊夹套法兰", "jacketed", 15, "E_P128", "夹套管专用；PN16 RF"),
    cat("FL_PN_JSO", "flange_type", "PN", "JSO", "带颈平焊夹套法兰", "jacketed", 17, "E_P128", "夹套管专用；PN16/25，RF/FM-M/T-G"),
    cat("FL_PN_JWN", "flange_type", "PN", "JWN", "带颈对焊夹套法兰", "jacketed", 20, "E_P128", "夹套管专用；PN16/25，RF/FM-M/T-G"),
    # Class flange types
    cat("FL_CL_SO", "flange_type", "CLASS", "SO", "带颈平焊法兰", "general", 55, "E_P270|E_P490", "公用工程或非易燃易爆、低密封要求、-45~200℃", class_min=150, class_max=300, dn_min=15, dn_max=600, t_min=-45, t_max=200, faces="RF"),
    cat("FL_CL_WN", "flange_type", "CLASS", "WN", "带颈对焊法兰", "general", 100, "E_P270|E_P490", "常用且泛用；高温高压RJ连接可用", class_min=150, class_max=2500, dn_min=15, dn_max=1500, faces="RF|RJ"),
    cat("FL_CL_LWN", "flange_type", "CLASS", "LWN", "长高颈法兰", "equipment_nozzle", 76, "E_P270|E_P532", "设备管口长颈结构；勘误确认LWN代码", class_min=150, class_max=2500),
    cat("FL_CL_IF", "flange_type", "CLASS", "IF", "整体法兰", "general", 92, "E_P270|E_P490", "整体结构，刚性高", class_min=150, class_max=2500, dn_min=15, dn_max=1500, faces="RF|RJ"),
    cat("FL_CL_SW", "flange_type", "CLASS", "SW", "承插焊法兰", "small_bore", 45, "E_P270|E_P490", "DN15~50、Class150~900、非严重循环", class_min=150, class_max=900, dn_min=15, dn_max=50, faces="RF"),
    cat("FL_CL_TH", "flange_type", "CLASS", "Th", "螺纹法兰", "small_bore", 30, "E_P270|E_P490|E_P532", "Class150小口径公用工程/仪表；高压锥管螺纹为NPT", class_min=150, class_max=150, dn_min=15, dn_max=150, faces="RF"),
    cat("FL_CL_LF_SE", "flange_type", "CLASS", "LF/SE", "松套法兰/对焊环", "lined_or_lap", 48, "E_P270|E_P490", "不锈钢、镍、钛等衬里管道", class_min=150, class_max=300, dn_min=15, dn_max=600, faces="RF"),
    cat("FL_CL_BL", "flange_type", "CLASS", "BL", "法兰盖", "closure", 20, "E_P270|E_P360", "盲端封闭；大直径范围与WN并列"),
    cat("FL_CL_KWN_T", "flange_type", "CLASS", "KWN-T", "NPT测压孔带颈对焊孔板法兰", "orifice", 15, "E_P334|E_P335", "孔板测量专用，NPT测压孔", class_min=150, class_max=2500, dn_min=25, dn_max=600, faces="RF"),
    cat("FL_CL_KWN_S", "flange_type", "CLASS", "KWN-S", "承插焊测压孔带颈对焊孔板法兰", "orifice", 16, "E_P334|E_P335", "孔板测量专用，承插焊测压孔", class_min=150, class_max=2500, dn_min=25, dn_max=600, faces="RF"),
    # Facing terminals and component codes
    cat("FACE_RF", "facing", "BOTH", "RF", "突面", "single_face", 100, "E_P040|E_P273|E_P490", "最常用密封面；缺省注册默认"),
    cat("FACE_FF", "facing", "BOTH", "FF", "全平面", "single_face", 70, "E_P040|E_P273|E_P491|E_P532", "钢—铸铁连接推荐，配全平面非金属垫"),
    cat("FACE_FM_M_PAIR", "facing", "BOTH", "FM/M", "凹凸面配对", "paired_face", 60, "E_P040|E_P273|E_P490", "常用于内部阀盖/阀体等连接，外部管道较少"),
    cat("FACE_T_G_PAIR", "facing", "BOTH", "T/G", "榫槽面配对", "paired_face", 58, "E_P040|E_P273|E_P490", "约束垫片的配对密封面"),
    cat("FACE_RJ", "facing", "BOTH", "RJ", "环连接面", "single_face", 80, "E_P040|E_P273|E_P490", "金属环垫必需的环槽密封面"),
    cat("FACE_FM_COMPONENT", "facing_component", "BOTH", "FM", "凹面", "component_face", 0, "E_P040|E_P273", "仅作为凹凸配对的一侧", terminal=False),
    cat("FACE_M_COMPONENT", "facing_component", "BOTH", "M", "凸面", "component_face", 0, "E_P040|E_P273", "仅作为凹凸配对的一侧", terminal=False),
    cat("FACE_T_COMPONENT", "facing_component", "BOTH", "T", "榫面", "component_face", 0, "E_P040|E_P273", "仅作为榫槽配对的一侧", terminal=False),
    cat("FACE_G_COMPONENT", "facing_component", "BOTH", "G", "槽面", "component_face", 0, "E_P040|E_P273", "仅作为榫槽配对的一侧", terminal=False),
    # Gaskets
    cat("G_RUBBER_FLAT", "gasket_type", "BOTH", "RUBBER", "橡胶平垫片", "nonmetal_flat", 34, "E_P014|E_P252|E_P492", "低压力一般介质；温度依橡胶材料", pn_max=16, class_min=150, class_max=150, dn_min=10, dn_max=2000, t_max=200, faces="RF|FM/M|T/G|FF"),
    cat("G_ASBESTOS_RUBBER", "gasket_type", "BOTH", "ASBESTOS", "石棉橡胶板垫片", "nonmetal_flat", 10, "E_P014|E_P252|E_P491|E_P492", "受法规和健康约束；不得用于高度/极度危害介质或高真空", pn_max=25, class_min=150, class_max=150, t_max=300, faces="RF|FM/M|T/G|FF"),
    cat("G_NON_ASBESTOS_FIBER", "gasket_type", "BOTH", "NAF", "非石棉纤维橡胶板垫片", "nonmetal_flat", 58, "E_P014|E_P252|E_P491|E_P492", "一般低中压工况；高度/极度危害介质或高真空排除", pn_max=40, class_min=150, class_max=300, t_max=290, faces="RF|FM/M|T/G|FF"),
    cat("G_PTFE_FLAT", "gasket_type", "BOTH", "PTFE", "聚四氟乙烯平垫片", "nonmetal_flat", 42, "E_P014|E_P252|E_P491|E_P492", "耐腐蚀但有冷流倾向，宜FF或受限温度", pn_max=16, class_min=150, class_max=150, t_max=100, faces="RF|FM/M|T/G|FF"),
    cat("G_MODIFIED_PTFE", "gasket_type", "BOTH", "EPTFE/MPTFE", "膨胀或填充改性聚四氟乙烯垫片", "nonmetal_flat", 72, "E_P014|E_P252|E_P492", "耐腐蚀、较宽泛的非金属垫选择", pn_max=40, class_min=150, class_max=300, t_max=200, faces="RF|FM/M|T/G|FF"),
    cat("G_FLEX_GRAPHITE_REINFORCED", "gasket_type", "BOTH", "RFG", "增强柔性石墨垫片", "nonmetal_flat", 76, "E_P014|E_P252|E_P491|E_P492", "耐高温；氧化性介质上限450℃；不锈钢/镍法兰需氯离子控制", pn_min=10, pn_max=63, class_min=150, class_max=600, t_max=650, faces="RF|FM/M|T/G"),
    cat("G_MICA_COMPOSITE", "gasket_type", "BOTH", "MICA", "高温云母复合垫片", "nonmetal_flat", 60, "E_P014|E_P252|E_P492", "高温非金属候选，最高温度900℃范围", pn_min=10, pn_max=63, class_min=150, class_max=600, t_max=900, faces="RF|FM/M|T/G"),
    cat("G_PTFE_ENVELOPE_A", "gasket_type", "BOTH", "A", "剖切型聚四氟乙烯包覆垫片", "ptfe_envelope", 50, "E_P015|E_P162|E_P257|E_P491|E_P496|E_P531|E_P532", "DN≤500；真空或嵌入层易腐蚀时排除", pn_min=6, pn_max=40, class_min=150, class_max=300, dn_min=10, dn_max=500, t_max=150, faces="RF"),
    cat("G_PTFE_ENVELOPE_B", "gasket_type", "BOTH", "B", "机加工型聚四氟乙烯包覆垫片", "ptfe_envelope", 64, "E_P015|E_P162|E_P257|E_P491|E_P496|E_P531|E_P532", "DN≤500，标准说明推荐；可加厚内径、利于齐平", pn_min=6, pn_max=40, class_min=150, class_max=300, dn_min=10, dn_max=500, t_max=150, faces="RF"),
    cat("G_PTFE_ENVELOPE_C", "gasket_type", "BOTH", "C", "折包型聚四氟乙烯包覆垫片", "ptfe_envelope", 44, "E_P015|E_P162|E_P257|E_P491|E_P496|E_P531|E_P532", "DN≥350；尺寸弹性大但存在搭接且密封性低于A/B", pn_min=6, pn_max=40, class_min=150, class_max=300, dn_min=350, dn_max=600, t_max=150, faces="RF"),
    cat("G_METAL_JACKET_I", "gasket_type", "BOTH", "I", "I型金属包覆垫片", "metal_jacket", 48, "E_P014|E_P252|E_P492", "半金属垫；温度由包覆层和填充层较低值控制", pn_min=25, pn_max=100, class_min=300, class_max=900, dn_min=10, dn_max=600, faces="RF"),
    cat("G_METAL_JACKET_II", "gasket_type", "BOTH", "II", "II型金属包覆垫片", "metal_jacket", 46, "E_P014|E_P252|E_P492", "半金属垫；温度由包覆层和填充层较低值控制", pn_min=25, pn_max=100, class_min=300, class_max=900, dn_min=10, dn_max=600, faces="RF"),
    cat("G_SPIRAL_A", "gasket_type", "BOTH", "A", "基本型缠绕垫", "spiral_wound", 62, "E_P178|E_P416", "用于T/G；不带内环/对中环", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="T/G"),
    cat("G_SPIRAL_B", "gasket_type", "BOTH", "B", "带内环型缠绕垫", "spiral_wound", 72, "E_P178|E_P416|E_P417", "用于FM/M；高等级或PTFE填充需内环", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="FM/M"),
    cat("G_SPIRAL_C", "gasket_type", "BOTH", "C", "带对中环型缠绕垫", "spiral_wound", 82, "E_P178|E_P416", "用于RF/FF；便于对中但无内环", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="RF|FF"),
    cat("G_SPIRAL_D", "gasket_type", "BOTH", "D", "带内环和对中环型缠绕垫", "spiral_wound", 100, "E_P178|E_P416|E_P417|E_P491", "RF/FF泛用半金属垫；无充分条件时注册默认", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="RF|FF"),
    cat("G_KAMMPROFILE_A", "gasket_type", "BOTH", "A", "基本型齿形组合垫", "kammprofile", 68, "E_P190|E_P432", "用于T/G或FM/M", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="T/G|FM/M"),
    cat("G_KAMMPROFILE_B", "gasket_type", "BOTH", "B", "带整体对中环型齿形组合垫", "kammprofile", 82, "E_P190|E_P432|E_P433", "RF/FF；整体对中环与齿形金属环同材", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="RF|FF"),
    cat("G_KAMMPROFILE_C", "gasket_type", "BOTH", "C", "带活动对中环型齿形组合垫", "kammprofile", 80, "E_P190|E_P432|E_P433", "RF/FF；活动对中环可采用经表面处理的碳钢", pn_min=16, pn_max=160, class_min=150, class_max=2500, dn_min=10, dn_max=1500, faces="RF|FF"),
    cat("G_RING_OVAL", "gasket_type", "BOTH", "OVAL", "椭圆型金属环垫", "ring_joint", 78, "E_P202|E_P446|E_P447", "仅RJ；垫片硬度应低于法兰环槽面", pn_min=63, pn_max=160, class_min=150, class_max=2500, dn_min=15, dn_max=900, t_max=700, faces="RJ"),
    cat("G_RING_OCTAGONAL", "gasket_type", "BOTH", "OCTAGONAL", "八角型金属环垫", "ring_joint", 84, "E_P202|E_P446|E_P447", "仅RJ；垫片硬度应低于法兰环槽面", pn_min=63, pn_max=160, class_min=150, class_max=2500, dn_min=15, dn_max=900, t_max=700, faces="RJ"),
    # Fastener assemblies
    cat("FST_PN_HEX_I", "fastener_type", "PN", "HEX+NUT-I", "六角头螺栓+I型六角螺母", "bolt_assembly", 50, "E_P018|E_P254|E_P531", "低等级、非严重循环的一般连接；勘误后上限PN40", pn_max=40),
    cat("FST_PN_DOUBLE_I", "fastener_type", "PN", "DOUBLE-STUD+NUT-I", "双头螺柱+I型六角螺母", "stud_assembly", 72, "E_P018|E_P254|E_P255", "需螺柱连接但不要求全螺纹的中间选项"),
    cat("FST_PN_FULL_II", "fastener_type", "PN", "FULL-STUD+NUT-II", "全螺纹螺柱+II型六角螺母", "stud_assembly", 100, "E_P018|E_P254|E_P255|E_P531", "高温、高压、循环及缺省泛用选择"),
    cat("FST_CL_HEX_I", "fastener_type", "CLASS", "HEX+NUT-I", "六角头螺栓+I型六角螺母", "bolt_assembly", 48, "E_P018|E_P493", "Class150一般连接", class_min=150, class_max=150),
    cat("FST_CL_FULL_HH", "fastener_type", "CLASS", "FULL-STUD+HEAVY-HEX", "全螺纹螺柱+重型六角螺母", "stud_assembly", 100, "E_P018|E_P493|E_P494", "Class150~2500泛用、高载荷连接", class_min=150, class_max=2500),
]


CONDITION_REGISTRY = [
    ("object_family", "string", "", "flange_type|facing|gasket_type|fastener_type", "用户/调用脚本必填，确定候选对象族"),
    ("system_series", "string", "", "PN|CLASS", "从Aspen项目约定或用户法兰标准归一；缺失时不得臆造压力等级"),
    ("module_id", "string", "", "", "Aspen模块标识或手动记录标识；原始输入"),
    ("module_type", "string", "", "Aspen block class/user equipment class", "Aspen模块类别原始字段；供上游设备映射"),
    ("pressure_value", "number", "source unit", "", "Aspen流股/设备压力；仅归一为MPa，不直接替代法兰额定等级"),
    ("pressure_unit", "string", "", "Pa|kPa|MPa|bar|bara|barg|psi", "程序单位归一；表压需另有大气压基准"),
    ("pressure_mpa", "number", "MPa", "", "由pressure_value确定性换算；DETERMINISTIC_DERIVATION"),
    ("pn", "number", "bar-class code", "6|10|16|25|40|63|100|160", "用户/设计额定等级；不得仅凭操作压力越过p-T材料曲线确定"),
    ("class_rating", "number", "ASME Class", "150|300|600|900|1500|2500", "用户/设计额定等级"),
    ("dn_mm", "number", "mm", "", "Aspen管径、管道计算或用户给定；用于范围匹配"),
    ("temperature_value", "number", "source unit", "", "Aspen流股或手动原始温度；设计温度优先于操作温度"),
    ("temperature_unit", "string", "", "C|K|F", "温度单位，程序确定性换算为°C"),
    ("temperature_c", "number", "°C", "", "由temperature_value和temperature_unit确定性换算；DERIVED_OUTPUT_ONLY"),
    ("phase", "string", "", "liquid|vapor|two_phase|solid_bearing|unknown", "Aspen相态/汽液分率归一"),
    ("vapor_fraction", "number", "fraction", "0..1", "Aspen VFRAC；只用于相态归一"),
    ("solid_fraction", "number", "fraction", "0..1", "Aspen固相分率；只用于相态归一"),
    ("components", "array[object]", "", "component_id + fraction + basis", "Aspen组分及组成原始字段；名称本身不触发危害/腐蚀标签"),
    ("property_evidence", "array[object]", "", "fact + value + source_id + validity", "由有来源物性/相容性图谱生成的事实；无source_id一律拒绝"),
    ("composition_tags", "array[string]", "", "oxidizer|halide|acid|alkali|solvent|abrasive|polymerizing|other", "由Aspen组分清单和用户介质描述归一"),
    ("corrosivity", "string", "", "none|low|moderate|high|severe|unknown", "材料/腐蚀数据或用户条件；无数据保持unknown"),
    ("toxicity", "string", "", "normal|moderate|high|extreme|unknown", "法规/用户危害分类；标准中的高度/极度危害对应high/extreme"),
    ("flammability", "string", "", "nonflammable|flammable|highly_flammable|unknown", "SDS/用户/Aspen组分辅助归一"),
    ("explosivity", "string", "", "none|possible|explosive|unknown", "爆炸危险属性"),
    ("cleanliness", "string", "", "ordinary|clean|high_purity|sterile|unknown", "清洁/卫生要求；本标准未覆盖卫生认证"),
    ("leak_tightness", "string", "", "ordinary|enhanced|high|zero_emission|unknown", "密封等级要求；zero_emission需项目/供应商验证"),
    ("vacuum_level", "string", "", "none|vacuum|high_vacuum|unknown", "Aspen压力加当地大气压/用户真空等级归一"),
    ("severe_cyclic", "boolean", "", "true|false|unknown", "温压循环是否严重"),
    ("thermal_shock", "boolean", "", "true|false|unknown", "热冲击/快速温变"),
    ("oxidizing", "boolean", "", "true|false|unknown", "介质氧化性；影响柔性石墨上限"),
    ("crevice_corrosion_risk", "boolean", "", "true|false|unknown", "缝隙腐蚀风险"),
    ("severe_corrosion", "boolean", "", "true|false|unknown", "严重腐蚀风险"),
    ("utility_service", "boolean", "", "true|false|unknown", "公用工程工况"),
    ("instrument_service", "boolean", "", "true|false|unknown", "仪表/小口径螺纹连接工况"),
    ("low_sealing_demand", "boolean", "", "true|false|unknown", "低密封要求"),
    ("lining_material", "string", "", "none|stainless|nickel|titanium|other|unknown", "衬里材质"),
    ("flange_material_group", "string", "", "steel|stainless|nickel|titanium|cast_iron|other|unknown", "法兰材料组"),
    ("mating_material_group", "string", "", "steel|stainless|nickel|titanium|cast_iron|other|unknown", "对接件材料组"),
    ("current_facing", "string", "", "RF|FF|FM/M|T/G|RJ|unknown", "现有/拟定密封面配对"),
    ("gasket_family_preference", "string", "", "nonmetal_flat|ptfe_envelope|metal_jacket|spiral_wound|kammprofile|ring_joint|none", "用户偏好；不能越过硬排除"),
    ("ring_joint_required", "boolean", "", "true|false|unknown", "金属环垫或环槽连接要求"),
    ("flush_bore_required", "boolean", "", "true|false|unknown", "要求垫片/内环内径与法兰内径齐平"),
    ("core_corrosion_risk", "boolean", "", "true|false|unknown", "PTFE包覆垫嵌入层被介质腐蚀风险"),
    ("fire_safe_required", "boolean", "", "true|false|unknown", "防火要求；本标准类型表不足以给出认证结论"),
    ("cleanability_required", "boolean", "", "true|false|unknown", "可清洗/无滞留要求；本标准仅给局部结构提示"),
    ("jacketed_pipe", "boolean", "", "true|false|unknown", "夹套管连接"),
    ("orifice_service", "boolean", "", "true|false|unknown", "孔板流量测量连接"),
    ("pressure_tap_connection", "string", "", "NPT|socket_weld|unknown", "孔板法兰测压孔连接形式"),
    ("closure_required", "boolean", "", "true|false|unknown", "盲端封闭"),
    ("internal_component_connection", "boolean", "", "true|false|unknown", "阀盖/阀体等内部连接"),
    ("user_forced_candidate_id", "string", "", "registered candidate id", "人工覆盖；若触发硬排除，程序拒绝并报警"),
]


DERIVED_OUTPUT_FIELDS = {
    "pressure_mpa", "temperature_c", "phase", "corrosivity", "toxicity",
    "flammability", "explosivity", "cleanliness", "leak_tightness",
    "vacuum_level", "severe_cyclic", "thermal_shock", "oxidizing",
    "crevice_corrosion_risk", "severe_corrosion", "utility_service",
    "instrument_service", "low_sealing_demand", "lining_material",
    "flange_material_group", "mating_material_group", "current_facing",
    "ring_joint_required", "core_corrosion_risk", "fire_safe_required",
    "cleanability_required", "jacketed_pipe", "orifice_service",
    "closure_required", "internal_component_connection",
}


SERVICE_LABEL_DERIVATION = [
    {"derivation_id":"D_PRESSURE_MPA","raw_inputs":"pressure_value|pressure_unit","output_label":"pressure_mpa","method":"unit conversion table Pa/kPa/MPa/bar/bara/barg/psi -> MPa","missing_behavior":"UNKNOWN+W_RATING_MISSING","source_requirement":"deterministic unit definition","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"derivation_id":"D_TEMPERATURE_C","raw_inputs":"temperature_value|temperature_unit","output_label":"temperature_c","method":"C/K/F deterministic conversion","missing_behavior":"UNKNOWN","source_requirement":"deterministic unit definition","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"derivation_id":"D_PHASE","raw_inputs":"vapor_fraction|solid_fraction","output_label":"phase","method":"solid_fraction>1e-9 => solid_bearing; else vapor_fraction endpoints/interior => liquid/vapor/two_phase","missing_behavior":"UNKNOWN","source_requirement":"Aspen raw result","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"derivation_id":"D_PROPERTY_FACTS","raw_inputs":"components|temperature_value|pressure_value|property_evidence","output_label":"corrosivity|toxicity|flammability|explosivity|oxidizing|crevice_corrosion_risk|severe_corrosion","method":"accept only fact records with source_id and valid condition range; never infer from component name","missing_behavior":"UNKNOWN+W_PROPERTY_LABEL_UNKNOWN","source_requirement":"property/compatibility graph evidence id required","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"derivation_id":"D_REQUIREMENT_FACTS","raw_inputs":"module_id|module_type|property_evidence","output_label":"cleanliness|leak_tightness|severe_cyclic|thermal_shock|utility_service|instrument_service|low_sealing_demand|fire_safe_required|cleanability_required","method":"accept only source-bearing project/module requirement facts","missing_behavior":"UNKNOWN","source_requirement":"project requirement or module-rule evidence id required","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"derivation_id":"D_GEOMETRY_FACTS","raw_inputs":"module_id|module_type|property_evidence","output_label":"lining_material|flange_material_group|mating_material_group|current_facing|ring_joint_required|jacketed_pipe|orifice_service|closure_required|internal_component_connection","method":"accept only source-bearing geometry/material facts","missing_behavior":"UNKNOWN","source_requirement":"Aspen mapping, user raw equipment parameter, or material graph evidence id required","annotation_class":"DETERMINISTIC_DERIVATION"},
]


def capability(cid, tags, limits, strengths, weaknesses, refs):
    return {
        "candidate_id": cid,
        "capability_tags_json": compact(tags),
        "limit_tags_json": compact(limits),
        "strength_tags_json": compact(strengths),
        "weakness_tags_json": compact(weaknesses),
        "source_refs": refs,
        "source_raw_text": "",
        "normalized_annotation": "候选能力标签仅用于确定性匹配；数值限值来自表列，定性等级为工程归一化，不替代材料p-T曲线、泄漏等级或供应商确认。",
        "annotation_class": "ENGINEERING_NORMALIZATION",
    }


def build_capabilities():
    rows = []
    for item in CATALOG:
        if item["terminal_selectable"] != "true":
            continue
        cid, family, group = item["candidate_id"], item["object_family"], item["subtype_group"]
        tags = {"series": item["system_series"], "subtype_group": group, "faces": item["faces_allowed"].split("|") if item["faces_allowed"] else []}
        limits = {key: item[key] for key in ("pn_min", "pn_max", "class_min", "class_max", "dn_min_mm", "dn_max_mm", "temperature_min_c", "temperature_max_c") if item[key] != ""}
        strengths, weaknesses = [], []
        if family == "flange_type":
            strengths = ["pressure_boundary_connection"]
            if "WN" in cid or cid.endswith("_IF") or cid.endswith("_LWN"):
                strengths += ["high_generality", "cyclic_resistance"]
            if group == "small_bore": weaknesses += ["crevice_corrosion_sensitive"]
            if group == "orifice": strengths += ["orifice_metering"]
            if group == "jacketed": strengths += ["jacketed_pipe"]
        elif family == "facing":
            strengths = ["face_pair_definition"]
            if cid == "FACE_RJ": strengths += ["ring_joint_compatibility", "high_leak_tightness_potential"]
            if cid == "FACE_FF": strengths += ["cast_iron_interface"]
        elif family == "gasket_type":
            strengths = ["sealing_element"]
            if group in ("spiral_wound", "kammprofile", "ring_joint"): strengths += ["enhanced_leak_tightness", "cyclic_service_candidate"]
            if group in ("ptfe_envelope", "nonmetal_flat") and ("PTFE" in cid): strengths += ["corrosion_resistance"]
            if group == "ptfe_envelope": weaknesses += ["vacuum_excluded", "core_corrosion_sensitive"]
            if cid in ("G_ASBESTOS_RUBBER", "G_NON_ASBESTOS_FIBER"): weaknesses += ["high_hazard_excluded", "high_vacuum_excluded"]
            if cid == "G_FLEX_GRAPHITE_REINFORCED": weaknesses += ["oxidizing_temperature_limit_450c"]
        elif family == "fastener_type":
            strengths = ["joint_preload"]
            if "FULL" in cid: strengths += ["high_generality", "high_pressure_temperature_candidate"]
            else: weaknesses += ["rating_and_cyclic_limit"]
        rows.append(capability(cid, tags, limits, strengths, weaknesses, item["source_refs"]))
    return rows


def pred(**kwargs):
    return compact(kwargs)


HARD_EXCLUSIONS = [
    {"rule_id":"HX_FL_SEVERE_CYCLIC_LAP","object_family":"flange_type","candidate_ids":"FL_PN_PL|FL_PN_PJ_SE|FL_PN_PJ_RJ|FL_CL_LF_SE","predicate_json":pred(field="severe_cyclic",op="eq",value=True),"reason":"板式平焊、螺纹及松套环类不得用于严重循环；保守将松套类先排除","source_refs":"E_P250|E_P251|E_P490","annotation_class":"ENGINEERING_NORMALIZATION"},
    {"rule_id":"HX_FL_CORROSION_TH_SW","object_family":"flange_type","candidate_ids":"FL_PN_TH|FL_PN_SW|FL_CL_TH|FL_CL_SW","predicate_json":compact({"any":[{"field":"crevice_corrosion_risk","op":"eq","value":True},{"field":"severe_corrosion","op":"eq","value":True},{"field":"corrosivity","op":"in","value":["high","severe"]}]}),"reason":"螺纹法兰和承插焊法兰不用于可能缝隙腐蚀或严重腐蚀场合","source_refs":"E_P251|E_P491","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_FL_SO_HAZARD","object_family":"flange_type","candidate_ids":"FL_CL_SO","predicate_json":compact({"any":[{"field":"flammability","op":"in","value":["flammable","highly_flammable"]},{"field":"explosivity","op":"in","value":["possible","explosive"]},{"field":"low_sealing_demand","op":"eq","value":False}]}),"reason":"Class SO表列用途为公用工程或非易燃易爆、低密封要求","source_refs":"E_P490","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_FL_SO_TEMP","object_family":"flange_type","candidate_ids":"FL_CL_SO","predicate_json":compact({"any":[{"field":"temperature_c","op":"lt","value":-45},{"field":"temperature_c","op":"gt","value":200}]}),"reason":"Class SO表列温度范围-45~200℃","source_refs":"E_P490","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_FL_SPECIAL_NOT_ORIFICE","object_family":"flange_type","candidate_ids":"FL_PN_KWN_T|FL_PN_KWN_S|FL_CL_KWN_T|FL_CL_KWN_S","predicate_json":pred(field="orifice_service",op="eq",value=False),"reason":"孔板法兰仅用于孔板测量连接","source_refs":"E_P119|E_P120|E_P334|E_P335","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"rule_id":"HX_FL_SPECIAL_NOT_JACKET","object_family":"flange_type","candidate_ids":"FL_PN_JPL|FL_PN_JSO|FL_PN_JWN","predicate_json":pred(field="jacketed_pipe",op="eq",value=False),"reason":"夹套法兰仅用于夹套管连接","source_refs":"E_P128","annotation_class":"DETERMINISTIC_DERIVATION"},
    {"rule_id":"HX_G_ENVELOPE_VACUUM","object_family":"gasket_type","candidate_ids":"G_PTFE_ENVELOPE_A|G_PTFE_ENVELOPE_B|G_PTFE_ENVELOPE_C","predicate_json":pred(field="vacuum_level",op="in",value=["vacuum","high_vacuum"]),"reason":"聚四氟乙烯包覆垫片不用于真空","source_refs":"E_P491","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_ENVELOPE_CORE_CORROSION","object_family":"gasket_type","candidate_ids":"G_PTFE_ENVELOPE_A|G_PTFE_ENVELOPE_B|G_PTFE_ENVELOPE_C","predicate_json":pred(field="core_corrosion_risk",op="eq",value=True),"reason":"聚四氟乙烯包覆垫片不用于嵌入层材料易被介质腐蚀的场合","source_refs":"E_P491","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_FLAT_HAZARD","object_family":"gasket_type","candidate_ids":"G_ASBESTOS_RUBBER|G_NON_ASBESTOS_FIBER","predicate_json":pred(field="toxicity",op="in",value=["high","extreme"]),"reason":"石棉和非石棉垫片不用于极度或高度危害介质","source_refs":"E_P491","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_FLAT_HIGH_VAC","object_family":"gasket_type","candidate_ids":"G_ASBESTOS_RUBBER|G_NON_ASBESTOS_FIBER","predicate_json":pred(field="vacuum_level",op="eq",value="high_vacuum"),"reason":"石棉和非石棉垫片不用于高真空密封","source_refs":"E_P491","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_GRAPHITE_OXIDIZING","object_family":"gasket_type","candidate_ids":"G_FLEX_GRAPHITE_REINFORCED","predicate_json":compact({"all":[{"field":"oxidizing","op":"eq","value":True},{"field":"temperature_c","op":"gt","value":450}]}),"reason":"柔性石墨用于氧化性介质时最高450℃","source_refs":"E_P491|E_P417|E_P433","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_ENVELOPE_A_B_DN","object_family":"gasket_type","candidate_ids":"G_PTFE_ENVELOPE_A|G_PTFE_ENVELOPE_B","predicate_json":pred(field="dn_mm",op="gt",value=500),"reason":"A/B型包覆垫适用于DN≤500","source_refs":"E_P015|E_P162","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_ENVELOPE_C_DN","object_family":"gasket_type","candidate_ids":"G_PTFE_ENVELOPE_C","predicate_json":pred(field="dn_mm",op="lt",value=350),"reason":"C型包覆垫用于DN≥350","source_refs":"E_P015|E_P162","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_RING_FACE","object_family":"gasket_type","candidate_ids":"G_RING_OVAL|G_RING_OCTAGONAL","predicate_json":pred(field="current_facing",op="not_in",value=["RJ","unknown",None]),"reason":"金属环垫仅配RJ环连接面","source_refs":"E_P202|E_P446|E_P492","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_SPIRAL_A_FACE","object_family":"gasket_type","candidate_ids":"G_SPIRAL_A","predicate_json":pred(field="current_facing",op="not_in",value=["T/G","unknown",None]),"reason":"A型缠绕垫适用T/G","source_refs":"E_P178|E_P416","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_SPIRAL_B_FACE","object_family":"gasket_type","candidate_ids":"G_SPIRAL_B","predicate_json":pred(field="current_facing",op="not_in",value=["FM/M","unknown",None]),"reason":"B型缠绕垫适用FM/M","source_refs":"E_P178|E_P416","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_G_SPIRAL_CD_FACE","object_family":"gasket_type","candidate_ids":"G_SPIRAL_C|G_SPIRAL_D","predicate_json":pred(field="current_facing",op="not_in",value=["RF","FF","unknown",None]),"reason":"C/D型缠绕垫适用RF并可用于FF","source_refs":"E_P178|E_P416","annotation_class":"SOURCE_NORMALIZATION"},
    {"rule_id":"HX_FST_HEX_CYCLIC","object_family":"fastener_type","candidate_ids":"FST_PN_HEX_I|FST_CL_HEX_I","predicate_json":compact({"any":[{"field":"severe_cyclic","op":"eq","value":True},{"field":"thermal_shock","op":"eq","value":True}]}),"reason":"低强度/六角螺栓组件仅用于非严重循环；循环工况采用全螺纹螺柱","source_refs":"E_P253|E_P254|E_P493|E_P494","annotation_class":"ENGINEERING_NORMALIZATION"},
]


def compat(rule_id, family, priority, predicate, allowed, strength, reason, refs, ann="SOURCE_NORMALIZATION"):
    return {"rule_id":rule_id,"object_family":family,"priority":priority,"predicate_json":compact(predicate),"allowed_candidate_ids":allowed,"strength":strength,"reason":reason,"source_refs":refs,"annotation_class":ann}


COMPATIBILITY = [
    compat("MC_FL_ORIFICE_NPT","flange_type",100,{"all":[{"field":"orifice_service","op":"eq","value":True},{"field":"pressure_tap_connection","op":"eq","value":"NPT"}]},"FL_PN_KWN_T|FL_CL_KWN_T","MANDATORY","孔板测量且测压孔为NPT时匹配KWN-T","E_P119|E_P334"),
    compat("MC_FL_ORIFICE_SW","flange_type",100,{"all":[{"field":"orifice_service","op":"eq","value":True},{"field":"pressure_tap_connection","op":"eq","value":"socket_weld"}]},"FL_PN_KWN_S|FL_CL_KWN_S","MANDATORY","孔板测量且测压孔为承插焊时匹配KWN-S","E_P119|E_P334"),
    compat("MC_FL_JACKET","flange_type",95,{"field":"jacketed_pipe","op":"eq","value":True},"FL_PN_JPL|FL_PN_JSO|FL_PN_JWN","MANDATORY","夹套管连接限定夹套法兰族","E_P128"),
    compat("MC_FL_CLOSURE","flange_type",90,{"field":"closure_required","op":"eq","value":True},"FL_PN_BL|FL_PN_BL_S|FL_CL_BL","MANDATORY","盲端封闭限定法兰盖","E_P035|E_P270"),
    compat("MC_FACE_RING","facing",100,{"field":"ring_joint_required","op":"eq","value":True},"FACE_RJ","MANDATORY","金属环垫必须配RJ","E_P202|E_P446|E_P492"),
    compat("MC_FACE_CAST_IRON","facing",80,{"any":[{"field":"flange_material_group","op":"eq","value":"cast_iron"},{"field":"mating_material_group","op":"eq","value":"cast_iron"}]},"FACE_FF","MANDATORY_POLICY","钢—铸铁低等级连接按勘误后条款优先FF；宜用条款转为确定性政策时保留说明","E_P491|E_P532","ENGINEERING_NORMALIZATION"),
    compat("MC_FACE_INTERNAL","facing",70,{"field":"internal_component_connection","op":"eq","value":True},"FACE_FM_M_PAIR|FACE_T_G_PAIR","PREFERRED","内部连接优先凹凸或榫槽配对","E_P490"),
    compat("MC_G_FACE_RJ","gasket_type",100,{"any":[{"field":"ring_joint_required","op":"eq","value":True},{"field":"current_facing","op":"eq","value":"RJ"}]},"G_RING_OVAL|G_RING_OCTAGONAL","MANDATORY","RJ环槽限定金属环垫","E_P202|E_P446|E_P492"),
    compat("MC_G_PREF_ENVELOPE","gasket_type",80,{"field":"gasket_family_preference","op":"eq","value":"ptfe_envelope"},"G_PTFE_ENVELOPE_A|G_PTFE_ENVELOPE_B|G_PTFE_ENVELOPE_C","PREFERRED_STRONG","用户指定包覆垫族时，在硬排除之后优先A/B/C","E_P162|E_P491"),
    compat("MC_G_PREF_SPIRAL","gasket_type",80,{"field":"gasket_family_preference","op":"eq","value":"spiral_wound"},"G_SPIRAL_A|G_SPIRAL_B|G_SPIRAL_C|G_SPIRAL_D","PREFERRED_STRONG","用户指定缠绕垫族","E_P178|E_P416"),
    compat("MC_G_PREF_KAMM","gasket_type",80,{"field":"gasket_family_preference","op":"eq","value":"kammprofile"},"G_KAMMPROFILE_A|G_KAMMPROFILE_B|G_KAMMPROFILE_C","PREFERRED_STRONG","用户指定齿形组合垫族","E_P190|E_P432"),
]


def score(rule_id, family, candidates, points, predicate, reason, refs, ann="ENGINEERING_NORMALIZATION"):
    return {"rule_id":rule_id,"object_family":family,"candidate_ids":candidates,"score":points,"predicate_json":compact(predicate),"reason":reason,"source_refs":refs,"annotation_class":ann}


SELECTION_RULES = [
    score("SC_FL_UTILITY_SO","flange_type","FL_CL_SO|FL_PN_SO",45,{"all":[{"field":"utility_service","op":"eq","value":True},{"field":"low_sealing_demand","op":"eq","value":True},{"field":"flammability","op":"in","value":["nonflammable","unknown",None]}]},"公用工程、非易燃、低密封要求优先平焊","E_P490","SOURCE_NORMALIZATION"),
    score("SC_FL_INSTRUMENT_TH","flange_type","FL_CL_TH|FL_PN_TH",70,{"field":"instrument_service","op":"eq","value":True},"仪表小口径工况优先螺纹法兰","E_P490|E_P532","SOURCE_NORMALIZATION"),
    score("SC_FL_LINED","flange_type","FL_CL_LF_SE|FL_PN_PJ_SE|FL_PN_PJ_RJ",70,{"field":"lining_material","op":"in","value":["stainless","nickel","titanium","other"]},"衬里管道优先松套/焊环结构","E_P490","SOURCE_NORMALIZATION"),
    score("SC_FL_LINED_CLOSURE","flange_type","FL_PN_BL_S",35,{"all":[{"field":"closure_required","op":"eq","value":True},{"field":"lining_material","op":"in","value":["stainless","nickel","titanium","other"]}]},"衬里盲端优先衬里法兰盖","E_P035|E_P036","DETERMINISTIC_DERIVATION"),
    score("SC_FL_CYCLIC_WN","flange_type","FL_PN_WN|FL_CL_WN|FL_PN_IF|FL_CL_IF",60,{"any":[{"field":"severe_cyclic","op":"eq","value":True},{"field":"thermal_shock","op":"eq","value":True}]},"循环/热冲击优先高刚性结构","E_P250|E_P490","SOURCE_NORMALIZATION"),
    score("SC_FL_HIGH_HAZARD_WN","flange_type","FL_PN_WN|FL_CL_WN|FL_PN_IF|FL_CL_IF",45,{"any":[{"field":"toxicity","op":"in","value":["high","extreme"]},{"field":"flammability","op":"in","value":["flammable","highly_flammable"]},{"field":"leak_tightness","op":"in","value":["high","zero_emission"]}]},"高危或高密封要求优先刚性较高的对焊/整体法兰","E_P250|E_P490","ENGINEERING_NORMALIZATION"),
    score("SC_FACE_CAST_FF","facing","FACE_FF",80,{"any":[{"field":"flange_material_group","op":"eq","value":"cast_iron"},{"field":"mating_material_group","op":"eq","value":"cast_iron"}]},"铸铁接口优先FF","E_P491|E_P532","SOURCE_NORMALIZATION"),
    score("SC_FACE_INTERNAL_FM","facing","FACE_FM_M_PAIR",35,{"field":"internal_component_connection","op":"eq","value":True},"内部连接优先FM/M配对","E_P490","SOURCE_NORMALIZATION"),
    score("SC_G_LOW_GENERAL_NAF","gasket_type","G_NON_ASBESTOS_FIBER",48,{"all":[{"field":"utility_service","op":"eq","value":True},{"field":"toxicity","op":"in","value":["normal","moderate","unknown",None]},{"field":"vacuum_level","op":"in","value":["none","unknown",None]}]},"一般公用工程优先非石棉纤维橡胶板","E_P252|E_P492","ENGINEERING_NORMALIZATION"),
    score("SC_G_CORROSIVE_PTFE","gasket_type","G_MODIFIED_PTFE|G_PTFE_FLAT|G_PTFE_ENVELOPE_B",80,{"field":"corrosivity","op":"in","value":["moderate","high","severe"]},"腐蚀性工况优先PTFE类，仍须材料相容性确认","E_P252|E_P492","ENGINEERING_NORMALIZATION"),
    score("SC_G_HIGH_HAZARD_SPIRAL","gasket_type","G_SPIRAL_D|G_KAMMPROFILE_B|G_KAMMPROFILE_C",65,{"any":[{"field":"toxicity","op":"in","value":["high","extreme"]},{"field":"flammability","op":"in","value":["highly_flammable"]},{"field":"leak_tightness","op":"in","value":["high","zero_emission"]},{"field":"severe_cyclic","op":"eq","value":True}]},"高危、高密封或循环工况优先带定位/约束的半金属垫","E_P491|E_P492","ENGINEERING_NORMALIZATION"),
    score("SC_G_HIGH_TEMP_MICA","gasket_type","G_MICA_COMPOSITE",80,{"field":"temperature_c","op":"gt","value":650},"650~900℃范围优先云母复合垫；仍须核对压力和材料","E_P252|E_P492","DETERMINISTIC_DERIVATION"),
    score("SC_G_ENVELOPE_B_RECOMMENDED","gasket_type","G_PTFE_ENVELOPE_B",30,{"field":"dn_mm","op":"lte","value":500},"A/B均适用时标准说明推荐B型","E_P015|E_P162","SOURCE_NORMALIZATION"),
    score("SC_G_ENVELOPE_C_LARGE","gasket_type","G_PTFE_ENVELOPE_C",35,{"field":"dn_mm","op":"gte","value":350},"DN≥350可采用C型","E_P015|E_P162","SOURCE_NORMALIZATION"),
    score("SC_G_FLUSH_BORE_B","gasket_type","G_PTFE_ENVELOPE_B",45,{"field":"flush_bore_required","op":"eq","value":True},"机加工B型可加厚内径并利于与法兰内径齐平","E_P015|E_P162","SOURCE_NORMALIZATION"),
    score("SC_G_RF_SPIRAL_D","gasket_type","G_SPIRAL_D",35,{"field":"current_facing","op":"in","value":["RF","FF"]},"RF/FF时D型缠绕垫兼具内环和对中环","E_P178|E_P416","ENGINEERING_NORMALIZATION"),
    score("SC_G_FM_SPIRAL_B","gasket_type","G_SPIRAL_B",45,{"field":"current_facing","op":"eq","value":"FM/M"},"FM/M配B型带内环缠绕垫","E_P178|E_P416","SOURCE_NORMALIZATION"),
    score("SC_G_TG_SPIRAL_A","gasket_type","G_SPIRAL_A",45,{"field":"current_facing","op":"eq","value":"T/G"},"T/G配A型基本缠绕垫","E_P178|E_P416","SOURCE_NORMALIZATION"),
    score("SC_G_RJ_OCT","gasket_type","G_RING_OCTAGONAL",8,{"field":"ring_joint_required","op":"eq","value":True},"椭圆/八角均为标准型式；无环槽细节时以较高注册优先级唯一收敛，须复核环号","E_P202|E_P446","ENGINEERING_NORMALIZATION"),
    score("SC_FST_LOW_BENIGN_HEX","fastener_type","FST_PN_HEX_I|FST_CL_HEX_I",60,{"all":[{"field":"severe_cyclic","op":"eq","value":False},{"field":"thermal_shock","op":"eq","value":False},{"field":"toxicity","op":"in","value":["normal","moderate"]}]},"有来源事实确认低等级、非严重循环时可用六角头螺栓组件；未知条件不触发","E_P254|E_P493","ENGINEERING_NORMALIZATION"),
    score("SC_FST_SEVERE_FULL","fastener_type","FST_PN_FULL_II|FST_CL_FULL_HH",70,{"any":[{"field":"severe_cyclic","op":"eq","value":True},{"field":"thermal_shock","op":"eq","value":True},{"field":"temperature_c","op":"gt","value":200}]},"高温、循环或热冲击优先全螺纹螺柱","E_P254|E_P493|E_P494","ENGINEERING_NORMALIZATION"),
]


WARNINGS = [
    ("W_DEFAULTED","未获得足够的区分条件，已选注册的最泛用默认型式；结果为暂定，补齐最小缺失字段后重算。"),
    ("W_INCOMPLETE_CONTEXT","已有条件触发了选型规则，但仍缺少部分必要工况证据；结果为暂定，按最小缺失字段补齐后重算。"),
    ("W_RATING_MISSING","缺少PN或Class额定等级；操作压力不能单独替代材料—温度条件下的额定等级核定。"),
    ("W_SCOPE_MISMATCH","所选类型的标准表列范围与输入存在冲突；类型仅作保底，不得据此生成标准尺寸或宣称符合标准。"),
    ("W_MATERIAL_PT","温度能力受具体材料、填充层和法兰材料p-T曲线限制，必须在材料确定后复核。"),
    ("W_VENDOR_SPECIAL","特殊、超范围、零逸散、防火或卫生工况需项目规范及供应商/试验确认。"),
    ("W_FIRE_CLEAN","本标准类型表不足以证明防火或可清洗/卫生性能；已保留类型推荐但必须补专项验证。"),
    ("W_ASBESTOS","含石棉材料受现行法律、健康和项目禁限用要求约束，程序不会将其作为默认。"),
    ("W_CHLORIDE","石棉或柔性石墨用于不锈钢/镍基合金法兰时，垫片材料氯离子含量不得超过标准条款限值。"),
    ("W_FLUSH_BORE","要求内径齐平时，应提供法兰内径并在订货时明确；程序类型选择不能替代制造尺寸确认。"),
    ("W_FORCED_REJECTED","用户强制候选触发硬排除，程序已拒绝并改选未被排除的唯一候选。"),
    ("W_COMPAT_CONFLICT","多个必需兼容条件相互冲突；程序按优先级保留更高优先级条件并报警。"),
    ("W_ERRATA_APPLIED","已采用2012年5月后发布勘误：A/B/C、PN40、LWN、NPT及Class300修正。"),
]


LOGICAL_GROUPS = [
    ("LG_COMMENTARY_GASKET_TYPES","编制说明表2-1",14,14,"E_P014","CLOSED","表在第14页结束；第15页进入结构说明"),
    ("LG_PN_FLANGE_SELECTION","HG/T 20614表3.0.1",250,251,"E_P250|E_P251","CLOSED","第251页表结束；第252页进入3.0.2"),
    ("LG_PN_GASKET_SELECTION","HG/T 20614表3.0.2",252,253,"E_P252|E_P253","CLOSED","第253页表结束并进入3.0.3"),
    ("LG_PN_FASTENER_1","HG/T 20614表3.0.3-1",254,254,"E_P254","CLOSED","单页闭合"),
    ("LG_PN_FASTENER_2","HG/T 20614表3.0.3-2",254,255,"E_P254|E_P255","CLOSED","第255页表结束并进入3.0.4"),
    ("LG_PN_ANNEX_GASKET","HG/T 20614表A.0.3",256,256,"E_P256","CLOSED","单页闭合；第257页进入曲线和A/B/C说明"),
    ("LG_CLASS_FLANGE_SELECTION","HG/T 20635表3.1.1",490,490,"E_P490","CLOSED","单页闭合"),
    ("LG_CLASS_GASKET_SELECTION","HG/T 20635表3.2.11",492,492,"E_P492","CLOSED","单页闭合"),
    ("LG_CLASS_FASTENER_TYPES","HG/T 20635表3.3.1",493,493,"E_P493","CLOSED","单页闭合"),
    ("LG_CLASS_FASTENER_MATERIAL","HG/T 20635表3.3.10",494,494,"E_P494","CLOSED","单页闭合"),
    ("LG_CLASS_ANNEX_GASKET","HG/T 20635表A.0.3",495,495,"E_P495","CLOSED","单页闭合；第496页进入曲线和A/B/C说明"),
    ("LG_LATER_ERRATA","2012年5月勘误关键链",531,532,"E_P531|E_P532","CLOSED","只采用后发布勘误，旧勘误页不作为当前规则"),
]


TESTS = [
    {"test_id":"T01","input":{"object_family":"flange_type","system_series":"CLASS","utility_service":True,"low_sealing_demand":True,"flammability":"nonflammable","temperature_c":100,"class_rating":150,"dn_mm":100},"expected":"FL_CL_SO"},
    {"test_id":"T02","input":{"object_family":"flange_type","system_series":"CLASS","instrument_service":True,"class_rating":150,"dn_mm":25,"corrosivity":"low"},"expected":"FL_CL_TH"},
    {"test_id":"T03","input":{"object_family":"flange_type","system_series":"CLASS","severe_cyclic":True,"class_rating":600,"dn_mm":200,"flammability":"flammable"},"expected":"FL_CL_WN"},
    {"test_id":"T04","input":{"object_family":"flange_type","system_series":"CLASS","lining_material":"titanium","class_rating":300,"dn_mm":150},"expected":"FL_CL_LF_SE"},
    {"test_id":"T05","input":{"object_family":"flange_type","system_series":"CLASS","orifice_service":True,"pressure_tap_connection":"NPT","class_rating":600,"dn_mm":100},"expected":"FL_CL_KWN_T"},
    {"test_id":"T06","input":{"object_family":"flange_type","system_series":"PN","orifice_service":True,"pressure_tap_connection":"socket_weld","pn":40,"dn_mm":80},"expected":"FL_PN_KWN_S"},
    {"test_id":"T07","input":{"object_family":"flange_type","system_series":"PN","jacketed_pipe":True,"pn":25,"dn_mm":100,"severe_cyclic":True},"expected":"FL_PN_JWN"},
    {"test_id":"T08","input":{"object_family":"flange_type","system_series":"PN","closure_required":True,"lining_material":"stainless"},"expected":"FL_PN_BL_S"},
    {"test_id":"T09","input":{"object_family":"flange_type","system_series":"PN"},"expected":"FL_PN_WN","status_contains":"PROVISIONAL"},
    {"test_id":"T10","input":{"object_family":"flange_type","system_series":"CLASS","corrosivity":"severe","instrument_service":True,"class_rating":150,"dn_mm":25},"expected":"FL_CL_WN","excluded_contains":"FL_CL_TH"},
    {"test_id":"T11","input":{"object_family":"facing","system_series":"CLASS","flange_material_group":"steel","mating_material_group":"cast_iron","class_rating":300},"expected":"FACE_FF"},
    {"test_id":"T12","input":{"object_family":"facing","system_series":"PN","ring_joint_required":True},"expected":"FACE_RJ"},
    {"test_id":"T13","input":{"object_family":"facing","system_series":"CLASS","internal_component_connection":True},"expected":"FACE_FM_M_PAIR"},
    {"test_id":"T14","input":{"object_family":"facing","system_series":"CLASS"},"expected":"FACE_RF","status_contains":"PROVISIONAL"},
    {"test_id":"T15","input":{"object_family":"gasket_type","system_series":"PN","utility_service":True,"toxicity":"normal","vacuum_level":"none","pn":16,"temperature_c":120},"expected":"G_NON_ASBESTOS_FIBER"},
    {"test_id":"T16","input":{"object_family":"gasket_type","system_series":"CLASS","corrosivity":"high","class_rating":300,"temperature_c":150,"current_facing":"RF"},"expected":"G_MODIFIED_PTFE"},
    {"test_id":"T17","input":{"object_family":"gasket_type","system_series":"PN","gasket_family_preference":"ptfe_envelope","dn_mm":200,"vacuum_level":"none","core_corrosion_risk":False,"pn":25},"expected":"G_PTFE_ENVELOPE_B"},
    {"test_id":"T18","input":{"object_family":"gasket_type","system_series":"PN","gasket_family_preference":"ptfe_envelope","dn_mm":550,"vacuum_level":"none","core_corrosion_risk":False,"pn":25},"expected":"G_PTFE_ENVELOPE_C"},
    {"test_id":"T19","input":{"object_family":"gasket_type","system_series":"PN","gasket_family_preference":"ptfe_envelope","dn_mm":300,"vacuum_level":"vacuum","corrosivity":"high","pn":16},"expected":"G_MODIFIED_PTFE","excluded_contains":"G_PTFE_ENVELOPE_B"},
    {"test_id":"T20","input":{"object_family":"gasket_type","system_series":"CLASS","temperature_c":800,"oxidizing":False,"class_rating":300,"current_facing":"RF"},"expected":"G_MICA_COMPOSITE"},
    {"test_id":"T21","input":{"object_family":"gasket_type","system_series":"CLASS","temperature_c":500,"oxidizing":True,"class_rating":300,"current_facing":"RF","toxicity":"high"},"expected":"G_SPIRAL_D","excluded_contains":"G_FLEX_GRAPHITE_REINFORCED"},
    {"test_id":"T22","input":{"object_family":"gasket_type","system_series":"CLASS","toxicity":"extreme","leak_tightness":"high","class_rating":600,"current_facing":"RF"},"expected":"G_SPIRAL_D"},
    {"test_id":"T23","input":{"object_family":"gasket_type","system_series":"CLASS","ring_joint_required":True,"current_facing":"RJ","class_rating":900,"dn_mm":100},"expected":"G_RING_OCTAGONAL"},
    {"test_id":"T24","input":{"object_family":"gasket_type","system_series":"PN","current_facing":"FM/M","gasket_family_preference":"spiral_wound","pn":63},"expected":"G_SPIRAL_B"},
    {"test_id":"T25","input":{"object_family":"gasket_type","system_series":"PN","current_facing":"T/G","gasket_family_preference":"spiral_wound","pn":63},"expected":"G_SPIRAL_A"},
    {"test_id":"T26","input":{"object_family":"gasket_type","system_series":"PN"},"expected":"G_SPIRAL_D","status_contains":"PROVISIONAL"},
    {"test_id":"T27","input":{"object_family":"gasket_type","system_series":"CLASS","fire_safe_required":True,"cleanability_required":True},"expected":"G_SPIRAL_D","warning_contains":"W_FIRE_CLEAN"},
    {"test_id":"T28","input":{"object_family":"gasket_type","system_series":"CLASS","user_forced_candidate_id":"G_PTFE_ENVELOPE_B","vacuum_level":"high_vacuum","toxicity":"high","current_facing":"RF"},"expected":"G_SPIRAL_D","warning_contains":"W_FORCED_REJECTED"},
    {"test_id":"T29","input":{"object_family":"fastener_type","system_series":"CLASS","class_rating":150,"severe_cyclic":False,"thermal_shock":False,"toxicity":"normal","temperature_c":80},"expected":"FST_CL_HEX_I"},
    {"test_id":"T30","input":{"object_family":"fastener_type","system_series":"CLASS","class_rating":600,"severe_cyclic":True,"temperature_c":300},"expected":"FST_CL_FULL_HH"},
    {"test_id":"T31","input":{"object_family":"fastener_type","system_series":"PN","pn":40,"severe_cyclic":False,"thermal_shock":False,"toxicity":"normal","temperature_c":80},"expected":"FST_PN_HEX_I"},
    {"test_id":"T32","input":{"object_family":"fastener_type","system_series":"PN","pn":63,"temperature_c":250},"expected":"FST_PN_FULL_II"},
    {"test_id":"T33","input":{"object_family":"fastener_type","system_series":"PN"},"expected":"FST_PN_FULL_II","status_contains":"PROVISIONAL"},
    {"test_id":"T34","input":{"object_family":"facing","system_series":"CLASS","ring_joint_required":True,"mating_material_group":"cast_iron"},"expected":"FACE_RJ","warning_contains":"W_COMPAT_CONFLICT"},
    {"test_id":"T35","input":{"object_family":"gasket_type","system_series":"PN","temperature_c":1200,"pn":250,"dn_mm":2500},"expected":"G_SPIRAL_D","warning_contains":"W_SCOPE_MISMATCH"},
    {"test_id":"T36","input":{"object_family":"flange_type","system_series":"CLASS","pressure_value":10,"pressure_unit":"bar","severe_cyclic":True},"expected":"FL_CL_WN","status_contains":"PROVISIONAL"},
]


def build():
    if not RAW_PAGES.exists():
        raise FileNotFoundError(f"required source layer missing: {RAW_PAGES}")
    pages = load_pages()
    if any(pages[p]["source_pdf_sha256"] != PDF_SHA256 for p in EVIDENCE_PAGES):
        raise RuntimeError("source PDF hash mismatch")

    write_csv("source_records.csv", source_records(pages))
    write_csv("type_catalog.csv", CATALOG)
    cap_rows = build_capabilities()
    write_csv("candidate_capabilities.csv", cap_rows)
    write_csv(
        "condition_registry.csv",
        [{"field_name":a,"data_type":b,"unit":c,"allowed_values":d,"field_role":"DERIVED_OUTPUT_ONLY" if a in DERIVED_OUTPUT_FIELDS else "RAW_INPUT","normalization_note":e,"annotation_class":"ENGINEERING_NORMALIZATION"} for a,b,c,d,e in CONDITION_REGISTRY],
    )
    write_csv("service_label_derivation.csv", SERVICE_LABEL_DERIVATION)
    write_csv("hard_exclusions.csv", HARD_EXCLUSIONS)
    write_csv("compatibility_matrix.csv", COMPATIBILITY)
    write_csv("selection_rules.csv", SELECTION_RULES)
    write_csv(
        "tie_default_priority.csv",
        [{"candidate_id":r["candidate_id"],"object_family":r["object_family"],"system_series":r["system_series"],"default_priority":r["default_priority"],"policy_note":"仅在硬排除和必需兼容之后用于唯一收敛；不是标准原文默认值","annotation_class":"DETERMINISTIC_POLICY"} for r in CATALOG if r["terminal_selectable"] == "true"],
    )
    write_csv("warning_templates.csv", [{"warning_id":a,"message_zh":b} for a,b in WARNINGS])
    write_csv(
        "logical_table_grouping_manifest.csv",
        [{"group_id":a,"title":b,"start_page":c,"end_page":d,"source_refs":e,"closure_status":f,"closure_note":g} for a,b,c,d,e,f,g in LOGICAL_GROUPS],
    )
    relations = []
    for filename, records, id_field in [
        ("type_catalog.csv", CATALOG, "candidate_id"),
        ("candidate_capabilities.csv", cap_rows, "candidate_id"),
        ("hard_exclusions.csv", HARD_EXCLUSIONS, "rule_id"),
        ("compatibility_matrix.csv", COMPATIBILITY, "rule_id"),
        ("selection_rules.csv", SELECTION_RULES, "rule_id"),
    ]:
        for record in records:
            for ref in record.get("source_refs", "").split("|"):
                if ref:
                    relations.append({"target_file":filename,"target_id":record[id_field],"relation":"SUPPORTED_BY","evidence_id":ref})
    write_csv("source_relations.csv", relations)
    # Test authoring constants above remain compact, but emitted fixtures obey
    # the public contract: service labels are carried as source-bearing graph
    # facts, never as direct user fields.
    emitted_tests = []
    for test in TESTS:
        test = json.loads(json.dumps(test, ensure_ascii=False))
        data = test["input"]
        property_evidence = list(data.get("property_evidence", []))
        if "temperature_c" in data:
            data["temperature_value"] = data.pop("temperature_c")
            data["temperature_unit"] = "C"
        for key in sorted(DERIVED_OUTPUT_FIELDS):
            if key in data:
                property_evidence.append({"fact":key,"value":data.pop(key),"source_id":f"TEST_FIXTURE:{test['test_id']}:{key}"})
        if property_evidence:
            data["property_evidence"] = property_evidence
        emitted_tests.append(test)
    write_json("test_cases.json", emitted_tests)
    write_json(
        "input_schema.json",
        {
            "$schema":"https://json-schema.org/draft/2020-12/schema",
            "title":"HG/T 20592~20635 deterministic type-selection input",
            "type":"object",
            "required":["object_family"],
            "properties":{
                row[0]: (
                    {"type":["number","null"]} if row[1] == "number" else
                    {"type":["boolean","string","null"]} if row[1] == "boolean" else
                    {"type":["array","null"],"items":{"type":"object"}} if row[1] == "array[object]" else
                    {"type":["array","null"],"items":{"type":"string"}} if row[1].startswith("array") else
                    {"type":["string","null"]}
                )
                for row in CONDITION_REGISTRY if row[0] not in DERIVED_OUTPUT_FIELDS
            },
            "additionalProperties":False,
            "x-evidence-layer-note":"原始字段与工程归一化字段分层；外部模型只能补候选/解释，不能绕过硬排除或改写程序结果。",
        },
    )
    write_json(
        "package_metadata.json",
        {
            "package_version":PACKAGE_VERSION,
            "source_pdf_sha256":PDF_SHA256,
            "source_document":"HG/T 20592~20635-2009（含编制说明和后发布勘误）",
            "scope":"法兰型式、密封面、垫片型式、紧固件组件的确定性唯一终端选型",
            "runtime_vision":False,
            "runtime_source_access":False,
            "errata_policy":"2012-05 later errata overrides earlier base text and obsolete errata",
            "evidence_layers":["SOURCE_RAW_TEXT","SOURCE_NORMALIZATION","DETERMINISTIC_DERIVATION","ENGINEERING_NORMALIZATION","DETERMINISTIC_POLICY"],
            "known_boundary":"不替代材料p-T曲线、泄漏等级、耐火/卫生认证、供应商特殊工况确认或法兰尺寸表全量数字化",
        },
    )

    manifest_rows = []
    excluded_dirs = {"audit_page_renders", "tmp", "__pycache__"}
    for path in sorted(ROOT.rglob("*"), key=lambda p: p.as_posix()):
        if not path.is_file() or path.name == "hash_manifest.csv":
            continue
        if any(part in excluded_dirs for part in path.relative_to(ROOT).parts):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        manifest_rows.append({"relative_path":path.relative_to(ROOT).as_posix(),"sha256":digest,"size_bytes":path.stat().st_size})
    write_csv("hash_manifest.csv", manifest_rows)


if __name__ == "__main__":
    build()
