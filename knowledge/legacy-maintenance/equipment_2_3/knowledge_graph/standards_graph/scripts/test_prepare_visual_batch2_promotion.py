from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from prepare_visual_batch2_promotion import (
    STANDARD_FIELDS,
    page_ok,
    prepare_gbt1220_table,
    require_runtime_safe,
    validate_figure_graph,
)


def write_valid_gbt1220_table16_candidate(root: Path) -> tuple[Path, Path]:
    candidate = root / "candidate"
    data = candidate / "candidate_data"
    data.mkdir(parents=True)
    printed_rows = [
        ("化学成分", "1", "GB/T 20066", "GB/T 223(见第2章)、GB/T 11170、GB/T 9971—2004的附录A"),
        ("拉伸", "2", "不同根钢棒，GB/T 2975", "GB/T 228"),
        ("冲击", "2", "不同根钢棒，GB/T 2975", "GB/T 229"),
        ("硬度", "2", "不同根钢棒", "GB/T 230.1、GB/T 231.1、GB/T 4340.1"),
        ("晶间腐蚀", "2", "不同根钢棒", "GB/T 4334.1、GB/T 4334.2、GB/T 4334.3、GB/T 4334.5"),
        ("低倍组织", "2", "相当于钢锭头部的不同根钢棒或钢坯；连铸钢在任意不同根钢棒", "GB/T 226、GB/T 1979"),
        ("超声波检验", "2", "整根钢棒", "GB/T 7736"),
        ("热顶锻", "2", "不同根钢棒", "YB/T 5293"),
        ("非金属夹杂物", "2", "不同根钢棒", "GB/T 10561"),
        ("晶粒度", "1", "任一钢棒", "GB/T 6394"),
        ("α相", "1", "任一钢棒", "GB/T 6401—1986、GB/T 13305—1991"),
        ("塔形", "2", "相当于钢锭头部的不同根钢棒或钢坯；连铸钢在任意不同根钢棒", "GB/T 15711、GB/T 10121"),
        ("尺寸", "逐根", "整根钢棒", "卡尺、千分尺"),
        ("表面", "逐根", "整根钢棒", "目视"),
    ]
    records = []
    for index, (item, quantity, location, method) in enumerate(printed_rows, 1):
        records.append({
            "record_id": f"std_gb_t_1220_2007:p0019:t01:r{index:02d}",
            "record_type": "table_row", "physical_page": "19",
            "source_section": "Table 16",
            "source_table": "std_gb_t_1220_2007:p0019:t01",
            "source_row_label": f"row {index}",
            "source_column_label": "inspection_and_sampling",
            "source_bbox_pt": "page_19_table_bbox; table_bbox_only",
            "raw_value": (
                f"序号={index}；检验项目={item}；取样数量={quantity}；"
                f"取样部位={location}；试验方法={method}"
            ),
            "normalized_value": json.dumps({
                "inspection_item": item,
                "sampling_quantity_printed": quantity,
                "sampling_location_printed": location,
                "test_method_printed": method,
                "inheritance_flags": {
                    "sampling_quantity": False,
                    "sampling_location": index in {3, 5, 9, 11, 14},
                    "test_method": False,
                },
            }, ensure_ascii=False),
            "unit": "", "applicability": "all", "qa_status": "VERIFIED",
            "terminal_class": "DIRECT_REUSE_VERIFIED",
            "reuse_status": "DIRECT_REUSE_VERIFIED",
        })
    records.append({
        **records[0],
        "record_id": "std_gb_t_1220_2007:p0019:t01:footnote:a",
        "record_type": "table_footnote", "source_row_label": "footnote a",
        "source_column_label": "sampling_quantity_condition",
        "raw_value": (
            "a 电渣钢除表面和尺寸逐根外，其他检验项目的取样数量均为1个。"
            "以自耗电极的熔炼母炉号组批时，除化学成分每个电渣炉号取1个外，"
            "其他检验项目取样数量同表中规定。"
        ),
        "normalized_value": json.dumps({
            "conditions": [
                {"condition_text": "电渣钢（表面和尺寸除外）", "sampling_quantity_printed": "1个"},
                {
                    "condition_text": "以自耗电极的熔炼母炉号组批",
                    "chemical_composition_sampling_quantity_printed": "每个电渣炉号1个",
                    "other_inspection_items_sampling_quantity_printed": "同表中规定",
                },
            ]
        }, ensure_ascii=False),
    })
    source = data / "gbt1220_table16_records.csv"
    with source.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
        writer.writeheader()
        writer.writerows(records)
    audit = root / "audit.md"
    audit.write_text("reviewed\n" * 30, encoding="utf-8")
    return candidate, audit


class VisualBatch2PromotionTest(unittest.TestCase):
    def test_closed_physical_page_chain(self) -> None:
        self.assertTrue(page_ok("23"))
        self.assertTrue(page_ok("23-24"))
        self.assertTrue(page_ok("37|38|39|40"))
        self.assertFalse(page_ok("0"))
        self.assertFalse(page_ok("p23"))

    def test_dangling_figure_relation_is_rejected(self) -> None:
        rows = [
            {
                "figure_id": "std:p0001:f01",
                "entity_id": "root",
                "parent_entity_id": "",
                "relation_from_entity_id": "",
                "relation_to_entity_id": "",
            },
            {
                "figure_id": "std:p0001:f01",
                "entity_id": "relation",
                "parent_entity_id": "root",
                "relation_from_entity_id": "root",
                "relation_to_entity_id": "missing",
            },
        ]
        with self.assertRaisesRegex(ValueError, "dangling relation_to_entity_id"):
            validate_figure_graph(rows)

    def test_runtime_csv_rejects_source_image_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "runtime.csv"
            path.write_text("record_id,payload\n1,evidence.png\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference leaked"):
                require_runtime_safe(path)

    def test_gbt1220_table16_without_material_footnote_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "candidate"
            data = candidate / "candidate_data"
            data.mkdir(parents=True)
            fields = (
                "record_id,record_type,physical_page,source_section,source_table,"
                "source_row_label,source_column_label,source_bbox_pt,raw_value,"
                "normalized_value,unit,applicability,qa_status,terminal_class,reuse_status\n"
            )
            rows = []
            for index in range(1, 15):
                rows.append(
                    f"std_gb_t_1220_2007:p0019:t01:r{index:02d},table_row,19,"
                    "Table 16,std_gb_t_1220_2007:p0019:t01,row,inspection_and_sampling,"
                    "page_19_table_bbox; table_bbox_only,printed,normalized,,all,"
                    "VERIFIED,DIRECT_REUSE_VERIFIED,DIRECT_REUSE_VERIFIED"
                )
            (data / "gbt1220_table16_records.csv").write_text(
                fields + "\n".join(rows) + "\n", encoding="utf-8-sig"
            )
            audit = root / "audit.md"
            audit.write_text("reviewed\n" * 30, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "15 records"):
                prepare_gbt1220_table(candidate, root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_requires_exact_material_footnote(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "candidate" / "candidate_data"
            data.mkdir(parents=True)
            records = []
            for index in range(1, 15):
                records.append({
                    "record_id": f"std_gb_t_1220_2007:p0019:t01:r{index:02d}",
                    "record_type": "table_row", "physical_page": "19",
                    "source_section": "Table 16",
                    "source_table": "std_gb_t_1220_2007:p0019:t01",
                    "source_row_label": f"row {index}",
                    "source_column_label": "inspection_and_sampling",
                    "source_bbox_pt": "page_19_table_bbox; table_bbox_only",
                    "raw_value": f"printed row {index}",
                    "normalized_value": json.dumps({
                        "inspection_item": f"item {index}",
                        "sampling_quantity_printed": "1",
                        "sampling_location_printed": "sample",
                        "test_method_printed": "method",
                        "inheritance_flags": {
                            "sampling_quantity": False,
                            "sampling_location": index in {3, 5, 9, 11, 14},
                            "test_method": False,
                        },
                    }),
                    "unit": "", "applicability": "all", "qa_status": "VERIFIED",
                    "terminal_class": "DIRECT_REUSE_VERIFIED",
                    "reuse_status": "DIRECT_REUSE_VERIFIED",
                })
            records.append({
                **records[0],
                "record_id": "std_gb_t_1220_2007:p0019:t01:footnote:a",
                "record_type": "table_footnote", "source_row_label": "footnote a",
                "source_column_label": "sampling_quantity_condition",
                "raw_value": "not the printed footnote",
                "normalized_value": json.dumps({"rules": ["one", "two"]}),
            })
            source = data / "gbt1220_table16_records.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(records)
            audit = root / "audit.md"
            audit.write_text("reviewed\n" * 30, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "printed footnote"):
                prepare_gbt1220_table(root / "candidate", root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_requires_two_structured_footnote_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "candidate" / "candidate_data"
            data.mkdir(parents=True)
            records = []
            for index in range(1, 15):
                records.append({
                    "record_id": f"std_gb_t_1220_2007:p0019:t01:r{index:02d}",
                    "record_type": "table_row", "physical_page": "19",
                    "source_section": "Table 16",
                    "source_table": "std_gb_t_1220_2007:p0019:t01",
                    "source_row_label": f"row {index}",
                    "source_column_label": "inspection_and_sampling",
                    "source_bbox_pt": "page_19_table_bbox; table_bbox_only",
                    "raw_value": f"printed row {index}",
                    "normalized_value": json.dumps({
                        "inspection_item": f"item {index}",
                        "sampling_quantity_printed": "1",
                        "sampling_location_printed": "sample",
                        "test_method_printed": "method",
                        "inheritance_flags": {
                            "sampling_quantity": False,
                            "sampling_location": index in {3, 5, 9, 11, 14},
                            "test_method": False,
                        },
                    }),
                    "unit": "", "applicability": "all", "qa_status": "VERIFIED",
                    "terminal_class": "DIRECT_REUSE_VERIFIED",
                    "reuse_status": "DIRECT_REUSE_VERIFIED",
                })
            records.append({
                **records[0],
                "record_id": "std_gb_t_1220_2007:p0019:t01:footnote:a",
                "record_type": "table_footnote", "source_row_label": "footnote a",
                "source_column_label": "sampling_quantity_condition",
                "raw_value": (
                    "a 电渣钢除表面和尺寸逐根外，其他检验项目的取样数量均为1个。"
                    "以自耗电极的熔炼母炉号组批时，除化学成分每个电渣炉号取1个外，"
                    "其他检验项目取样数量同表中规定。"
                ),
                "normalized_value": json.dumps({"conditions": [{"condition_text": "only one"}]}),
            })
            source = data / "gbt1220_table16_records.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(records)
            audit = root / "audit.md"
            audit.write_text("reviewed\n" * 30, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "structured footnote"):
                prepare_gbt1220_table(root / "candidate", root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_rejects_blank_direct_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[3]["raw_value"] = ""
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "incomplete direct record"):
                prepare_gbt1220_table(candidate, root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_requires_row_semantics_and_inheritance_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            rows[5]["normalized_value"] = json.dumps({"inspection_item": "item 6"})
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "row semantics"):
                prepare_gbt1220_table(candidate, root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_requires_source_verified_merge_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            row5 = json.loads(rows[4]["normalized_value"])
            row5["inheritance_flags"]["sampling_location"] = False
            rows[4]["normalized_value"] = json.dumps(row5, ensure_ascii=False)
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "merge pattern"):
                prepare_gbt1220_table(candidate, root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_rejects_changed_printed_row_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            row7 = json.loads(rows[6]["normalized_value"])
            row7["test_method_printed"] = "changed"
            rows[6]["normalized_value"] = json.dumps(row7, ensure_ascii=False)
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "printed row semantics"):
                prepare_gbt1220_table(candidate, root / "out", audit, "2026-07-20T00:00:00Z")

    def test_gbt1220_table16_prepares_runtime_dataset_and_exact_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            out = root / "out"
            result = prepare_gbt1220_table(
                candidate, out, audit, "2026-07-20T00:00:00Z"
            )
            self.assertEqual(result["records"], 15)
            runtime = out / "gbt1220_2007_table16_records.csv"
            datasets = out / "dataset_registry.fragment.csv"
            rules = out / "table_promotion_rules.fragment.csv"
            self.assertTrue(runtime.is_file())
            self.assertTrue(datasets.is_file())
            self.assertTrue(rules.is_file())
            require_runtime_safe(runtime)
            with datasets.open("r", encoding="utf-8-sig", newline="") as handle:
                dataset_rows = list(csv.DictReader(handle))
            with rules.open("r", encoding="utf-8-sig", newline="") as handle:
                rule_rows = list(csv.DictReader(handle))
            self.assertEqual(dataset_rows[0]["record_filter_values"], "DIRECT_REUSE_VERIFIED")
            self.assertEqual(rule_rows[0]["table_ids"], "std_gb_t_1220_2007:p0019:t01")

    def test_gbt1220_table16_accepts_reviewed_glyph_candidate_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, audit = write_valid_gbt1220_table16_candidate(root)
            source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows[:14]:
                row["record_type"] = "inspection_sampling_rule"
            for row in rows:
                row["source_table"] = "表16 钢棒检验项目、取样数量、取样部位及试验方法"
                row["qa_status"] = "VERIFIED_PRINTED_GLYPH"
                row["terminal_class"] = ""
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            out = root / "out"
            prepare_gbt1220_table(candidate, out, audit, "2026-07-20T00:00:00Z")
            with (out / "gbt1220_2007_table16_records.csv").open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                runtime = list(csv.DictReader(handle))
            self.assertEqual(len(runtime), 15)
            self.assertTrue(all(row["source_table"] == "std_gb_t_1220_2007:p0019:t01" for row in runtime))
            self.assertTrue(all(row["qa_status"] == "VERIFIED" for row in runtime))
            self.assertTrue(all(row["terminal_class"] == "DIRECT_REUSE_VERIFIED" for row in runtime))


if __name__ == "__main__":
    unittest.main()
