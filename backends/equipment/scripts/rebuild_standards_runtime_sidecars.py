#!/usr/bin/env python3
"""Rebuild compact, auditable sidecars from the standards SQLite carrier.

The SQLite database remains the authority carrier.  These generated files make
its searchable grain, evidence boundary, and known metadata discrepancies
visible to the runtime bundle without copying source PDFs or render assets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable


CATALOG_COLUMNS = (
    "chunk_id",
    "doc_id",
    "chunk_order",
    "relative_path",
    "source_pdf_sha256",
    "family",
    "source_kind",
    "evidence_default",
    "page_start",
    "page_end",
    "section_path",
    "extraction_methods",
    "quality_score",
    "char_count",
    "text_sha256",
    "location_status",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _atomic_replace_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def _atomic_write_catalog(path: Path, rows: Iterable[tuple[Any, ...]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8-sig",
        newline="",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
        suffix=".tmp",
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CATALOG_COLUMNS)
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
        temporary = Path(handle.name)
    temporary.replace(path)
    return count


def _query_rows(connection: sqlite3.Connection, sql: str) -> list[tuple[Any, ...]]:
    return list(connection.execute(sql))


def _progress(message: str) -> None:
    print(f"[standards-sidecars] {message}", file=sys.stderr, flush=True)


def _render_crosswalk(report: dict[str, Any]) -> str:
    family_rows = "\n".join(
        f"| {family} | {document_count} | {chunk_count} |"
        for family, document_count, chunk_count in report["family_counts"]
    )
    mismatch_rows = "\n".join(
        "| {doc_id} | {declared} | {actual} | {duplicate_of} | {status} |".format(
            doc_id=item["doc_id"],
            declared=item["declared_chunk_count"],
            actual=item["actual_chunk_count"],
            duplicate_of=item["duplicate_of"] or "—",
            status=item["package_status"],
        )
        for item in report["document_chunk_count_mismatches"]
    )
    return f"""# 标准参数与运行时证据交叉表

## 1. 权威载体

- 数据库：`source_layer/indexes/standards_knowledge.sqlite`
- 数据库 SHA-256：`{report["database_sha256"]}`
- 数据库必需表结构检查：`{report["database_schema_check"]}`
- 文档记录：{report["document_count"]}
- 实际 chunk 记录：{report["chunk_count"]}
- 表格记录：{report["table_count"]}
- 公式记录：{report["formula_count"]}
- 图件记录：{report["figure_count"]}
- chunk 外键悬空记录：{report["orphan_chunk_count"]}
- 缺失 chunk_id：{report["missing_chunk_id_count"]}
- 缺失 text_sha256：{report["missing_text_sha256_count"]}

数据库是运行时检索的权威载体；本文件和 `source_layer/indexes/chunk_catalog.csv`
是从同一数据库确定性生成的轻量旁证，不替代标准原文，也不把检索命中自动升级成
正式设计结论。

## 2. 参数/证据层到程序用途的交叉关系

| 数据层 | 可提供字段 | 程序用途 | 允许的最高声明 | 必须保留的门 |
| --- | --- | --- | --- | --- |
| `documents` | 文档 ID、相对路径、PDF 哈希、资料族、来源类型、默认证据级、包状态 | 来源身份、版本和资料族路由 | 来源已登记 | 不能据此宣称参数适用或设备定型 |
| `chunks` | 页码、章节、提取方法、质量分、文本哈希、位置状态、正文 | 全文检索与证据定位 | 找到可复核文本证据 | 参数语义、适用范围、单位和工况仍须核对 |
| `tables_data` | 表题、单元格文本、结构置信度、几何状态、`numeric_reuse_allowed` | 查找尺寸系列、材料或标准表候选 | 仅在数值复用允许且规则显式消费时进入程序初筛 | 表号、表头、脚注、版本和同一设备适用性 |
| `formulas_data` | 公式标签、题注、原始文本、QA 状态、页码和原文哈希 | 公式发现与人工复核 | 公式证据候选 | 只有程序内已登记并测试的确定性公式可自动计算 |
| `figures_data` | 图题、关键图标记、页码、边界框、原文哈希 | 结构示意和人工复核 | 视觉证据候选 | 不允许从图像自动生成正式尺寸或型号 |
| `type_selection/*` | 已校验目录表、硬排除、兼容矩阵、规则、警告、包内哈希清单 | 法兰/垫片等确定性组件初筛 | 具体程序候选 | 正式标准范围、材料兼容、工况及厂家数据仍须闭合 |

设备、管线计算结果仍以应用内确定性公式链、输入来源、候选规则和最终记录哈希为准；
本知识库只提供检索证据和标准路由，不能绕过 `OPEN`、证据等级或正式发布门。

## 3. 资料族覆盖

| 资料族 | 文档数 | 实际 chunk 数 |
| --- | ---: | ---: |
{family_rows}

## 4. 已知元数据差异

`documents.chunk_count` 是源包登记值；实际可检索粒度必须以 `chunks` 表和生成目录为准。
当前发现 {len(report["document_chunk_count_mismatches"])} 个差异：

| doc_id | 登记 chunk 数 | 实际 chunk 数 | duplicate_of | 包状态 |
| --- | ---: | ---: | --- | --- |
{mismatch_rows}

- `std_hg_t_21514_2005_tower` 是指向 reactor 版本的显式重复记录，不重复装载正文。
- `std_hgj_211_85` 标记为 `RECOVERED_WITH_LAYOUT_LIMITS`；只装载了 57 个可定位
  chunk，不能把登记的 192 当作已可检索。
- 生成的 `chunk_catalog.csv` 严格包含 {report["catalog_row_count"]} 个实际 chunk，
  不伪造缺失记录。

## 5. 可复现性

- 生成脚本：`scripts/rebuild_standards_runtime_sidecars.py`
- 生成报告：`source_layer/indexes/sidecar_generation_report.json`
- chunk 目录 SHA-256：`{report["catalog_sha256"]}`
- 交叉表内容由数据库哈希、表计数、资料族统计和差异清单生成。
- 发布包的 `runtime_asset_manifest.json` 会再次记录数据库、目录、交叉表和生成报告的
  文件哈希；任何改动都会触发运行时资产校验失败。
"""


def rebuild(database_path: Path, standards_graph_root: Path) -> dict[str, Any]:
    database_path = database_path.resolve()
    # Keep the caller-visible output path.  Resolving a workspace junction can
    # redirect writes to its historical source tree, while relative I/O must
    # stay inside the active package being rebuilt.
    standards_graph_root = Path(standards_graph_root)
    if not database_path.is_file():
        raise FileNotFoundError(f"Standards database is missing: {database_path}")

    catalog_path = standards_graph_root / "source_layer" / "indexes" / "chunk_catalog.csv"
    report_path = (
        standards_graph_root
        / "source_layer"
        / "indexes"
        / "sidecar_generation_report.json"
    )
    crosswalk_path = standards_graph_root / "standard_parameter_crosswalk.md"

    _progress("opening hash-bound SQLite carrier")
    connection = sqlite3.connect(f"file:{database_path.as_posix()}?mode=ro", uri=True)
    try:
        required_tables = {
            "documents",
            "chunks",
            "tables_data",
            "formulas_data",
            "figures_data",
        }
        available_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        missing_tables = sorted(required_tables - available_tables)
        if missing_tables:
            raise RuntimeError(
                f"Standards database is missing required tables: {missing_tables}"
            )
        _progress("required schema tables present")

        select_columns = ", ".join(CATALOG_COLUMNS)
        # The chunks table stores large text payloads.  Walking the chunk_id
        # index would force thousands of random table-page reads merely to emit
        # compact metadata.  Rowid order is deterministic for the frozen,
        # hash-bound database and permits one sequential table scan.
        catalog_rows = connection.execute(
            f"SELECT {select_columns} FROM chunks ORDER BY rowid"
        )
        _progress("exporting compact chunk catalog")
        catalog_row_count = _atomic_write_catalog(catalog_path, catalog_rows)
        _progress(f"chunk catalog exported: {catalog_row_count} rows")

        document_count = int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
        chunk_count = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        table_count = int(connection.execute("SELECT COUNT(*) FROM tables_data").fetchone()[0])
        formula_count = int(connection.execute("SELECT COUNT(*) FROM formulas_data").fetchone()[0])
        figure_count = int(connection.execute("SELECT COUNT(*) FROM figures_data").fetchone()[0])
        if catalog_row_count != chunk_count:
            raise RuntimeError(
                f"Catalog row count mismatch: catalog={catalog_row_count}, chunks={chunk_count}"
            )

        family_counts = _query_rows(
            connection,
            """
            SELECT d.family, COUNT(DISTINCT d.doc_id), COUNT(c.chunk_id)
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.doc_id = d.doc_id
            GROUP BY d.family
            ORDER BY d.family
            """,
        )
        mismatch_rows = _query_rows(
            connection,
            """
            SELECT
                d.doc_id,
                d.chunk_count,
                COUNT(c.chunk_id),
                d.duplicate_of,
                d.package_status
            FROM documents AS d
            LEFT JOIN chunks AS c ON c.doc_id = d.doc_id
            GROUP BY d.doc_id
            HAVING d.chunk_count != COUNT(c.chunk_id)
            ORDER BY d.doc_id
            """,
        )
        orphan_chunk_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM chunks AS c
                LEFT JOIN documents AS d ON d.doc_id = c.doc_id
                WHERE d.doc_id IS NULL
                """
            ).fetchone()[0]
        )
        missing_chunk_id_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM chunks WHERE chunk_id IS NULL OR TRIM(chunk_id) = ''"
            ).fetchone()[0]
        )
        missing_text_sha256_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM chunks
                WHERE text_sha256 IS NULL OR TRIM(text_sha256) = ''
                """
            ).fetchone()[0]
        )
    finally:
        connection.close()

    _progress("hashing SQLite carrier and generated catalog")
    report: dict[str, Any] = {
        "schema": "standards-runtime-sidecar-generation-report-v1",
        "status": "PASS",
        "database_relative_path": "source_layer/indexes/standards_knowledge.sqlite",
        "database_sha256": _sha256(database_path),
        "database_schema_check": "PASS",
        "database_required_tables": sorted(required_tables),
        "document_count": document_count,
        "chunk_count": chunk_count,
        "catalog_row_count": catalog_row_count,
        "catalog_sha256": _sha256(catalog_path),
        "table_count": table_count,
        "formula_count": formula_count,
        "figure_count": figure_count,
        "orphan_chunk_count": orphan_chunk_count,
        "missing_chunk_id_count": missing_chunk_id_count,
        "missing_text_sha256_count": missing_text_sha256_count,
        "family_counts": [
            [family, int(documents), int(chunks)]
            for family, documents, chunks in family_counts
        ],
        "document_chunk_count_mismatches": [
            {
                "doc_id": doc_id,
                "declared_chunk_count": int(declared),
                "actual_chunk_count": int(actual),
                "duplicate_of": duplicate_of,
                "package_status": package_status,
            }
            for doc_id, declared, actual, duplicate_of, package_status in mismatch_rows
        ],
        "claim_boundary": (
            "The SQLite database is the authority carrier. The CSV and Markdown "
            "sidecars expose searchable grain and evidence boundaries; they do not "
            "promote retrieved text, tables, formulas, or figures to formal design."
        ),
    }
    _atomic_replace_text(
        crosswalk_path,
        _render_crosswalk(report).rstrip() + "\n",
    )
    report["crosswalk_sha256"] = _sha256(crosswalk_path)
    _atomic_replace_text(
        report_path,
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _progress("sidecars rebuilt and hash-bound")
    return report


def main() -> int:
    package_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=(
            package_root
            / "knowledge_graph"
            / "standards_graph"
            / "source_layer"
            / "indexes"
            / "standards_knowledge.sqlite"
        ),
    )
    parser.add_argument(
        "--standards-graph-root",
        type=Path,
        default=package_root / "knowledge_graph" / "standards_graph",
    )
    args = parser.parse_args()
    report = rebuild(args.database, args.standards_graph_root)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
