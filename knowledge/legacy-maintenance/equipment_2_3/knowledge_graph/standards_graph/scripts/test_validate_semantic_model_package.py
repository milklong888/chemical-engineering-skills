from __future__ import annotations

import unittest

from validate_semantic_model_package import (
    validate_figure_object_rows,
    validate_figure_model_alignment,
    validate_package_links,
    validate_model_rows,
    validate_semantic_rows,
)


class SemanticResolutionValidationTests(unittest.TestCase):
    def test_rejects_nonterminal_ocr_candidate_resolution_status(self) -> None:
        rows = [{
            "source_fact_id": "std:p0141:t01:r01:c01",
            "asset_kind": "table_cell",
            "resolution_status": "OCR_CELL_CANDIDATE",
            "raw_observed": "112",
            "resolved_value": "112",
            "resolution_basis": "OCR word candidate",
            "context_refs": "p0141;r1c1;bbox=[1,2,3,4]",
            "source_file": "tables/p0141_t01_cells.csv",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("non-terminal resolution status" in error for error in errors))

    def test_visual_table_cell_status_requires_image_evidence_not_csv(self) -> None:
        rows = [{
            "source_fact_id": "std:p0141:t01:r01:c01",
            "asset_kind": "table_cell",
            "resolution_status": "VISUAL_GLYPH_CONFIRMED",
            "raw_observed": "112",
            "resolved_value": "112",
            "resolution_basis": "copied from extracted cell grid",
            "context_refs": "p0141;r1c1;bbox=[1,2,3,4]",
            "source_file": "tables/p0141_t01_cells.csv",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("visual table-cell status needs image evidence" in error for error in errors))

    def test_rejects_source_fact_deferring_to_original_document(self) -> None:
        rows = [{
            "record_id": "b1:p25:r18:c6",
            "raw_observed": "典型用途见表B.1 p25原文",
            "resolved_value": "典型用途见表B.1 p25原文",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("deferred source placeholder" in error for error in errors))

    def test_rejects_mojibake_in_source_fact_text(self) -> None:
        rows = [{
            "source_fact_id": "std:p0033:t01:r01:c01",
            "resolution_status": "VISUAL_GLYPH_VERIFIED",
            "raw_observed": "鏉愭枡绫诲埆鎸変綆娓╂€ц兘",
            "resolved_value": "鏉愭枡绫诲埆鎸変綆娓╂€ц兘",
            "resolution_basis": "direct source cell",
            "context_refs": "p0033:r01:c01",
            "resolution_confidence": "SOURCE_DIRECT",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("mojibake" in error for error in errors))

    def test_accepts_replayable_semantic_resolution(self) -> None:
        rows = [{
            "cell_id": "std:p0102:t01:r03:c04",
            "cell_status": "SEMANTIC_CONTEXT_RESOLVED",
            "raw_observed": "<1 X10*",
            "resolved_value": "<1×10⁴ mPa·s",
            "resolution_basis": (
                "column header=粘度; unit=mPa·s; exponent pattern confirmed by "
                "p0102:r02:c04 and p0103:r02:c04"
            ),
            "context_cells": "p0102:r02:c04;p0103:r02:c04;header:粘度;unit:mPa·s",
            "resolution_confidence": "HIGH_UNIQUE_CONTEXT",
        }]
        self.assertEqual(validate_semantic_rows(rows), [])

    def test_rejects_generic_context_template(self) -> None:
        rows = [{
            "cell_id": "std:p0102:t01:r03:c04",
            "cell_status": "SEMANTIC_CONTEXT_RESOLVED",
            "raw_observed": "<1 X10*",
            "resolved_value": "<1×10⁴ mPa·s",
            "resolution_basis": (
                "full-page image + same physical merge + row identity + "
                "unit/variable convention"
            ),
            "context_cells": (
                "same page; same column; adjacent logical row(s); merged "
                "master/member where applicable"
            ),
            "resolution_confidence": "HIGH_UNIQUE_CONTEXT",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("concrete" in error for error in errors))
        self.assertTrue(any("generic template" in error for error in errors))

    def test_visual_status_cannot_claim_semantic_basis(self) -> None:
        rows = [{
            "cell_id": "std:p0102:t01:r03:c04",
            "cell_status": "VISUAL_GLYPH_VERIFIED",
            "raw_observed": "<1 X10*",
            "resolved_value": "<1×10⁴ mPa·s",
            "resolution_basis": "semantic reconstruction from p0102:r02:c04",
            "context_cells": "p0102:r02:c04",
            "resolution_confidence": "HIGH_UNIQUE_CONTEXT",
        }]
        errors = validate_semantic_rows(rows)
        self.assertTrue(any("masquerade" in error for error in errors))


class FigureObjectValidationTests(unittest.TestCase):
    def test_closed_digitized_curve_requires_explicit_interpolation_domain(self) -> None:
        figures = [{
            "figure_id": "std:p0292:f02",
            "content_kind": "quantitative",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["reynolds_number_axis", "correction_factor_curve"],
            "curve_data_status": "DIGITIZED_POINT_LEDGER_LINKED",
        }]
        models = [{
            "constraint_id": "curve-rel",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "std:p0292:f02",
            "object_json": (
                '{"curve_pointsets":{"factor":[[30,0.3],[100000,1.0]]},'
                '"series_metadata":{"factor":{"x_quantity_id":"reynolds_number",'
                '"x_unit":"1"}}}'
            ),
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear; x=log10",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden"}'
            ),
        }]
        errors = validate_figure_model_alignment(models, figures)
        self.assertTrue(any("interpolation_x_domain" in error for error in errors))

    def test_closed_curve_rejects_axis_domain_used_as_interpolation_domain(self) -> None:
        figures = [{
            "figure_id": "std:p0292:f02",
            "content_kind": "quantitative",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["reynolds_number_axis", "correction_factor_curve"],
            "curve_data_status": "DIGITIZED_POINT_LEDGER_LINKED",
        }]
        models = [{
            "constraint_id": "curve-rel",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "std:p0292:f02",
            "object_json": (
                '{"curve_pointsets":{"factor":[[30,0.3],[100000,1.0]]},'
                '"series_metadata":{"factor":{"x_quantity_id":"reynolds_number",'
                '"x_unit":"1"}}}'
            ),
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear; x=log10",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden",'
                '"axis_display_domain":{"quantity_id":"reynolds_number",'
                '"value_min":10,"value_max":100000,"unit":"1"},'
                '"interpolation_x_domain":{"quantity_id":"reynolds_number",'
                '"value_min":10,"value_max":100000,"unit":"1"}}'
            ),
        }]
        errors = validate_figure_model_alignment(models, figures)
        self.assertTrue(any("exceeds pointset coverage" in error for error in errors))

    def test_closed_digitized_curve_requires_separate_axis_display_domain(self) -> None:
        figures = [{
            "figure_id": "std:p0292:f02",
            "content_kind": "quantitative",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["reynolds_number_axis", "correction_factor_curve"],
            "curve_data_status": "DIGITIZED_POINT_LEDGER_LINKED",
        }]
        models = [{
            "constraint_id": "curve-rel",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "std:p0292:f02",
            "object_json": '{"curve_pointsets":{"factor":[[30,0.3],[100000,1.0]]}}',
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear; x=log10",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden",'
                '"interpolation_x_domain":{"quantity_id":"reynolds_number",'
                '"value_min":30,"value_max":100000,"unit":"1"}}'
            ),
        }]
        errors = validate_figure_model_alignment(models, figures)
        self.assertTrue(any("axis_display_domain" in error for error in errors))

    def test_accepts_axis_display_domain_broader_than_curve_interpolation_domain(self) -> None:
        figures = [{
            "figure_id": "std:p0292:f02",
            "content_kind": "quantitative",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["reynolds_number_axis", "correction_factor_curve"],
            "curve_data_status": "DIGITIZED_POINT_LEDGER_LINKED",
        }]
        models = [{
            "constraint_id": "curve-rel",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "std:p0292:f02",
            "object_json": '{"curve_pointsets":{"factor":[[30,0.3],[100000,1.0]]}}',
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear; x=log10",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden",'
                '"axis_display_domain":{"quantity_id":"reynolds_number",'
                '"value_min":10,"value_max":100000,"unit":"1"},'
                '"interpolation_x_domain":{"quantity_id":"reynolds_number",'
                '"value_min":30,"value_max":100000,"unit":"1"}}'
            ),
        }]
        self.assertEqual(validate_figure_model_alignment(models, figures), [])

    def test_rejects_quantitative_figure_with_stale_structural_objects(self) -> None:
        rows = [{
            "figure_id": "std:p0292:f02",
            "content_kind": "quantitative",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["branch_connection", "main_pipe", "branch_pipe"],
            "dimensions": ["R_ge_0_25D"],
            "ports": ["branch_end"],
            "edges": ["branch connected_to main pipe"],
            "directions": ["section_view_axis"],
            "conditions": [],
            "legend": [],
            "curve_data_status": "DIGITIZED_POINT_LEDGER_LINKED",
        }]
        errors = validate_figure_object_rows(rows)
        self.assertTrue(any("coordinate/curve objects" in error for error in errors))

    def test_rejects_incomplete_structural_label_and_edge_coverage(self) -> None:
        rows = [{
            "figure_id": "std:p0300:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["flame_arrester", "terminal_type", "pipeline_type"],
            "dimensions": [],
            "ports": ["classification_root"],
            "edges": ["root connects_to three broad branches"],
            "directions": ["root_to_leaf"],
            "conditions": [],
            "legend": [],
            "printed_label_count": 20,
            "modelled_label_count": 3,
            "printed_edge_count": 19,
            "modelled_edge_count": 1,
        }]
        errors = validate_figure_object_rows(rows)
        self.assertTrue(any("label coverage mismatch" in error for error in errors))
        self.assertTrue(any("edge coverage mismatch" in error for error in errors))

    def test_rejects_caption_only_structural_figure_placeholder(self) -> None:
        rows = [{
            "figure_id": "std:p0061:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["diagram_subject:8"],
            "dimensions": [],
            "ports": [],
            "edges": ["diagram declares the captioned subject"],
            "directions": ["not_direction_bearing"],
            "conditions": [],
            "legend": [],
        }]
        errors = validate_figure_object_rows(rows)
        self.assertTrue(any("caption-only placeholder" in error for error in errors))

    def test_accepts_structural_figure_with_objects_and_edges(self) -> None:
        rows = [{
            "figure_id": "std:p0052:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": ["socket_boss", "pipe_wall_section", "centerline"],
            "dimensions": ["A_horizontal", "B_vertical"],
            "ports": ["socket_opening"],
            "edges": ["socket_boss connected_to pipe_wall_section"],
            "directions": ["dimension_A_horizontal"],
            "conditions": [],
            "legend": [],
            "printed_label_count": 6,
            "modelled_label_count": 6,
            "printed_edge_count": 1,
            "modelled_edge_count": 1,
        }]
        self.assertEqual(validate_figure_object_rows(rows), [])

    def test_accepts_structured_object_port_edge_graph(self) -> None:
        rows = [{
            "figure_id": "std:p0301:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": [
                {"object_id": "source", "object_kind": "equipment"},
                {"object_id": "sink", "object_kind": "equipment"},
            ],
            "dimensions": [],
            "ports": [
                {"port_id": "source:out", "object_id": "source", "port_name": "out"},
                {"port_id": "sink:in", "object_id": "sink", "port_name": "in"},
            ],
            "edges": [{
                "edge_id": "e1",
                "source_id": "source",
                "source_port": "out",
                "target_id": "sink",
                "target_port": "in",
            }],
            "directions": ["source_to_sink"],
            "conditions": [],
            "legend": [],
            "printed_label_count": 0,
            "modelled_label_count": 0,
            "printed_edge_count": 1,
            "modelled_edge_count": 1,
        }]
        self.assertEqual(validate_figure_object_rows(rows), [])

    def test_rejects_structured_edge_with_unknown_endpoint_or_port(self) -> None:
        rows = [{
            "figure_id": "std:p0301:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": [
                {"object_id": "source", "object_kind": "equipment"},
                {"object_id": "sink", "object_kind": "equipment"},
            ],
            "dimensions": [],
            "ports": [
                {"port_id": "source:out", "object_id": "source", "port_name": "out"},
                {"port_id": "sink:in", "object_id": "sink", "port_name": "in"},
            ],
            "edges": [{
                "edge_id": "e1",
                "source_id": "ghost",
                "source_port": "out",
                "target_id": "sink",
                "target_port": "missing",
            }],
            "directions": [],
            "conditions": [],
            "legend": [],
            "printed_label_count": 0,
            "modelled_label_count": 0,
            "printed_edge_count": 1,
            "modelled_edge_count": 1,
        }]
        errors = validate_figure_object_rows(rows)
        self.assertTrue(any("unknown source object" in error for error in errors))
        self.assertTrue(any("unknown target port" in error for error in errors))

    def test_rejects_synthetic_label_to_source_anchor_coverage_graph(self) -> None:
        rows = [{
            "figure_id": "std:p0052:f01",
            "content_kind": "structural",
            "terminal_status": "CLOSED_CANDIDATE",
            "objects": [
                {"object_id": "label_instance_001", "object_kind": "printed_label_instance"},
                {"object_id": "source_anchor_001", "object_kind": "source_anchor"},
            ],
            "dimensions": [],
            "ports": [],
            "edges": [{
                "edge_id": "coverage_edge_001",
                "source_id": "label_instance_001",
                "target_id": "source_anchor_001",
                "edge_kind": "printed_annotation_anchor",
            }],
            "directions": [],
            "conditions": [],
            "legend": [],
            "printed_label_count": 1,
            "modelled_label_count": 1,
            "printed_edge_count": 1,
            "modelled_edge_count": 1,
        }]
        errors = validate_figure_object_rows(rows)
        self.assertTrue(any("synthetic coverage anchor" in error for error in errors))


class QuantitativeModelValidationTests(unittest.TestCase):
    def test_rejects_opaque_source_cell_feature_placeholder(self) -> None:
        rows = [{
            "constraint_id": "mc_sf_std_p0141_t01_r3_c8_relation",
            "source_fact_ids": "sf_std_p0141_t01_r3_c8",
            "entity_id": "std:p0141:t01:r3:c8",
            "quantity_id": "source_table_cell_semantic",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "declared_source_relation",
            "applicability_json": "{}",
            "source_label": "source table cell",
            "predicate_id": "has_source_cell_semantic",
            "subject_id": "std:p0141:t01:r3:c8",
            "object_json": '{"feature_ids":["feature:sf_std_p0141_t01_r3_c8"]}',
            "relation_domain_json": "{}",
            "confidence": "0.9",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("opaque source-cell placeholder" in error for error in errors))

    def test_rejects_unkeyed_generic_table_numeric_quantity(self) -> None:
        rows = [{
            "constraint_id": "mc_sf_std_p0141_t01_r3_c8_numeric",
            "source_fact_ids": "sf_std_p0141_t01_r3_c8",
            "entity_id": "std:p0141:t01:r3:c8",
            "quantity_id": "source_table_cell_numeric",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "112",
            "normalized_value": "112",
            "source_unit": "MPa",
            "normalized_unit": "MPa",
            "applicability_json": "{}",
            "source_label": "112",
            "confidence": "0.9",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("unkeyed generic table quantity" in error for error in errors))

    def test_zone_decision_rules_reject_free_text_when_conditions(self) -> None:
        rows = [{
            "constraint_id": "gbt1503.figure.p0051.f01.zone_relation",
            "source_fact_ids": "gbt1503.figure.p0051.f01.governing_text",
            "entity_id": "gbt1503.figure.p0051.chart",
            "quantity_id": "chart.zone_decision",
            "value_kind": "relation",
            "operator": "defines",
            "value": "reinforcement_zone_rule",
            "applicability_json": "{}",
            "source_label": "zone_relation",
            "predicate_id": "gbt1503.has_zone_relation",
            "subject_id": "gbt1503.figure.p0051.chart",
            "object_json": (
                '{"feature_ids":["reinforce"],"decision_rules":['
                '{"when":"alpha > 31.5 degree","zone_id":"reinforce"}]}'
            ),
            "relation_domain_json": "{}",
            "confidence": "high",
            "conflict_policy": "source_figure_controls",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("structured decision conditions" in error for error in errors))

    def test_heat_treatment_group_relations_require_controlled_string_ids(self) -> None:
        rows = [{
            "constraint_id": "a5:r3:g1:cooling",
            "source_fact_ids": "table_a5:r03:g1:age_510",
            "entity_id": "gbt1220_grade:07Cr17Ni7Al",
            "quantity_id": "heat_treatment_cooling_method",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "controlled_cooling_method",
            "applicability_json": '{"heat_treatment_group_id":"group_1"}',
            "source_label": "空冷",
            "predicate_id": "heat_treatment_cooling_requirement",
            "subject_id": "gbt1220_grade:07Cr17Ni7Al",
            "object_json": '{"cooling_method":"空冷","group_id":1}',
            "relation_domain_json": '{"table_id":"table_a5","group_id":1}',
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("controlled string group_id" in error for error in errors))

    def test_typical_use_relation_requires_atomic_use_feature_ids(self) -> None:
        rows = [{
            "constraint_id": "b1:p25:r18:use",
            "source_fact_ids": "b1:p25:r18:c6",
            "entity_id": "gbt1220_grade:022Cr19Ni10",
            "quantity_id": "typical_use",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "controlled_typical_use",
            "applicability_json": "{}",
            "source_label": "典型用途",
            "predicate_id": "stainless_steel_grade_typical_use",
            "subject_id": "gbt1220_grade:022Cr19Ni10",
            "object_json": '{"type":"austenitic"}',
            "relation_domain_json": '{"table":"B.1"}',
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("use_feature_ids" in error for error in errors))

    def test_typical_use_same_as_grade_requires_structured_grade_reference(self) -> None:
        rows = [{
            "constraint_id": "b1:p25:r24:use",
            "source_fact_ids": "b1:p25:r24:c6",
            "entity_id": "gbt1220_grade:06Cr19Ni10NbN",
            "quantity_id": "typical_use",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "controlled_typical_use",
            "applicability_json": "{}",
            "source_label": "具有与06Cr19Ni10N钢相同的特性和用途",
            "predicate_id": "stainless_steel_grade_typical_use",
            "subject_id": "gbt1220_grade:06Cr19Ni10NbN",
            "object_json": (
                '{"use_feature_ids":["use_same_as_06Cr19Ni10N"],'
                '"use_ids":["use_same_as_06Cr19Ni10N"]}'
            ),
            "relation_domain_json": '{"table":"B.1"}',
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("reference_grade_ids" in error for error in errors))

    def test_scatter_pointset_relation_forbids_interpolation_with_canonical_field(self) -> None:
        rows = [{
            "constraint_id": "scatter-rel-1",
            "source_fact_ids": "std:p0206:f01:squares",
            "entity_id": "chart:observations",
            "quantity_id": "chart.scatter_pointsets",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "digitized_scatter_points",
            "applicability_json": "{}",
            "source_label": "source square observations",
            "predicate_id": "standard.has_scatter_pointset",
            "subject_id": "chart:observations",
            "object_json": (
                '{"scatter_pointsets":{"observed":[[1,2],[1,3],[2,4]]}}'
            ),
            "relation_domain_json": (
                '{"x_unit":"1","y_unit":"°C","relative_error_max":0.1,'
                '"interpolation_policy":"forbidden; observations are not a curve"}'
            ),
            "confidence": "medium",
            "conflict_policy": "source_figure_controls",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("interpolation_policy" in error for error in errors))

    def test_formula_numeric_domain_cannot_be_encoded_as_free_string(self) -> None:
        rows = [{
            "constraint_id": "formula-domain-string",
            "source_fact_ids": "std:p0042:f01:formula",
            "entity_id": "chart:head_ratio",
            "quantity_id": "head_ratio",
            "value_kind": "formula",
            "operator": "EQ",
            "value": "printed_formula",
            "normalized_expression": "y==1640*pow(x,-1.414)+1.48",
            "output_quantity_id": "head_ratio",
            "input_quantity_ids": '["diameter_thickness_ratio"]',
            "symbol_bindings_json": (
                '{"y":"head_ratio","x":"diameter_thickness_ratio"}'
            ),
            "formula_domain_json": '{"domain":"x_gt_0"}',
            "applicability_json": "{}",
            "source_label": "y=1640*x^-1.414+1.48",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_figure_controls",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("structured conditions" in error for error in errors))

    def test_figure_formula_no_extrapolation_requires_structured_domain_conditions(self) -> None:
        rows = [{
            "constraint_id": "curve-formula-domain",
            "source_fact_ids": "std:p0228:f01:plateau",
            "entity_id": "chart:seismic_factor:plateau",
            "quantity_id": "seismic_influence_coefficient",
            "value_kind": "formula",
            "operator": "EQ",
            "value": "printed_curve_formula",
            "normalized_expression": "alpha==eta2*alpha_max",
            "output_quantity_id": "seismic_influence_coefficient",
            "input_quantity_ids": '["eta2","alpha_max"]',
            "symbol_bindings_json": (
                '{"alpha":"seismic_influence_coefficient",'
                '"eta2":"eta2","alpha_max":"alpha_max"}'
            ),
            "formula_domain_json": (
                '{"domain_id":"displayed_regime",'
                '"extrapolation_policy":"forbidden; displayed only"}'
            ),
            "applicability_json": "{}",
            "source_label": "alpha=eta2*alpha_max",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": (
                "Formula source is authoritative; do not extrapolate outside "
                "the printed chart domain."
            ),
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("formula domain conditions" in error for error in errors))
        self.assertTrue(any("extrapolation_policy" in error for error in errors))

    def test_curve_pointset_relation_requires_explicit_extrapolation_policy(self) -> None:
        rows = [{
            "constraint_id": "curve-rel-1",
            "source_fact_ids": "std:p0031:f01:curve-points",
            "entity_id": "chart:arc_length_limit",
            "quantity_id": "chart.curve_pointsets",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "digitized_curve_pointsets",
            "applicability_json": "{}",
            "source_label": "digitized curve pointsets",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "chart:arc_length_limit",
            "object_json": (
                '{"curve_pointsets":{"series_a":[[0.1,10],[1.0,20]]}}'
            ),
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1}'
            ),
            "confidence": "medium",
            "conflict_policy": "source_figure_controls",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("extrapolation_policy" in error for error in errors))

    def test_forbidden_extrapolation_rejects_declared_x_domain_beyond_points(self) -> None:
        rows = [{
            "constraint_id": "curve-domain-gap",
            "source_fact_ids": "figure:curve",
            "entity_id": "figure:curve",
            "quantity_id": "chart.curve_pointsets",
            "value_kind": "relation",
            "operator": "defines",
            "value": "boundary",
            "applicability_json": "{}",
            "source_label": "curve_points",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "figure:curve",
            "object_json": '{"curve_pointsets":{"boundary":[[10,0.001],[30,0.02]]}}',
            "relation_domain_json": (
                '{"condition_logic":"ALL","conditions":['
                '{"quantity_id":"alpha","operator":"BETWEEN",'
                '"value_min":10,"value_max":35,"unit":"degree"}],'
                '"interpolation":"piecewise_linear","x_unit":"degree",'
                '"y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden"}'
            ),
            "confidence": "medium",
            "conflict_policy": "source_figure_controls",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("declared x domain exceeds pointset coverage" in error for error in errors))

    def test_accepts_replayable_curve_pointset_relation(self) -> None:
        rows = [{
            "constraint_id": "curve-rel-ok",
            "source_fact_ids": "std:p0031:f01:curve-points",
            "entity_id": "chart:arc_length_limit",
            "quantity_id": "chart.curve_pointsets",
            "value_kind": "relation",
            "operator": "EQ",
            "value": "digitized_curve_pointsets",
            "applicability_json": "{}",
            "source_label": "digitized curve pointsets",
            "predicate_id": "standard.has_curve_pointsets",
            "subject_id": "chart:arc_length_limit",
            "object_json": (
                '{"curve_pointsets":{"series_a":[[0.1,10],[1.0,20]]}}'
            ),
            "relation_domain_json": (
                '{"interpolation":"piecewise_linear",'
                '"x_unit":"1","y_unit":"1","relative_error_max":0.1,'
                '"extrapolation_policy":"forbidden"}'
            ),
            "confidence": "medium",
            "conflict_policy": "source_figure_controls",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_rejects_opaque_table_reference_in_applicability_value(self) -> None:
        rows = [{
            "constraint_id": "c-app-reference",
            "source_fact_ids": "std:p0023:t01:note-a",
            "entity_id": "heat_treatment:single_tempering",
            "quantity_id": "single_tempering_temperature",
            "value_kind": "range",
            "operator": "BETWEEN",
            "value_min": "620",
            "value_max": "720",
            "source_unit": "℃",
            "normalized_unit": "°C",
            "normalized_value_min": "620",
            "normalized_value_max": "720",
            "applicability_json": (
                '{"condition_logic":"ALL","conditions":['
                '{"quantity_id":"nickel_content","operator":"EQ",'
                '"value":"table_4_lower_limit"}]}'
            ),
            "source_label": "单次回火条件",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("value_ref" in error for error in errors))

    def test_accepts_structured_quantity_reference_condition(self) -> None:
        rows = [{
            "constraint_id": "c-app-reference-ok",
            "source_fact_ids": "std:p0023:t01:note-a",
            "entity_id": "heat_treatment:single_tempering",
            "quantity_id": "single_tempering_temperature",
            "value_kind": "range",
            "operator": "BETWEEN",
            "value_min": "620",
            "value_max": "720",
            "source_unit": "℃",
            "normalized_unit": "°C",
            "normalized_value_min": "620",
            "normalized_value_max": "720",
            "applicability_json": (
                '{"condition_logic":"ALL","conditions":['
                '{"quantity_id":"nickel_content","operator":"EQ",'
                '"value_ref":{"quantity_id":"grade.nickel_lower_limit",'
                '"source_fact_ids":["std:table4:grade-row:nickel-min"],'
                '"unit":"%"}}]}'
            ),
            "source_label": "单次回火条件",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_rejects_numeric_applicability_hidden_as_free_text(self) -> None:
        rows = [{
            "constraint_id": "c-app-1",
            "source_fact_ids": "std:p0094:t01:r02:c02",
            "entity_id": "impeller:anchor_frame",
            "quantity_id": "base_fluid_radial_force_coefficient",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "0.08",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "0.08",
            "applicability_json": '{"n0_times_n_over_nk":"≤0.5"}',
            "source_label": "基本流体径向力系数",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("numeric applicability" in error for error in errors))

    def test_numeric_applicability_condition_requires_quantity_operator_value_and_unit(self) -> None:
        rows = [{
            "constraint_id": "c-app-2",
            "source_fact_ids": "std:p0094:t01:r02:c02",
            "entity_id": "impeller:anchor_frame",
            "quantity_id": "base_fluid_radial_force_coefficient",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "0.08",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "0.08",
            "applicability_json": (
                '{"conditions":[{"quantity_id":"n0_times_n_over_nk",'
                '"operator":"LE","value":0.5}]}'
            ),
            "source_label": "基本流体径向力系数",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("condition needs unit" in error for error in errors))

    def test_applicability_condition_list_requires_explicit_boolean_logic(self) -> None:
        rows = [{
            "constraint_id": "c-app-logic",
            "source_fact_ids": "std:p0097:t01:r05:c01",
            "entity_id": "vessel:vacuum",
            "quantity_id": "K3",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "0.30",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "0.30",
            "applicability_json": (
                '{"conditions":[{"quantity_id":"equipment_pressure",'
                '"operator":"BETWEEN","value_min":0.1,"value_max":0.6,'
                '"unit":"MPa"},{"quantity_id":"agitator_speed",'
                '"operator":"LE","value":100,"unit":"r/min"}]}'
            ),
            "source_label": "K3系数",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("condition_logic" in error for error in errors))

    def test_accepts_machine_replayable_numeric_applicability_condition(self) -> None:
        rows = [{
            "constraint_id": "c-app-3",
            "source_fact_ids": "std:p0094:t01:r02:c02",
            "entity_id": "impeller:anchor_frame",
            "quantity_id": "base_fluid_radial_force_coefficient",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "0.08",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "0.08",
            "applicability_json": (
                '{"condition_logic":"ALL","conditions":['
                '{"quantity_id":"n0_times_n_over_nk",'
                '"operator":"LE","value":0.5,"unit":"1"}],'
                '"impeller_type":"anchor_frame","interpolation":"not_asserted"}'
            ),
            "source_label": "基本流体径向力系数",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_accepts_linked_range_constraint(self) -> None:
        rows = [{
            "constraint_id": "c-1",
            "source_fact_ids": "std:p0102:t01:r03:c04",
            "entity_id": "impeller:bent_open_turbine",
            "quantity_id": "fluid.dynamic_viscosity",
            "value_kind": "range",
            "operator": "LT",
            "value": "",
            "value_min": "",
            "value_max": "10000",
            "value_list": "",
            "source_unit": "mPa.s",
            "normalized_unit": "Pa.s",
            "normalized_value": "10",
            "normalized_value_min": "",
            "normalized_value_max": "10",
            "applicability_json": '{"impeller_type":"bent_open_turbine"}',
            "source_label": "<1×10⁴ mPa·s",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_ordinal_requires_explicit_versioned_mapping(self) -> None:
        rows = [{
            "constraint_id": "c-2",
            "source_fact_ids": "std:p0102:t01:r03:c07",
            "entity_id": "impeller:bent_open_turbine",
            "quantity_id": "mixing.shear_intensity",
            "value_kind": "ordinal",
            "operator": "EQ",
            "value": "3",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "3",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": '{"operation":"gas_dispersion"}',
            "source_label": "剪切力高",
            "model_mapping_version": "",
            "confidence": "MODEL_MAPPED",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("model_mapping_version" in error for error in errors))

    def test_range_rejects_reversed_bounds(self) -> None:
        rows = [{
            "constraint_id": "c-3",
            "source_fact_ids": "std:p0102:t01:r03:c05",
            "entity_id": "impeller:bent_open_turbine",
            "quantity_id": "geometry.impeller_to_vessel_diameter_ratio",
            "value_kind": "range",
            "operator": "BETWEEN",
            "value": "",
            "value_min": "0.8",
            "value_max": "0.2",
            "value_list": "",
            "source_unit": "1",
            "normalized_unit": "1",
            "normalized_value": "",
            "normalized_value_min": "0.8",
            "normalized_value_max": "0.2",
            "applicability_json": "{}",
            "source_label": "0.20～0.80",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("value_min" in error for error in errors))

    def test_rejects_numeric_looking_source_as_categorical(self) -> None:
        rows = [{
            "constraint_id": "c-4",
            "source_fact_ids": "std:p0102:t01:r03:c04",
            "entity_id": "impeller:bent_open_turbine",
            "quantity_id": "fluid.dynamic_viscosity",
            "value_kind": "categorical",
            "operator": "source_literal_only",
            "value": '{"unit":"mPa.s"}',
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": "{}",
            "source_label": "<1×10⁴ mPa·s",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("numeric-looking" in error for error in errors))

    def test_converted_range_requires_normalized_bounds(self) -> None:
        rows = [{
            "constraint_id": "c-5",
            "source_fact_ids": "std:p0101:t01:r02:c06",
            "entity_id": "impeller:paddle",
            "quantity_id": "rotation.speed",
            "value_kind": "range",
            "operator": "BETWEEN",
            "value": "",
            "value_min": "60",
            "value_max": "120",
            "value_list": "",
            "source_unit": "r/min",
            "normalized_unit": "s^-1",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": "{}",
            "source_label": "60～120 r/min",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("normalized_value_min" in error for error in errors))

    def test_rejects_non_executable_placeholder_as_model_constraint(self) -> None:
        rows = [{
            "constraint_id": "c-6",
            "source_fact_ids": "sf-6",
            "entity_id": "std:p0020:r01",
            "quantity_id": "source_cell.c01",
            "value_kind": "categorical",
            "operator": "source_cell_text",
            "value": "类 型",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": '{"execution_gate":"visual_cell_QA_required"}',
            "source_label": "类 型",
            "model_mapping_version": "",
            "confidence": "LOW_TABLE_BBOX_ONLY",
            "conflict_policy": "not_executable_until_visual_cell_QA",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("non-executable placeholder" in error for error in errors))

    def test_range_bearing_enumeration_must_be_split(self) -> None:
        rows = [{
            "constraint_id": "c-7",
            "source_fact_ids": "std:p0102:r03:c05",
            "entity_id": "impeller:bent_open_turbine",
            "quantity_id": "geometry.blade_count",
            "value_kind": "enumeration",
            "operator": "IN",
            "value": "",
            "value_min": "",
            "value_max": "",
            "value_list": "[3,16,3,4,6,8]",
            "source_unit": "count",
            "normalized_unit": "count",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": "{}",
            "source_label": "z=3～16（3、4、6、8居多）",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("range-bearing" in error for error in errors))

    def test_formula_requires_machine_expression_and_symbol_contract(self) -> None:
        rows = [{
            "constraint_id": "c-8",
            "source_fact_ids": "sf-8",
            "entity_id": "closure:type_1",
            "quantity_id": "geometry.closure_thickness",
            "value_kind": "formula",
            "operator": "=",
            "value": "t_rc≥t_rj",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "",
            "output_quantity_id": "",
            "input_quantity_ids": "",
            "symbol_bindings_json": "",
            "formula_domain_json": "",
            "applicability_json": "{}",
            "source_label": "t_rc≥t_rj",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("normalized_expression" in error for error in errors))

    def test_accepts_atomic_machine_formula(self) -> None:
        rows = [{
            "constraint_id": "c-9",
            "source_fact_ids": "sf-9",
            "entity_id": "closure:type_1",
            "quantity_id": "geometry.closure_thickness",
            "value_kind": "formula",
            "operator": "GE",
            "value": "t_rc≥t_rj",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm",
            "normalized_unit": "mm",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "t_rc >= t_rj",
            "output_quantity_id": "geometry.closure_thickness",
            "input_quantity_ids": '["geometry.jacket_required_thickness"]',
            "symbol_bindings_json": '{"t_rc":"geometry.closure_thickness","t_rj":"geometry.jacket_required_thickness"}',
            "formula_domain_json": '{"all_nonnegative":true}',
            "applicability_json": '{"jacket_type":1}',
            "source_label": "t_rc≥t_rj",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_rejects_compound_formula_as_one_constraint(self) -> None:
        rows = [{
            "constraint_id": "c-10",
            "source_fact_ids": "sf-10",
            "entity_id": "closure:type_4",
            "quantity_id": "weld.geometry",
            "value_kind": "formula",
            "operator": "RELATION",
            "value": "Y≥min(0.75t_c,0.75t_s); c≥0.7Y; Z≥t_j",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm",
            "normalized_unit": "mm",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "Y >= min(0.75*t_c,0.75*t_s)",
            "output_quantity_id": "weld.leg_y",
            "input_quantity_ids": '["geometry.t_c","geometry.t_s"]',
            "symbol_bindings_json": '{"Y":"weld.leg_y","t_c":"geometry.t_c","t_s":"geometry.t_s"}',
            "formula_domain_json": '{"all_nonnegative":true}',
            "applicability_json": "{}",
            "source_label": "Y≥min(0.75t_c,0.75t_s); c≥0.7Y; Z≥t_j",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("compound formula" in error for error in errors))

    def test_rejects_syntactically_invalid_machine_expression(self) -> None:
        rows = [{
            "constraint_id": "c-11",
            "source_fact_ids": "sf-11",
            "entity_id": "closure:type_1",
            "quantity_id": "geometry.closure_thickness",
            "value_kind": "formula",
            "operator": "GE",
            "value": "t_rc≥t_rj",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm",
            "normalized_unit": "mm",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "t_rc >=",
            "output_quantity_id": "geometry.closure_thickness",
            "input_quantity_ids": '["geometry.jacket_required_thickness"]',
            "symbol_bindings_json": '{"t_rc":"geometry.closure_thickness","t_rj":"geometry.jacket_required_thickness"}',
            "formula_domain_json": "{}",
            "applicability_json": "{}",
            "source_label": "t_rc≥t_rj",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("parseable" in error for error in errors))

    def test_relation_requires_controlled_predicate_contract(self) -> None:
        rows = [{
            "constraint_id": "c-12",
            "source_fact_ids": "sf-12",
            "entity_id": "symbol:A1",
            "quantity_id": "symbol.definition",
            "value_kind": "relation",
            "operator": "defines",
            "value": "短边侧板上加强件的横截面积，mm²",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "predicate_id": "",
            "subject_id": "",
            "object_json": "",
            "relation_domain_json": "",
            "applicability_json": "{}",
            "source_label": "A1",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("predicate contract" in error for error in errors))

    def test_accepts_controlled_relation(self) -> None:
        rows = [{
            "constraint_id": "c-13",
            "source_fact_ids": "sf-13",
            "entity_id": "symbol:A1",
            "quantity_id": "symbol.definition",
            "value_kind": "relation",
            "operator": "defines",
            "value": "短边侧板上加强件的横截面积，mm²",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "predicate_id": "defines_symbol",
            "subject_id": "symbol:A1",
            "object_json": '{"quantity_id":"geometry.reinforcement_area_short_side","unit":"mm2"}',
            "relation_domain_json": '{"standard":"GB/T 150.3-2024"}',
            "applicability_json": "{}",
            "source_label": "A1",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_relation_rejects_source_text_as_only_machine_object(self) -> None:
        rows = [{
            "constraint_id": "c-rel-text-only",
            "source_fact_ids": "sf-rel-text-only",
            "entity_id": "operation:homogeneous_low_viscosity",
            "quantity_id": "selection.recommended_impeller",
            "value_kind": "relation",
            "operator": "defines",
            "value": "推进式、轴流旋桨及涡轮式等",
            "predicate_id": "has_recommended_impeller",
            "subject_id": "operation:homogeneous_low_viscosity",
            "object_json": '{"source_text":"推进式、轴流旋桨及涡轮式等"}',
            "relation_domain_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "applicability_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "source_label": "推荐搅拌桨",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("controlled machine payload" in error for error in errors))

    def test_recommended_impeller_relation_rejects_opaque_sentence_id(self) -> None:
        rows = [{
            "constraint_id": "c-rel-opaque",
            "source_fact_ids": "sf-rel-opaque",
            "entity_id": "operation:homogeneous_low_viscosity",
            "quantity_id": "selection.recommended_impeller",
            "value_kind": "relation",
            "operator": "defines",
            "value": "推进式、轴流旋桨及涡轮式等",
            "predicate_id": "has_recommended_impeller",
            "subject_id": "operation:homogeneous_low_viscosity",
            "object_json": (
                '{"source_text":"推进式、轴流旋桨及涡轮式等",'
                '"impeller_recommendation_id":"has_recommended_impeller:'
                'homogeneous_low_viscosity"}'
            ),
            "relation_domain_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "applicability_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "source_label": "推荐搅拌桨",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        errors = validate_model_rows(rows)
        self.assertTrue(any("impeller_type_ids" in error for error in errors))

    def test_accepts_atomic_recommended_impeller_ids_with_source_text(self) -> None:
        rows = [{
            "constraint_id": "c-rel-atomic",
            "source_fact_ids": "sf-rel-atomic",
            "entity_id": "operation:homogeneous_low_viscosity",
            "quantity_id": "selection.recommended_impeller",
            "value_kind": "relation",
            "operator": "defines",
            "value": "推进式、轴流旋桨及涡轮式等",
            "predicate_id": "has_recommended_impeller",
            "subject_id": "operation:homogeneous_low_viscosity",
            "object_json": (
                '{"source_text":"推进式、轴流旋桨及涡轮式等",'
                '"impeller_type_ids":["impeller:propeller",'
                '"impeller:axial_flow_propeller","impeller:turbine_unspecified"]}'
            ),
            "relation_domain_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "applicability_json": '{"operation_id":"homogeneous_low_viscosity"}',
            "source_label": "推荐搅拌桨",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }]
        self.assertEqual(validate_model_rows(rows), [])

    def test_numeric_relation_must_be_decomposed(self) -> None:
        row = {
            "constraint_id": "c-14",
            "source_fact_ids": "sf-14",
            "entity_id": "structure:a",
            "quantity_id": "structure.requirement",
            "value_kind": "relation",
            "operator": "defines",
            "value": "最小为2t_c，但不需超过13 mm",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "",
            "normalized_unit": "",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "predicate_id": "has_requirement",
            "subject_id": "structure:a",
            "object_json": '{"text":"最小为2t_c，但不需超过13 mm"}',
            "relation_domain_json": "{}",
            "applicability_json": "{}",
            "source_label": "最小为2t_c，但不需超过13 mm",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }
        errors = validate_model_rows([row])
        self.assertTrue(any("numeric relation" in error for error in errors))

    def test_hollow_applicability_does_not_trigger_low_confidence_marker(self) -> None:
        row = {
            "constraint_id": "c-15",
            "source_fact_ids": "sf-15",
            "entity_id": "shaft:hollow",
            "quantity_id": "shaft.straightness_tolerance",
            "value_kind": "numeric",
            "operator": "LT",
            "value": "0.1",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm/m",
            "normalized_unit": "mm/m",
            "normalized_value": "0.1",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": '{"shaft_type":"hollow","hollow_shaft_segment":"machined","execution_gate":"project_authority_and_equipment_scope_required"}',
            "source_label": "空心轴<0.1 mm/m",
            "model_mapping_version": "",
            "confidence": "HIGH_VISUAL_READ",
            "conflict_policy": "source_faithful; project_authority_and_equipment_scope_required",
        }
        self.assertEqual(validate_model_rows([row]), [])

    def test_accepts_trigonometric_formula_with_explicit_angle_domain(self) -> None:
        row = {
            "constraint_id": "c-16",
            "source_fact_ids": "sf-16",
            "entity_id": "impeller:geometry",
            "quantity_id": "geometry.beta",
            "value_kind": "formula",
            "operator": "EQ",
            "value": "β=arctg(D_j/(πd_1))",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "rad",
            "normalized_unit": "rad",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "beta == atan(D_j/(pi*d_1))",
            "output_quantity_id": "geometry.beta",
            "input_quantity_ids": '["geometry.impeller_diameter","geometry.d1"]',
            "symbol_bindings_json": '{"beta":"geometry.beta","D_j":"geometry.impeller_diameter","d_1":"geometry.d1"}',
            "formula_domain_json": '{"angle_unit":"rad","source_function_aliases":{"arctg":"atan"}}',
            "applicability_json": "{}",
            "source_label": "β=arctg(D_j/(πd_1))",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }
        self.assertEqual(validate_model_rows([row]), [])

    def test_trigonometric_formula_requires_angle_domain(self) -> None:
        row = {
            "constraint_id": "c-17",
            "source_fact_ids": "sf-17",
            "entity_id": "impeller:geometry",
            "quantity_id": "geometry.b",
            "value_kind": "formula",
            "operator": "EQ",
            "value": "b=2R_b sin²θ",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm",
            "normalized_unit": "mm",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "b == 2*R_b*sin(theta)**2",
            "output_quantity_id": "geometry.b",
            "input_quantity_ids": '["geometry.R_b","geometry.theta"]',
            "symbol_bindings_json": '{"b":"geometry.b","R_b":"geometry.R_b","theta":"geometry.theta"}',
            "formula_domain_json": "{}",
            "applicability_json": "{}",
            "source_label": "b=2R_b sin²θ",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }
        errors = validate_model_rows([row])
        self.assertTrue(any("angle_unit" in error for error in errors))

    def test_formula_operator_must_match_normalized_comparison(self) -> None:
        row = {
            "constraint_id": "c-18",
            "source_fact_ids": "sf-18",
            "entity_id": "closure:type_1",
            "quantity_id": "geometry.closure_thickness",
            "value_kind": "formula",
            "operator": "EQ",
            "value": "t_rc≥t_rj",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm",
            "normalized_unit": "mm",
            "normalized_value": "",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "normalized_expression": "t_rc >= t_rj",
            "output_quantity_id": "geometry.closure_thickness",
            "input_quantity_ids": '["geometry.jacket_required_thickness"]',
            "symbol_bindings_json": '{"t_rc":"geometry.closure_thickness","t_rj":"geometry.jacket_required_thickness"}',
            "formula_domain_json": "{}",
            "applicability_json": "{}",
            "source_label": "t_rc≥t_rj",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }
        errors = validate_model_rows([row])
        self.assertTrue(any("operator does not match" in error for error in errors))

    def test_same_unit_numeric_normalization_must_preserve_value(self) -> None:
        row = {
            "constraint_id": "c-19",
            "source_fact_ids": "sf-19",
            "entity_id": "shaft:solid",
            "quantity_id": "shaft.straightness_tolerance",
            "value_kind": "numeric",
            "operator": "LT",
            "value": "0.1",
            "value_min": "",
            "value_max": "",
            "value_list": "",
            "source_unit": "mm/m",
            "normalized_unit": "mm/m",
            "normalized_value": "1.0",
            "normalized_value_min": "",
            "normalized_value_max": "",
            "applicability_json": "{}",
            "source_label": "<0.1 mm/m",
            "model_mapping_version": "",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_specificity_then_conservative",
        }
        errors = validate_model_rows([row])
        self.assertTrue(any("same-unit normalized_value" in error for error in errors))

    def test_rejects_incorrect_registered_unit_conversion(self) -> None:
        row = {
            "constraint_id": "c-unit-wrong",
            "source_fact_ids": "sf-unit-wrong",
            "entity_id": "geometry:eccentricity",
            "quantity_id": "geometry.eccentricity",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "100",
            "source_unit": "mm",
            "normalized_unit": "m",
            "normalized_value": "100",
            "applicability_json": "{}",
            "source_label": "偏心距100 mm",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }
        errors = validate_model_rows([row])
        self.assertTrue(any("unit conversion" in error for error in errors))

    def test_accepts_registered_unit_conversion(self) -> None:
        row = {
            "constraint_id": "c-unit-correct",
            "source_fact_ids": "sf-unit-correct",
            "entity_id": "geometry:eccentricity",
            "quantity_id": "geometry.eccentricity",
            "value_kind": "numeric",
            "operator": "EQ",
            "value": "100",
            "source_unit": "mm",
            "normalized_unit": "m",
            "normalized_value": "0.1",
            "applicability_json": "{}",
            "source_label": "偏心距100 mm",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }
        self.assertEqual(validate_model_rows([row]), [])

    def test_accepts_degree_to_radian_range_conversion(self) -> None:
        row = {
            "constraint_id": "c-unit-angle",
            "source_fact_ids": "sf-unit-angle",
            "entity_id": "support:unreinforced_shell",
            "quantity_id": "support.minimum_contact_angle",
            "value_kind": "range",
            "operator": "GE",
            "value_min": "120",
            "value_max": "",
            "normalized_value_min": "2.0943951023931953",
            "normalized_value_max": "",
            "source_unit": "degree",
            "normalized_unit": "rad",
            "applicability_json": "{}",
            "source_label": "至少120°",
            "confidence": "SOURCE_DIRECT",
            "conflict_policy": "source_faithful",
        }
        self.assertEqual(validate_model_rows([row]), [])


class BidirectionalLinkValidationTests(unittest.TestCase):
    def test_nested_header_source_refs_must_participate_in_bidirectional_links(self) -> None:
        source_rows = [
            {"source_fact_id": "sf_value", "model_constraint_ids": "mc_value"},
            {"source_fact_id": "sf_header", "model_constraint_ids": ""},
        ]
        model_rows = [{
            "constraint_id": "mc_value",
            "source_fact_ids": "sf_value",
            "applicability_json": '{"header_source_fact_ids":["sf_header"]}',
            "object_json": "{}",
            "relation_domain_json": "{}",
        }]
        errors = validate_package_links(source_rows, model_rows)
        self.assertTrue(any("nested source reference is absent from source_fact_ids" in error for error in errors))

    def test_accepts_bidirectional_source_model_links(self) -> None:
        source_rows = [{
            "cell_id": "sf-1",
            "model_constraint_ids": "mc-1",
        }]
        model_rows = [{
            "constraint_id": "mc-1",
            "source_fact_ids": "sf-1",
        }]
        self.assertEqual(validate_package_links(source_rows, model_rows), [])

    def test_rejects_unknown_source_and_missing_backlink(self) -> None:
        source_rows = [{
            "cell_id": "sf-1",
            "model_constraint_ids": "mc-other",
        }]
        model_rows = [{
            "constraint_id": "mc-1",
            "source_fact_ids": "sf-1|sf-missing",
        }]
        errors = validate_package_links(source_rows, model_rows)
        self.assertTrue(any("unknown source_fact_id" in error for error in errors))
        self.assertTrue(any("missing source backlink" in error for error in errors))
        self.assertTrue(any("unknown model_constraint_id" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
