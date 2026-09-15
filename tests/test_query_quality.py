"""Focused regression checks for offline knowledge-query quality."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


CANDIDATE = Path(__file__).resolve().parents[1]
SCRIPTS = CANDIDATE / "knowledge" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import query_knowledge as query  # noqa: E402
import vector_adapter  # noqa: E402
from retrieval_quality import (  # noqa: E402
    _fragment_candidates,
    is_pure_chapter_title,
)


class QueryQuality(unittest.TestCase):
    def test_natural_chinese_and_macro_layer(self):
        result = query.search("节流降压为什么有时反而升温？", limit=5)
        self.assertEqual(result["results"][0]["node_id"], "TH03-A8")
        macro = query.search("热量 温位 先减负荷 再回收 后升级", limit=5)
        self.assertEqual(macro["results"][0]["node_id"], "L3-05")
        self.assertEqual(macro["results"][0]["knowledge_layer"], "L3")

    def test_detail_question_is_not_weak_l3_first(self):
        result = query.search("压缩机功率计算", limit=5, detail=True)
        self.assertEqual(result["results"][0]["knowledge_layer"], "L1")
        self.assertNotIn(result["results"][0]["node_id"], {"L3-01", "L3-02", "L3-03", "L3-04", "L3-05", "L3-06", "L3-07", "L3-08"})

    def test_vector_fragment_and_unrelated_queries(self):
        result = vector_adapter.query("吸收式制冷和压缩式制冷的COP能直接比较吗？", limit=5)
        self.assertEqual(result["results"][0]["node_id"], "TH03-B4")
        self.assertEqual(vector_adapter.query("天气 预报 明天 下雨", limit=5)["results"], [])
        self.assertEqual(vector_adapter.query("菜谱 土豆 鸡蛋 做法", limit=5)["results"], [])

    def test_corpus_scoped_queries_reach_expected_nodes(self):
        cases = (
            ("二元汽液平衡数据拿来回归活度系数之前，怎样筛查整体一致性和局部错误？", "TH03-C6"),
            ("同样是降压，阀门出口和透平出口的闪蒸求解分别要守什么能量约束？", "TH03-C10"),
        )
        for text, expected in cases:
            lexical = query.search(text, corpus="chemical_principles", limit=5)
            vector = vector_adapter.query(text, corpus="chemical_principles", limit=5)
            self.assertIn(expected, {row["node_id"] for row in lexical["results"]})
            self.assertIn(expected, {row["node_id"] for row in vector["results"]})

    def test_fragment_spies_receive_only_scoped_admitted_records(self):
        text = "二元汽液平衡数据拿来回归活度系数之前，怎样筛查整体一致性和局部错误？"
        lexical_calls = []
        vector_calls = []
        lexical_original = query.select_query_fragments
        vector_original = vector_adapter.select_query_fragments

        def lexical_spy(value, documents=None, **kwargs):
            lexical_calls.append(list(documents or []))
            return lexical_original(value, documents, **kwargs)

        def vector_spy(value, documents=None, **kwargs):
            vector_calls.append(list(documents or []))
            return vector_original(value, documents, **kwargs)

        with patch.object(query, "select_query_fragments", side_effect=lexical_spy), \
             patch.object(vector_adapter, "select_query_fragments", side_effect=vector_spy):
            query.search(text, corpus="chemical_principles", limit=5)
            vector_adapter.query(text, corpus="chemical_principles", limit=5)

        self.assertEqual(len(lexical_calls), 1)
        self.assertEqual(len(vector_calls), 1)
        for rows in (*lexical_calls, *vector_calls):
            self.assertTrue(rows)
            self.assertTrue(all(
                row["corpus"] == "chemical_principles"
                and row.get("content_available")
                and row.get("retrieval_eligible")
                for row in rows
            ))
            self.assertNotIn("UG10-CH06-D017", {row["node_id"] for row in rows})

    def test_weather_sentence_has_no_syntax_only_answer(self):
        result = query.search("明天上海会不会下雨，出门需要带伞吗？", limit=5)
        self.assertEqual(result["results"], [])

    def test_cooking_sentence_has_no_syntax_only_answer(self):
        result = query.search("烹饪时还是先蒸还是后炒？", limit=5)
        self.assertEqual(result["results"], [])

    def test_common_question_phrase_substrings_are_boundaries(self):
        candidates = {fragment for fragment, _ in _fragment_candidates(
            "会不会需要应该还是先安排"
        )}
        self.assertNotIn("不会", candidates)
        self.assertNotIn("需要", candidates)
        self.assertNotIn("应该", candidates)
        self.assertNotIn("还是", candidates)
        self.assertNotIn("是先", candidates)

    def test_pure_heading_filter_does_not_change_records(self):
        _, records = query.load_records(CANDIDATE / "knowledge")
        heading = next(record for record in records if record["node_id"] == "UG10-CH38-D001")
        self.assertTrue(is_pure_chapter_title(heading))
        answer = query.search("ActiveX 自动控制服务器", limit=50)
        self.assertTrue(all(not is_pure_chapter_title(row) for row in answer["results"]))
        self.assertIn(heading["node_id"], {record["node_id"] for record in records})

    def test_short_exact_formula_is_not_length_filtered(self):
        result = query.search("Joule-Thomson throttling", limit=5)
        self.assertEqual(result["results"][0]["node_id"], "TH03-A8")
        self.assertTrue(query.search("COP", limit=20)["results"])

    def test_exact_text_group_keeps_all_identity_metadata(self):
        result = query.search("On Error GoTo ErrorHandler", limit=5)
        row = next(item for item in result["results"] if item["node_id"] == "UG10-CH38-D038")
        self.assertEqual(row["same_text_count"], 12)
        identifiers = {item["node_id"] for item in row["same_text_group"]}
        self.assertIn("UG10-CH38-D071", identifiers)
        self.assertTrue(all("source" in item and "title" in item and "applicability" in item for item in row["same_text_group"]))
        self.assertNotIn("semantic", json.dumps(row["same_text_group"], ensure_ascii=False).casefold())
        exact = query.search(node_id="UG10-CH38-D071", limit=5)
        self.assertEqual([item["node_id"] for item in exact["results"]], ["UG10-CH38-D071"])
        self.assertNotIn("same_text_count", exact["results"][0])

    def test_held_records_and_authority_gate_remain_closed(self):
        _, records = query.load_records(CANDIDATE / "knowledge")
        self.assertTrue(all(record["authority_scope"] == "shared" for record in records))
        natural = query.search("规定组分 物性", limit=100)
        self.assertTrue(all(item["content_available"] and item["retrieval_eligible"] for item in natural["results"]))
        held = query.search(node_id="UG10-CH06-D017", limit=5)
        self.assertEqual(held["results"][0]["text"], "")
        self.assertFalse(held["results"][0]["content_available"])

    def test_query_terms_signature_and_matrix_payload(self):
        self.assertIsInstance(query.query_terms("COP"), list)
        _, records = query.load_records(CANDIDATE / "knowledge")
        expected_count = sum(record["content_available"] and record["retrieval_eligible"] for record in records)
        config = json.loads((CANDIDATE / "knowledge" / "vectors" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["record_count"], expected_count)
        self.assertEqual(config["shape"], [expected_count, 768])
        import numpy as np
        matrix = np.load(CANDIDATE / "knowledge" / "vectors" / "vectors.npy", allow_pickle=False)
        self.assertEqual(matrix.shape, (expected_count, 768))
        self.assertEqual(matrix.dtype.name, "float32")
        self.assertTrue(np.isfinite(matrix).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
