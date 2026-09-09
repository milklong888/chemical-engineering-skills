#!/usr/bin/env python3
"""Build a fail-closed whole-source digitisation dispatch ledger."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


FIELDS = [
    "queue_rank",
    "source_id",
    "standard_id",
    "canonical_relative_path",
    "formal_unresolved_key_tables",
    "formal_unresolved_figures",
    "formal_unresolved_total",
    "supplemental_unresolved_key_tables",
    "supplemental_unresolved_figures",
    "supplemental_unresolved_total",
    "effective_unresolved_total",
    "model_gate_status",
    "assignee",
    "clearance_status",
    "closure_rule",
]


def build_clearance_rows(
    queue: list[dict[str, str]], *, assignments: dict[str, str],
    model_gates: dict[str, str],
    supplemental_obligations: dict[str, tuple[int, int]],
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    known_sources = {row["source_id"] for row in queue}
    unknown_assignments = sorted(set(assignments) - known_sources)
    if unknown_assignments:
        raise ValueError(f"assignments not present in formal queue: {unknown_assignments}")
    unknown_model_gates = sorted(set(model_gates) - known_sources)
    if unknown_model_gates:
        raise ValueError(f"model gates not present in formal queue: {unknown_model_gates}")
    unknown_supplemental = sorted(set(supplemental_obligations) - known_sources)
    if unknown_supplemental:
        raise ValueError(
            f"supplemental obligations not present in formal queue: {unknown_supplemental}"
        )
    invalid_model_gates = {
        source_id: status for source_id, status in model_gates.items()
        if status not in {"PASS", "FAIL", "NOT_ASSESSED"}
    }
    if invalid_model_gates:
        raise ValueError(f"invalid model gates: {invalid_model_gates}")
    for source in queue:
        tables = int(source["unresolved_key_table_count"])
        figures = int(source["unresolved_figure_count"])
        total = int(source["unresolved_total"])
        if tables < 0 or figures < 0 or total != tables + figures:
            raise ValueError(f"inconsistent formal counts for {source['source_id']}")
        supplemental_tables, supplemental_figures = supplemental_obligations.get(
            source["source_id"], (0, 0)
        )
        if supplemental_tables < 0 or supplemental_figures < 0:
            raise ValueError(
                f"negative supplemental counts for {source['source_id']}"
            )
        supplemental_total = supplemental_tables + supplemental_figures
        effective_total = total + supplemental_total
        assignee = assignments.get(source["source_id"], "")
        model_gate = model_gates.get(source["source_id"], "NOT_ASSESSED")
        if effective_total == 0 and model_gate == "PASS":
            status = "FORMAL_CLOSED"
        elif effective_total == 0:
            status = "MODEL_GATE_PENDING"
        elif assignee:
            status = "IN_PROGRESS"
        else:
            status = "PENDING"
        rows.append({
            "queue_rank": int(source["queue_rank"]),
            "source_id": source["source_id"],
            "standard_id": source["standard_id"],
            "canonical_relative_path": source["canonical_relative_path"],
            "formal_unresolved_key_tables": tables,
            "formal_unresolved_figures": figures,
            "formal_unresolved_total": total,
            "supplemental_unresolved_key_tables": supplemental_tables,
            "supplemental_unresolved_figures": supplemental_figures,
            "supplemental_unresolved_total": supplemental_total,
            "effective_unresolved_total": effective_total,
            "model_gate_status": model_gate,
            "assignee": assignee,
            "clearance_status": status,
            "closure_rule": "FORMAL_COUNTS_ZERO_AND_QUANT_MODEL_GATE_PASS",
        })
    return rows


def read_queue(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_assignments(values: list[str]) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for value in values:
        source_id, separator, assignee = value.partition("=")
        if not separator or not source_id.strip() or not assignee.strip():
            raise ValueError(f"assignment must be source_id=assignee: {value}")
        assignments[source_id.strip()] = assignee.strip()
    return assignments


def parse_supplemental_obligations(
    values: list[str],
) -> dict[str, tuple[int, int]]:
    obligations: dict[str, tuple[int, int]] = {}
    for value in values:
        source_id, separator, counts = value.partition("=")
        tables_text, comma, figures_text = counts.partition(",")
        if not separator or not comma or not source_id.strip():
            raise ValueError(
                f"supplemental obligation must be source_id=tables,figures: {value}"
            )
        tables = int(tables_text.strip())
        figures = int(figures_text.strip())
        if tables < 0 or figures < 0:
            raise ValueError(f"supplemental counts must be nonnegative: {value}")
        obligations[source_id.strip()] = (tables, figures)
    return obligations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--assign", action="append", default=[])
    parser.add_argument("--model-gate", action="append", default=[])
    parser.add_argument("--supplemental", action="append", default=[])
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument("--out-summary", type=Path, required=True)
    args = parser.parse_args()
    rows = build_clearance_rows(
        read_queue(args.queue.resolve()),
        assignments=parse_assignments(args.assign),
        model_gates={
            source_id: status.upper()
            for source_id, status in parse_assignments(args.model_gate).items()
        },
        supplemental_obligations=parse_supplemental_obligations(args.supplemental),
    )
    output = args.out_csv.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "schema": "full-source-digitization-clearance-ledger-v3",
        "source_count": len(rows),
        "status_counts": dict(sorted(Counter(row["clearance_status"] for row in rows).items())),
        "formal_unresolved_key_tables": sum(int(row["formal_unresolved_key_tables"]) for row in rows),
        "formal_unresolved_figures": sum(int(row["formal_unresolved_figures"]) for row in rows),
        "formal_unresolved_total": sum(int(row["formal_unresolved_total"]) for row in rows),
        "supplemental_unresolved_key_tables": sum(int(row["supplemental_unresolved_key_tables"]) for row in rows),
        "supplemental_unresolved_figures": sum(int(row["supplemental_unresolved_figures"]) for row in rows),
        "supplemental_unresolved_total": sum(int(row["supplemental_unresolved_total"]) for row in rows),
        "effective_unresolved_total": sum(int(row["effective_unresolved_total"]) for row in rows),
        "model_gate_status_counts": dict(sorted(Counter(row["model_gate_status"] for row in rows).items())),
        "acceptance": "PASS" if all(row["clearance_status"] == "FORMAL_CLOSED" for row in rows) else "FAIL",
        "closure_rule": "CANDIDATES_DO_NOT_REDUCE_FORMAL_COUNTS_AND_MODEL_GATE_MUST_PASS",
    }
    summary_path = args.out_summary.resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
