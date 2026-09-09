#!/usr/bin/env python3
"""Formula-audit GB/T 17395 theoretical-weight tables without overwriting OCR evidence."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path


PI = 3.1416
DENSITY_KG_DM3 = 7.85


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def write_csv(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)


def write_dict_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def first_number(text: str) -> float | None:
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)", text.replace(",", "."))
    return float(match.group(1)) if match else None


def exact_number(text: str) -> float | None:
    text = text.strip().replace(",", ".")
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return None
    return float(text)


def theoretical_weight(diameter_mm: float, thickness_mm: float) -> float:
    return PI * DENSITY_KG_DM3 * (diameter_mm - thickness_mm) * thickness_mm / 1000.0


def infer_thickness(row: list[str], diameters: dict[int, float]) -> tuple[float | None, str]:
    for cell in row[:4]:
        value = first_number(cell)
        if value is not None and 0.05 <= value <= 100:
            return value, "ocr_row_header"
    inferred: list[float] = []
    for column, diameter in diameters.items():
        if column >= len(row):
            continue
        weight = exact_number(row[column])
        if weight is None or weight <= 0:
            continue
        term = weight * 1000.0 / (PI * DENSITY_KG_DM3)
        discriminant = diameter * diameter - 4.0 * term
        if discriminant <= 0:
            continue
        thickness = (diameter - math.sqrt(discriminant)) / 2.0
        if 0.05 <= thickness < diameter / 2:
            inferred.append(thickness)
    if len(inferred) < 3:
        return None, "unresolved"
    median = statistics.median(inferred)
    quantized = round(median * 20.0) / 20.0
    if abs(quantized - median) > 0.08:
        quantized = round(median, 2)
    return quantized, "formula_inferred_from_row_weights"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    graph_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--package", type=Path, default=graph_root / "source_layer" / "documents" / "std_gb_t_17395_2024")
    args = parser.parse_args()
    package = args.package.resolve()
    status = json.loads((package / "status.json").read_text(encoding="utf-8"))
    if status.get("doc_id") != "std_gb_t_17395_2024":
        raise ValueError("this validator only accepts std_gb_t_17395_2024")

    tables = read_jsonl(package / "tables.jsonl")
    output_root = package / "derived" / "gbt17395_weight_formula_audit"
    audits: list[dict] = []
    table_summaries: list[dict] = []
    processed = 0
    for table in tables:
        page = int(table["page_1based"])
        if not (8 <= page <= 34) or table.get("dot_matrix") or int(table.get("row_count", 0)) * int(table.get("column_count", 0)) < 100:
            continue
        rows = read_csv(package / table["csv_path"])
        width = max((len(row) for row in rows), default=0)
        rows = [row + [""] * (width - len(row)) for row in rows]
        series_rows = [index for index, row in enumerate(rows) if "系列" in re.sub(r"\s+", "", " ".join(row))]
        if not series_rows:
            diameter_header_rows = [
                index
                for index, row in enumerate(rows)
                if "(D)/mm" in re.sub(r"\s+", "", " ".join(row))
                or ("公称外径" in re.sub(r"\s+", "", " ".join(row)))
            ]
            series_rows = diameter_header_rows[-1:] if diameter_header_rows else []
        if not series_rows:
            continue
        first_series = min(series_rows)
        diameters: dict[int, float] = {}
        for column in range(3, width):
            for row_index in sorted(series_rows, reverse=True):
                value = first_number(rows[row_index][column])
                if value is not None:
                    diameters[column] = value
                    break
        if len(diameters) < 4:
            continue

        reconstructed = [list(row) for row in rows]
        table_audits: list[dict] = []
        resolved_rows = 0
        for row_index in range(first_series):
            thickness, thickness_source = infer_thickness(rows[row_index], diameters)
            if thickness is None:
                continue
            resolved_rows += 1
            for column, diameter in diameters.items():
                if column >= width or diameter <= 2 * thickness:
                    continue
                calculated = theoretical_weight(diameter, thickness)
                calculated_text = f"{calculated:.3f}"
                raw = rows[row_index][column].strip()
                extracted = exact_number(raw)
                difference = abs(extracted - calculated) if extracted is not None else None
                qa_status = "matches_formula_rounding" if difference is not None and difference <= 0.006 else ("ocr_value_disagrees" if extracted is not None else "ocr_missing_or_unparseable")
                reconstructed[row_index][column] = calculated_text
                table_audits.append(
                    {
                        "table_id": table["table_id"],
                        "page_1based": page,
                        "row": row_index + 1,
                        "column": column + 1,
                        "diameter_mm": f"{diameter:g}",
                        "thickness_mm": f"{thickness:g}",
                        "thickness_source": thickness_source,
                        "raw_ocr_value": raw,
                        "formula_value_kg_per_m": calculated_text,
                        "absolute_difference": "" if difference is None else f"{difference:.6f}",
                        "qa_status": qa_status,
                        "formula": "W=pi*rho*(D-S)*S/1000",
                        "pi": PI,
                        "rho_kg_per_dm3": DENSITY_KG_DM3,
                        "source_pdf_sha256": status["source_pdf_sha256"],
                    }
                )
        if not table_audits:
            continue
        stem = Path(table["csv_path"]).stem
        write_csv(output_root / f"{stem}_formula_reconstruction.csv", reconstructed)
        write_dict_csv(output_root / f"{stem}_formula_audit.csv", table_audits)
        audits.extend(table_audits)
        table_summaries.append(
            {
                "table_id": table["table_id"],
                "page_1based": page,
                "bbox_pt": table.get("bbox_pt", [0, 0, 0, 0]),
                "resolved_thickness_rows": resolved_rows,
                "audited_cells": len(table_audits),
                "matches": sum(row["qa_status"] == "matches_formula_rounding" for row in table_audits),
                "ocr_disagrees": sum(row["qa_status"] == "ocr_value_disagrees" for row in table_audits),
                "ocr_missing": sum(row["qa_status"] == "ocr_missing_or_unparseable" for row in table_audits),
                "reconstruction_csv": f"{stem}_formula_reconstruction.csv",
                "audit_csv": f"{stem}_formula_audit.csv",
            }
        )
        processed += 1

    write_dict_csv(output_root / "all_formula_audit.csv", audits)
    write_dict_csv(output_root / "table_formula_audit_summary.csv", table_summaries)
    derived_assets = [
        {
            "table_id": f"{row['table_id']}:formula_audit",
            "doc_id": status["doc_id"],
            "page_id": f"{status['doc_id']}:p{int(row['page_1based']):04d}",
            "page_1based": int(row["page_1based"]),
            "table_order": 900,
            "method": "deterministic_formula_audit",
            "structure_confidence": 1.0,
            "bbox_pt": row.get("bbox_pt", [0, 0, 0, 0]),
            "caption": "GB/T 17395 理论重量公式复核 W=πρ(D-S)S/1000；复算值不是标准表转录",
            "row_count": int(row["audited_cells"]),
            "column_count": 15,
            "nonempty_cells": int(row["audited_cells"]),
            "key_table": True,
            "csv_path": f"derived/gbt17395_weight_formula_audit/{row['audit_csv']}",
            "cell_audit_csv_path": f"derived/gbt17395_weight_formula_audit/{row['audit_csv']}",
            "source_pdf_sha256": status["source_pdf_sha256"],
            "structure_mode": "deterministic_formula_audit",
            "numeric_reuse_allowed": False,
            "geometry_preserved": True,
            "common_spec_cells": 0,
            "dot_matrix": False,
            "asset_label": "formula_audit",
            "asset_qa_status": "method_only_not_standard_transcription",
            "structure_override": False,
        }
        for row in table_summaries
    ]
    with (package / "derived_assets.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in derived_assets:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = {
        "schema": "gbt17395-weight-formula-audit-v1",
        "status": "PASS_WITH_REVIEW" if any(row["ocr_disagrees"] or row["ocr_missing"] for row in table_summaries) else "PASS",
        "doc_id": status["doc_id"],
        "source_pdf_sha256": status["source_pdf_sha256"],
        "formula": "W = pi * rho * (D - S) * S / 1000",
        "constants": {"pi": PI, "rho_kg_per_dm3": DENSITY_KG_DM3},
        "evidence_class": "deterministic_derivation_for_OCR_QA_not_standard_table_transcription",
        "processed_tables": processed,
        "audited_cells": len(audits),
        "matches": sum(row["qa_status"] == "matches_formula_rounding" for row in audits),
        "ocr_disagrees": sum(row["qa_status"] == "ocr_value_disagrees" for row in audits),
        "ocr_missing": sum(row["qa_status"] == "ocr_missing_or_unparseable" for row in audits),
        "tables": table_summaries,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
