#!/usr/bin/env python3
"""Promote a re-extracted legacy standard to a bounded recovery status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc_id")
    parser.add_argument("--graph-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    source_layer = args.graph_root.resolve() / "source_layer"
    status_path = source_layer / "documents" / args.doc_id / "status.json"
    override_path = source_layer / "overrides" / f"{args.doc_id}.json"
    quality_path = source_layer / "recovered" / args.doc_id / "content_stream_gbk_quality.json"
    for path in (status_path, override_path, quality_path):
        if not path.is_file():
            raise SystemExit(f"missing required file: {path}")

    status = load_json(status_path)
    override = load_json(override_path)
    quality = load_json(quality_path)
    if {status.get("doc_id"), override.get("doc_id"), quality.get("doc_id")} != {args.doc_id}:
        raise SystemExit("doc_id mismatch across status/override/recovery")
    hashes = {
        status.get("source_pdf_sha256"),
        override.get("source_pdf_sha256"),
        quality.get("source_pdf_sha256"),
    }
    if len(hashes) != 1 or None in hashes:
        raise SystemExit("source SHA-256 mismatch across status/override/recovery")
    if int(status.get("page_count", -1)) != int(override.get("page_count", -2)):
        raise SystemExit("page count mismatch between status and override")
    expected = override.get("expected_counts", {})
    observed = {"tables": int(status.get("table_count", -1)), "figures": int(status.get("figure_count", -1))}
    if observed != {"tables": int(expected.get("tables", -2)), "figures": int(expected.get("figures", -2))}:
        raise SystemExit(f"structure counts do not match: expected={expected} observed={observed}")
    if status.get("structure_count_mismatches"):
        raise SystemExit("extractor reported structure count mismatches")
    if quality.get("status") != "RECOVERED_WITH_LAYOUT_LIMITS":
        raise SystemExit(f"unexpected recovery status: {quality.get('status')!r}")
    if quality.get("coordinate_boundary", {}).get("status") != "UNRESOLVED":
        raise SystemExit("glyph coordinate boundary must remain unresolved")

    override["package_status_override"] = "RECOVERED_WITH_LAYOUT_LIMITS"
    override["authority_note"] = (
        f"{observed['tables']}-table/{observed['figures']}-XObject structure was re-extracted and count-validated; "
        "GB18030 text recovery is page-level only, so automatic quotation and numeric reuse remain quarantined."
    )
    override_path.write_text(json.dumps(override, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "doc_id": args.doc_id,
        "status": override["package_status_override"],
        "source_pdf_sha256": next(iter(hashes)),
        "page_count": status["page_count"],
        "tables": observed["tables"],
        "figures": observed["figures"],
        "location_status": "page_level_only_no_glyph_bbox",
        "override": str(override_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
