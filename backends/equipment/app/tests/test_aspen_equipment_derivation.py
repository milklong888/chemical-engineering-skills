from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aspen_equipment_derivation as derivation
import customer_delivery


class AspenEquipmentDerivationUnitTests(unittest.TestCase):
    def _derive_test_pipe_stream(
        self,
        *,
        stream_id: str,
        phase: str,
        pressure_mpa: float,
        flow_m3_h: float,
        density_kg_m3: float,
        viscosity_mpa_s: float,
        temperature_c: float = 30.0,
    ) -> dict:
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": stream_id,
                "stream_record_type": "MATERIAL",
                "phase": phase,
                "pressure_mpa": pressure_mpa,
                "temperature_c": temperature_c,
                "volumetric_flow_m3_h": flow_m3_h,
                "mass_flow_kg_h": flow_m3_h * density_kg_m3,
                "density_kg_m3": density_kg_m3,
                "MUMX": viscosity_mpa_s,
                "aspen_raw_paths": {
                    "MUMX": (
                        rf"\Data\Streams\{stream_id}\Output\STRM_UPP"
                        r"\MUMX\MIXED"
                    ),
                },
            },
            {f"stream.{stream_id}.MUMX": "cP"},
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        return derivation.derive_piping(
            stream,
            {"from_block_ids": ["B-1"], "to_block_ids": ["B-2"]},
            {
                "case_id": f"CASE-{stream_id}",
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
            },
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

    def test_history_npsha_pressure_margin_is_converted_with_inlet_density(
        self,
    ) -> None:
        block, block_errors = derivation.normalize_block(
            {
                "block_id": "P-NPSH",
                "block_type": "PUMP",
                "inlet_streams": ["S-IN"],
                "outlet_streams": ["S-OUT"],
                "NPSHA": 63.41,
                # Reproduce an immutable legacy export made before the importer
                # corrected the false ``m`` label.  Raw-history identity must
                # win and make offline repair possible.
                "aspen_raw_paths": {
                    "NPSHA": "raw_history:P-NPSH:NPSH AVAIL",
                },
                "aspen_raw_values": {
                    "NPSHA": {
                        "value": 63.41,
                        "unit": "m",
                        "status": "raw_history_fallback",
                        "history_label": "NPSH AVAIL",
                    },
                },
                "head_m": 100.0,
                "efficiency_percent": 70.0,
            },
            {"block.P-NPSH.NPSHA": "m"},
        )
        self.assertEqual(block_errors, [])
        self.assertNotIn("npsha_m", block)
        self.assertAlmostEqual(block["npsha_pressure_kpa"], 63.41)
        self.assertEqual(
            block["_sources"]["npsha_pressure_kpa"]["origin"],
            "ASPEN_RAW_HISTORY_PRESSURE_MARGIN",
        )
        self.assertTrue(
            block["_sources"]["npsha_pressure_kpa"][
                "legacy_export_unit_reinterpreted_as_kpa"
            ]
        )
        self.assertEqual(
            block["_sources"]["npsha_pressure_kpa"][
                "hash_bound_export_raw_unit"
            ],
            "m",
        )
        self.assertEqual(
            block["_sources"]["npsha_pressure_kpa"]["transform"],
            "legacy_export_unit_reinterpreted_as_kPa_by_"
            "hash_bound_NPSH_AVAIL_quantity_identity",
        )

        inlet, inlet_errors = derivation.normalize_stream(
            {
                "stream_id": "S-IN",
                "phase": "liquid",
                "pressure_mpa": 1.2,
                "temperature_c": 25.0,
                "volumetric_flow_m3_h": 10.0,
                "liquid_volumetric_flow_m3_h": 10.0,
                "mass_flow_kg_h": 4_865.89,
                "density_kg_m3": 486.589,
                "MUMX": 0.4,
            },
            {"stream.S-IN.MUMX": "cP"},
        )
        outlet, outlet_errors = derivation.normalize_stream(
            {
                "stream_id": "S-OUT",
                "phase": "liquid",
                "pressure_mpa": 1.7,
                "temperature_c": 26.0,
                "volumetric_flow_m3_h": 10.0,
                "liquid_volumetric_flow_m3_h": 10.0,
                "mass_flow_kg_h": 4_865.89,
                "density_kg_m3": 486.589,
                "MUMX": 0.4,
            },
            {"stream.S-OUT.MUMX": "cP"},
        )
        self.assertEqual(inlet_errors + outlet_errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {"equipment_tag": "P-NPSH"},
            {"S-IN": inlet, "S-OUT": outlet},
            {"case_id": "NPSH", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )
        canonical = result["canonical_match_input"]
        expected = 63.41 * 1000.0 / (486.589 * 9.80665)
        self.assertAlmostEqual(canonical["npsha_m"], expected)
        self.assertEqual(
            canonical["pump_npsha_process_audit"]["status"],
            "SCREENING_VALUE_PHYSICALLY_PLAUSIBLE",
        )
        npsh_lineage = next(
            item
            for item in result["parameter_lineage"]
            if item.get("target_field") == "npsha_m"
        )
        self.assertEqual(
            npsh_lineage["result_status"],
            "DERIVED_FROM_ASPEN_HISTORY_PRESSURE_MARGIN",
        )

    def test_pump_wnet_is_electrical_not_shaft_power(
        self,
    ) -> None:
        block, errors = derivation.normalize_block(
            {
                "block_id": "P-POWER",
                "block_type": "PUMP",
                "WNET": 4316.0,
                "BRAKE_POWER": 4230.0,
                "FLUID_POWER": 3173.0,
                "CEFF": 0.75,
                "DEFF": 0.98,
                "aspen_raw_paths": {
                    "WNET": r"\Data\Blocks\P-POWER\Output\WNET",
                    "BRAKE_POWER": "raw_history:P-POWER:BRAKE PWR",
                    "FLUID_POWER": "raw_history:P-POWER:FLUID PWR",
                    "CEFF": r"\Data\Blocks\P-POWER\Input\SEFF",
                    "DEFF": r"\Data\Blocks\P-POWER\Input\DEFF",
                },
            },
            {
                "block.P-POWER.WNET": "W",
                "block.P-POWER.BRAKE_POWER": "W",
                "block.P-POWER.FLUID_POWER": "W",
                "block.P-POWER.CEFF": "fraction",
                "block.P-POWER.DEFF": "fraction",
            },
        )

        self.assertEqual(errors, [])
        self.assertAlmostEqual(block["hydraulic_power_kw"], 3.173)
        self.assertAlmostEqual(block["shaft_power_kw"], 4.230)
        self.assertAlmostEqual(block["electrical_power_kw"], 4.316)
        self.assertAlmostEqual(block["efficiency_percent"], 75.0)
        self.assertAlmostEqual(block["driver_efficiency_percent"], 98.0)
        self.assertEqual(
            block["_sources"]["electrical_power_kw"]["source_field"],
            "WNET",
        )
        self.assertEqual(
            block["_sources"]["electrical_power_kw"]["origin"],
            "ASPEN_PUMP_ELECTRICAL_INPUT_POWER",
        )
        self.assertEqual(
            block["_sources"]["efficiency_percent"]["origin"],
            "ASPEN_PUMP_HYDRAULIC_EFFICIENCY",
        )
        self.assertEqual(
            block["_sources"]["efficiency_percent"]["evidence_scope"],
            "PUMP_PROCESS_POWER_BALANCE",
        )

    def test_raw_history_pump_power_channels_and_deff_are_separated(
        self,
    ) -> None:
        history = """
    BLOCK P-1 PUMP
        PARAM PRES=25. EFF=0.75 DEFF=0.98 PUMP-TYPE=PUMP
        PERFOR-PARAM ACT-SH-SPEED=2800.0 NCURVES=3

    DESIGN-SPEC POUT
        VARY BLOCK-VAR BLOCK=P-1 VARIABLE=ACT-SH-SPEED
            SENTENCE=PERFOR-PARAM UOM="rpm"
        LIMITS "50" "2800" STEP-SIZE=.10

      GENERATING RESULTS FOR UOS BLOCK P-1 MODEL: PUMP
      FLUID PWR  =   3173.     , BRAKE PWR  =   4230.     , ELEC PWR   =   4316.
      NPSH AVAIL =   63.41
"""
        parsed = derivation.parse_raw_history_pump_power(history)

        self.assertAlmostEqual(parsed["P-1"]["hydraulic_power_kw"], 3.173)
        self.assertAlmostEqual(parsed["P-1"]["shaft_power_kw"], 4.230)
        self.assertAlmostEqual(parsed["P-1"]["electrical_power_kw"], 4.316)
        self.assertAlmostEqual(
            parsed["P-1"]["driver_efficiency_percent"],
            98.0,
        )
        self.assertAlmostEqual(
            parsed["P-1"][
                "aspen_configured_shaft_speed_candidate_rpm"
            ],
            2800.0,
        )
        self.assertTrue(
            parsed["P-1"][
                "configured_speed_varied_by_design_spec"
            ]
        )
        self.assertEqual(
            parsed["P-1"][
                "configured_speed_design_spec_lower_limit_rpm"
            ],
            50.0,
        )
        self.assertEqual(
            parsed["P-1"][
                "configured_speed_design_spec_upper_limit_rpm"
            ],
            2800.0,
        )
        self.assertFalse(
            parsed["P-1"]["configured_speed_is_solved_actual"]
        )
        self.assertRegex(parsed["P-1"]["audit_sha256"], r"^[A-F0-9]{64}$")

    def test_pump_power_pass_requires_both_complete_balances(self) -> None:
        streams: dict[str, dict[str, object]] = {}
        for stream_id, pressure in (("P-IN", 0.2), ("P-OUT", 0.8)):
            stream, errors = derivation.normalize_stream(
                {
                    "stream_id": stream_id,
                    "phase": "liquid",
                    "pressure_mpa": pressure,
                    "temperature_c": 30.0,
                    "volumetric_flow_m3_h": 25.0,
                    "liquid_volumetric_flow_m3_h": 25.0,
                    "mass_flow_kg_h": 20_000.0,
                    "density_kg_m3": 800.0,
                    "MUMX": 0.5,
                },
                {f"stream.{stream_id}.MUMX": "cP"},
            )
            self.assertEqual(errors, [])
            streams[stream_id] = stream
        source = Path(__file__).resolve()

        def power_audit(
            *,
            include_electrical_channel: bool,
        ) -> dict[str, object]:
            raw_block: dict[str, object] = {
                "block_id": (
                    "P-COMPLETE"
                    if include_electrical_channel
                    else "P-INCOMPLETE"
                ),
                "block_type": "PUMP",
                "inlet_streams": ["P-IN"],
                "outlet_streams": ["P-OUT"],
                "FLUID_POWER": 3173.0,
                "BRAKE_POWER": 4230.0,
                "CEFF": 0.75,
            }
            units = {
                f"block.{raw_block['block_id']}.FLUID_POWER": "W",
                f"block.{raw_block['block_id']}.BRAKE_POWER": "W",
                f"block.{raw_block['block_id']}.CEFF": "fraction",
            }
            if include_electrical_channel:
                raw_block["WNET"] = 4316.0
                raw_block["DEFF"] = 0.98
                units[f"block.{raw_block['block_id']}.WNET"] = "W"
                units[f"block.{raw_block['block_id']}.DEFF"] = "fraction"
            block, block_errors = derivation.normalize_block(
                raw_block,
                units,
            )
            self.assertEqual(block_errors, [])
            result = derivation.derive_equipment(
                block,
                {"equipment_tag": raw_block["block_id"]},
                streams,
                {"case_id": "P-POWER", "pressure_basis": "absolute"},
                source,
                derivation.sha256_file(source),
                derivation.matcher.load_rules(),
                derivation.matcher.load_graph(),
            )
            return result["canonical_match_input"][
                "pump_power_process_audit"
            ]

        complete = power_audit(include_electrical_channel=True)
        self.assertEqual(
            complete["status"],
            "PASS_ASPEN_POWER_CHANNELS_SEPARATED_AND_BALANCED",
        )
        self.assertTrue(complete["both_balances_complete"])
        self.assertEqual(complete["calculated_balance_count"], 2)
        self.assertEqual(complete["missing_power_channels"], [])

        incomplete = power_audit(include_electrical_channel=False)
        self.assertEqual(
            incomplete["status"],
            "OPEN_INCOMPLETE_PUMP_POWER_CHANNELS",
        )
        self.assertFalse(incomplete["both_balances_complete"])
        self.assertEqual(incomplete["calculated_balance_count"], 1)
        self.assertIn(
            "electrical_power_kw",
            incomplete["missing_power_channels"],
        )

    def test_nonpositive_npsha_retains_pump_type_but_blocks_ready_status(
        self,
    ) -> None:
        block, block_errors = derivation.normalize_block(
            {
                "block_id": "P-ZERO-NPSH",
                "block_type": "PUMP",
                "inlet_streams": ["IN"],
                "outlet_streams": ["OUT"],
                "NPSHA": 0.0,
                "aspen_raw_paths": {
                    "NPSHA": "raw_history:P-ZERO-NPSH:NPSH AVAIL",
                },
                "aspen_raw_values": {
                    "NPSHA": {
                        "value": 0.0,
                        "unit": "kPa",
                        "status": "raw_history_pressure_margin_fallback",
                        "quantity_kind": "available_suction_pressure_margin",
                    },
                },
                "head_m": 80.0,
                "efficiency_percent": 65.0,
            },
            {"block.P-ZERO-NPSH.NPSHA": "kPa"},
        )
        self.assertEqual(block_errors, [])
        streams: dict[str, dict[str, object]] = {}
        for stream_id, pressure in (("IN", 0.2), ("OUT", 0.8)):
            stream, errors = derivation.normalize_stream(
                {
                    "stream_id": stream_id,
                    "phase": "liquid",
                    "pressure_mpa": pressure,
                    "temperature_c": 30.0,
                    "volumetric_flow_m3_h": 25.0,
                    "liquid_volumetric_flow_m3_h": 25.0,
                    "mass_flow_kg_h": 20_000.0,
                    "density_kg_m3": 800.0,
                    "MUMX": 0.5,
                },
                {f"stream.{stream_id}.MUMX": "cP"},
            )
            self.assertEqual(errors, [])
            streams[stream_id] = stream
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {"equipment_tag": "P-ZERO-NPSH"},
            streams,
            {"case_id": "ZERO-NPSH", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )
        self.assertEqual(
            result["canonical_match_input"]["pump_npsha_process_audit"][
                "status"
            ],
            "BLOCKED_NONPOSITIVE_NPSHA",
        )
        model = result["match_result"]["model_recommendation"]
        self.assertEqual(
            model["status"],
            "PUMP_TYPE_SELECTED_CAVITATION_BASIS_BLOCKED",
        )
        self.assertEqual(
            model["leading_candidate"]["status"],
            "PUMP_TYPE_RETAINED_NONPOSITIVE_NPSHA_RISK",
        )
        self.assertTrue(
            any(
                item["code"] == "PUMP_NONPOSITIVE_NPSHA_CAVITATION_RISK"
                for item in result["adapter_blockers"]
            )
        )

    def test_programmatic_gas_valve_specification_is_concrete_hash_bound_and_no_liquid_cv(
        self,
    ) -> None:
        source = Path(__file__).resolve()
        source_sha256 = derivation.sha256_file(source)
        inlet_pipe_hash = "A" * 64
        outlet_pipe_hash = "B" * 64

        def pipe_specification(
            *,
            dn: int,
            pressure_class: str,
            specification_sha256: str,
        ) -> dict[str, object]:
            return {
                "programmatic_pipe_specification": {
                    "status": "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
                    "program_specification_sha256": specification_sha256,
                    "fields": {
                        "selected_dn": {"value": dn},
                        "pressure_class": {"value": pressure_class},
                        "material_grade": {"value": "20钢"},
                        "material": {"value": "20钢无缝钢管"},
                    },
                },
            }

        equipment: dict[str, object] = {
            "aspen_block_id": "V-TEST",
            "canonical_match_input": {
                "equipment_tag": "V-TEST",
                "aspen_block_type": "VALVE",
                "equipment_type": "调节阀",
                "process_function": "gas pressure reduction control",
                "phase": "vapor",
                "pressure_basis": "absolute",
                "inlet_pressure_mpa": 1.2,
                "outlet_pressure_mpa": 0.12,
                "pressure_drop_kpa": 1080.0,
                "flow_m3_h": 1_000.0,
                "inlet_temperature_c": 120.0,
                "gas_molecular_weight": 44.0,
            },
            "match_result": {},
            "parameter_lineage": [],
        }
        block = {
            "block_id": "V-TEST",
            "inlet_streams": ["V-IN"],
            "outlet_streams": ["V-OUT"],
        }
        piping_by_stream = {
            "V-IN": pipe_specification(
                dn=20,
                pressure_class="PN16",
                specification_sha256=inlet_pipe_hash,
            ),
            "V-OUT": pipe_specification(
                dn=65,
                pressure_class="PN10",
                specification_sha256=outlet_pipe_hash,
            ),
        }

        specification = derivation.build_programmatic_valve_specification(
            equipment=equipment,
            block=block,
            piping_by_stream=piping_by_stream,
            source_file=source,
            source_sha256=source_sha256,
        )

        self.assertEqual(
            specification["status"],
            "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
        )
        self.assertEqual(
            specification["fields"]["equipment_type"]["value"],
            "多级降压笼式气体调节阀"
            "（低噪声内件方案候选，噪声未校核）",
        )
        self.assertEqual(specification["fields"]["selected_dn"]["value"], 20)
        self.assertEqual(
            specification["fields"]["pressure_class"]["value"],
            "PN16",
        )
        self.assertEqual(
            specification["fields"]["cv"]["value"],
            "OPEN_GAS_COMPRESSIBLE_AND_CHOKED_FLOW_CAPACITY_GATE",
        )
        self.assertNotIsInstance(
            specification["fields"]["cv"]["value"],
            (int, float),
        )
        self.assertAlmostEqual(
            specification["maximum_pressure_drop_screening_audit"][
                "requested_value_kpa"
            ],
            1296.0,
        )
        self.assertAlmostEqual(
            specification["fields"]["maximum_pressure_drop_kpa"][
                "value"
            ],
            1200.0,
        )
        self.assertTrue(
            specification["maximum_pressure_drop_screening_audit"][
                "cap_applied"
            ]
        )
        self.assertFalse(
            specification["maximum_pressure_drop_screening_audit"][
                "formal_shutoff_differential_selected"
            ]
        )
        self.assertEqual(
            specification["adjacent_line_binding"][
                "inlet_pipe_specification_sha256"
            ],
            inlet_pipe_hash,
        )
        self.assertEqual(
            specification["adjacent_line_binding"][
                "outlet_pipe_specification_sha256"
            ],
            outlet_pipe_hash,
        )
        self.assertRegex(
            specification["program_specification_sha256"],
            r"^[A-F0-9]{64}$",
        )
        self.assertNotIn(
            "absolute_inlet_pressure_mpa",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertNotIn(
            "absolute_outlet_pressure_mpa",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertNotIn(
            "inlet_temperature_k",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertNotIn(
            "gas_molecular_weight_kg_kmol",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertIn(
            "specific_heat_ratio",
            specification["formal_readiness"]["open_gates"],
        )
        customer_delivery._verified_programmatic_valve_specification(
            specification
        )

        tampered = json.loads(json.dumps(specification, ensure_ascii=False))
        tampered["fields"]["selected_dn"]["value"] = 25
        with self.assertRaises(customer_delivery.CustomerDeliveryError):
            customer_delivery._verified_programmatic_valve_specification(
                tampered
            )

        liquid_equipment = json.loads(
            json.dumps(equipment, ensure_ascii=False)
        )
        liquid_equipment["canonical_match_input"]["phase"] = "liquid"
        liquid_equipment["match_result"] = {
            "derived_parameters": {"cv": 12.345}
        }
        liquid_specification = (
            derivation.build_programmatic_valve_specification(
                equipment=liquid_equipment,
                block=block,
                piping_by_stream=piping_by_stream,
                source_file=source,
                source_sha256=source_sha256,
            )
        )
        self.assertAlmostEqual(
            liquid_specification["fields"]["cv"]["value"],
            12.345,
        )
        self.assertEqual(
            liquid_specification["fields"]["cv"]["state"],
            "PROGRAM_PRELIMINARY_LIQUID_CV_CALCULATED",
        )
        self.assertEqual(
            liquid_specification["fields"]["capacity_sizing_status"][
                "value"
            ],
            "LIQUID_CV_SCREENING_CALCULATED",
        )

        derivation.apply_programmatic_valve_specification(
            equipment=equipment,
            specification=specification,
            rules=derivation.matcher.load_rules(),
            graph=derivation.matcher.load_graph(),
            source_file=source,
            source_sha256=source_sha256,
        )
        lineage_summary = (
            derivation.refresh_final_parameter_lineage_snapshots(
                equipment=[equipment],
                piping=[],
                piping_state_aliases=[],
            )
        )
        self.assertEqual(lineage_summary["status"], "PASS")
        self.assertEqual(
            lineage_summary["rows"][0]["record_kind"],
            "equipment",
        )
        provenance = equipment["input_provenance"]
        self.assertEqual(
            provenance["lineage_count"],
            len(equipment["parameter_lineage"]),
        )
        self.assertEqual(
            provenance["final_parameter_lineage_sha256"],
            derivation._canonical_sha256(
                equipment["parameter_lineage"]
            ),
        )
        provenance_payload = dict(provenance)
        provenance_sha256 = provenance_payload.pop(
            "final_snapshot_sha256"
        )
        self.assertEqual(
            provenance_sha256,
            derivation._canonical_sha256(provenance_payload),
        )
        self.assertEqual(
            equipment["match_result"]["input_provenance"],
            provenance,
        )
        leading = equipment["match_result"]["model_recommendation"][
            "leading_candidate"
        ]
        self.assertEqual(
            leading["source"]["kind"],
            "deterministic_programmatic_valve_specification",
        )
        self.assertEqual(
            leading["source"]["program_specification_sha256"],
            specification["program_specification_sha256"],
        )
        self.assertEqual(
            equipment["canonical_match_input"]["cv"],
            "OPEN_GAS_COMPRESSIBLE_AND_CHOKED_FLOW_CAPACITY_GATE",
        )
        self.assertFalse(leading["eligible_for_formal_selection"])
        model = equipment["match_result"]["model_recommendation"]
        self.assertEqual(
            model["status"],
            "VALVE_TYPE_SELECTED_CAPACITY_AND_RATING_BLOCKED",
        )
        self.assertEqual(
            model["terminal_selection"]["evidence_class"],
            "J",
        )
        self.assertTrue(model["terminal_selection"]["provisional"])
        self.assertEqual(
            model["terminal_selection"]["status"],
            "PROGRAMMATIC_VALVE_FORM_SELECTED",
        )
        self.assertFalse(
            model["selection_execution"]["formal_selection_executed"]
        )

    def test_bidirectional_com_topology_is_hash_bound_and_fully_checked(self) -> None:
        raw_streams = [
            {
                "stream_id": "FEED",
                "connections": [
                    {"name": "P-1", "value": "DEST"},
                    {"name": "#1", "value": "SOURCE"},
                ],
            },
            {
                "stream_id": "PRODUCT",
                "connections": [
                    {"name": "#0", "value": "DEST"},
                    {"name": "P-1", "value": "SOURCE"},
                ],
            },
        ]
        raw_blocks = [
            {
                "block_id": "P-1",
                "block_type": "PUMP",
                "inlet_streams": ["FEED"],
                "outlet_streams": ["PRODUCT"],
                "connections": [
                    {"name": "FEED", "value": "F(IN)"},
                    {"name": "PRODUCT", "value": "P(OUT)"},
                ],
                "port_detail": [
                    {"port": "F(IN)", "direction": "in", "streams": ["FEED"]},
                    {
                        "port": "P(OUT)",
                        "direction": "out",
                        "streams": ["PRODUCT"],
                    },
                ],
            },
        ]
        blocks = [derivation.normalize_block(raw_blocks[0], {})[0]]

        result = derivation.bidirectional_topology_integrity(
            raw_streams,
            raw_blocks,
            blocks,
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["validated_stream_count"], 2)
        self.assertEqual(result["validated_block_count"], 1)
        self.assertRegex(result["topology_sha256"], r"^[A-F0-9]{64}$")
        self.assertTrue(
            all(
                row["status"] == "PASS"
                and len(row["row_sha256"]) == 64
                for row in result["stream_rows"] + result["block_rows"]
            )
        )

    def test_dirty_history_problem_headers_are_attributed_to_exact_blocks(
        self,
    ) -> None:
        history = """
  *** SEVERE ERROR WHILE EXECUTING UNIT OPERATIONS BLOCK: "C-1" (MODEL:
      "RADFRAC")
      COLUMN INNER LOOP FAILED TO CONVERGE.
  **  ERROR WHILE EXECUTING UNIT OPERATIONS BLOCK: "E-101" (MODEL: "HEATX")
      A TEMPERATURE CROSS WAS DETECTED.
  *   WARNING WHILE EXECUTING UNIT OPERATIONS BLOCK: "P-3" (MODEL: "PUMP")
      NPSH CHECK REQUIRES REVIEW.
"""
        attribution = derivation.parse_raw_history_block_issues(history)

        self.assertEqual(attribution["event_count"], 3)
        self.assertEqual(
            attribution["attributed_counts"],
            {
                "terminal_errors": 0,
                "severe_errors": 1,
                "errors": 1,
                "warnings": 1,
            },
        )
        issues = {
            row["block_id"]: row
            for row in attribution["block_issues"]
        }
        self.assertEqual(
            issues["C-1"]["highest_severity"],
            "severe_error",
        )
        self.assertEqual(issues["C-1"]["models"], ["RADFRAC"])
        self.assertEqual(issues["E-101"]["counts"]["errors"], 1)
        self.assertEqual(issues["P-3"]["counts"]["warnings"], 1)
        self.assertRegex(
            attribution["attribution_sha256"],
            r"^[A-F0-9]{64}$",
        )

    def test_dirty_history_detail_excerpt_is_severity_first(self) -> None:
        warning_rows = "\n".join(
            (
                '  * WARNING WHILE EXECUTING UNIT OPERATIONS BLOCK: "B-1" '
                f'(MODEL: "FLASH2")\n      WARNING DETAIL {index}.'
            )
            for index in range(8)
        )
        history = (
            warning_rows
            + '\n  ** ERROR WHILE EXECUTING UNIT OPERATIONS BLOCK: "B-1" '
            '(MODEL: "FLASH2")\n      ERROR DETAIL MUST SURVIVE.\n'
            + '  *** SEVERE ERROR WHILE EXECUTING UNIT OPERATIONS BLOCK: '
            '"B-1" (MODEL: "FLASH2")\n'
            "      SEVERE DETAIL MUST SURVIVE.\n"
        )

        attribution = derivation.parse_raw_history_block_issues(history)

        row = next(
            item
            for item in attribution["block_issues"]
            if item["block_id"] == "B-1"
        )
        excerpt = row["detail_excerpts"]
        self.assertLessEqual(len(excerpt), 5)
        self.assertIn("SEVERE DETAIL MUST SURVIVE", excerpt[0])
        self.assertIn("ERROR DETAIL MUST SURVIVE", excerpt[1])

    def test_history_parser_attributes_property_and_sensitivity_warnings(
        self,
    ) -> None:
        history = """
  * WARNING IN PHYSICAL PROPERTY SYSTEM WHILE INITIALIZING PROPERTY MODELS
      PROPERTY METHOD EXTRAPOLATION REQUIRES REVIEW.
  * WARNING WHILE EXECUTING SENSITIVITY BLOCK: "S-1" (SNSTVI.5)
      SOME ROWS COMPLETED WITH WARNINGS.
  * WARNING WHILE EXECUTING UNIT OPERATIONS BLOCK: "P-1" (MODEL: "PUMP")
      CURVE RANGE REQUIRES REVIEW.
"""
        attribution = derivation.parse_raw_history_block_issues(history)

        self.assertEqual(attribution["event_count"], 3)
        self.assertEqual(attribution["attributed_counts"]["warnings"], 3)
        issues = {
            row["block_id"]: row
            for row in attribution["block_issues"]
        }
        self.assertEqual(
            issues["__PHYSICAL_PROPERTY_SYSTEM__"]["issue_scopes"],
            ["physical_property_system"],
        )
        self.assertEqual(
            issues["__PHYSICAL_PROPERTY_SYSTEM__"]["models"],
            ["PROPERTY_SYSTEM"],
        )
        self.assertEqual(
            issues["S-1"]["issue_scopes"],
            ["sensitivity_block"],
        )
        self.assertEqual(
            issues["P-1"]["issue_scopes"],
            ["unit_operation_block"],
        )

    def test_dirty_run_gate_caps_equipment_and_adjacent_pipe_to_identity(
        self,
    ) -> None:
        attribution = derivation.parse_raw_history_block_issues(
            """
  ** ERROR WHILE EXECUTING UNIT OPERATIONS BLOCK: "E-1" (MODEL: "HEATER")
     DUTY RESULT IS NOT CONVERGED.
"""
        )
        base_match = derivation.matcher.match_one(
            {
                "aspen_block_type": "HEATER",
                "heat_duty_kw": 100.0,
                "operating_pressure_mpa": 0.3,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
                "temperature_c": 120.0,
            },
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )
        equipment = [{
            "aspen_block_id": "E-1",
            "canonical_match_input": {
                "aspen_block_type": "HEATER",
            },
            "match_result": base_match,
            "evidence_boundary": {},
        }]
        piping = [{
            "stream_id": "S-1",
            "match_result": json.loads(
                json.dumps(base_match, ensure_ascii=False)
            ),
            "pfd_edge_label_data": {
                "details": {
                    "from_block_ids": ["E-1"],
                    "to_block_ids": ["B-2"],
                },
            },
            "evidence_boundary": {},
        }]
        gate = {
            "status": "DIRTY_RUN",
            "counts": {
                "terminal_errors": 0,
                "severe_errors": 0,
                "errors": 1,
                "warnings": 0,
            },
            "bad_blocks": [],
            "run_status_evidence": {
                "status": "RAW_HISTORY_NONZERO_COUNTS",
            },
            "raw_history_attribution": attribution,
        }

        derivation.apply_aspen_run_gate_boundaries(
            equipment=equipment,
            piping=piping,
            gate=gate,
        )

        self.assertEqual(
            equipment[0]["aspen_run_gate"]["local_status"],
            "LOCAL_ASPEN_BLOCK_ERROR",
        )
        self.assertFalse(
            equipment[0]["aspen_run_gate"][
                "process_values_formally_releasable"
            ]
        )
        for row in (equipment[0], piping[0]):
            self.assertTrue(
                row["evidence_boundary"][
                    "affects_aspen_formal_use_gate"
                ]
            )
            model = row["match_result"]["model_recommendation"]
            self.assertEqual(
                model["status"],
                "TYPE_IDENTITY_RETAINED_LOCAL_ASPEN_RUN_ERROR",
            )
            self.assertEqual(
                model["leading_candidate"]["candidate_eligibility"],
                "TYPE_IDENTITY_ONLY_DIRTY_ASPEN_RUN",
            )
            self.assertFalse(
                model["selection_execution"]["formal_selection_executed"]
            )

    def test_bidirectional_com_topology_rejects_stream_block_disagreement(self) -> None:
        raw_streams = [
            {
                "stream_id": "S-1",
                "connections": [
                    {"name": "WRONG-BLOCK", "value": "DEST"},
                    {"name": "#1", "value": "SOURCE"},
                ],
            },
        ]
        raw_blocks = [
            {
                "block_id": "B-1",
                "block_type": "HEATER",
                "inlet_streams": ["S-1"],
                "outlet_streams": [],
                "connections": [{"name": "S-1", "value": "F(IN)"}],
                "port_detail": [
                    {"port": "F(IN)", "direction": "in", "streams": ["S-1"]},
                ],
            },
        ]
        blocks = [derivation.normalize_block(raw_blocks[0], {})[0]]

        result = derivation.bidirectional_topology_integrity(
            raw_streams,
            raw_blocks,
            blocks,
        )

        self.assertEqual(result["status"], "FAILED")
        self.assertIn(
            "TOPOLOGY_STREAM_DESTINATION_BLOCK_MISMATCH",
            {item["code"] for item in result["issues"]},
        )

    def test_legacy_export_never_receives_false_bidirectional_topology_pass(self) -> None:
        raw_streams = [{"stream_id": "S-1"}]
        raw_blocks = [
            {
                "block_id": "B-1",
                "block_type": "HEATER",
                "inlet_streams": ["S-1"],
                "outlet_streams": [],
            },
        ]
        blocks = [derivation.normalize_block(raw_blocks[0], {})[0]]

        result = derivation.bidirectional_topology_integrity(
            raw_streams,
            raw_blocks,
            blocks,
        )

        self.assertEqual(result["status"], "NOT_AVAILABLE_LEGACY_EXPORT")
        self.assertFalse(result["stream_connection_evidence_available"])
        self.assertEqual(result["validated_stream_count"], 0)

    def test_stream_piping_projects_topology_and_closed_composition(self) -> None:
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": "S-1",
                "stream_record_type": "MATERIAL",
                "phase": "liquid",
                "pressure_mpa": 0.3,
                "temperature_c": 30.0,
                "volumetric_flow_m3_h": 12.0,
                "mass_flow_kg_h": 10_000.0,
                "MUMX": 0.27304936,
                "aspen_raw_paths": {
                    "MUMX": r"\Data\Streams\S-1\Output\STRM_UPP\MUMX\MIXED\LIQUID",
                },
                "component_mole_fractions": {
                    "WATER": 0.75,
                    "METHANOL": 0.25,
                },
            },
            {"stream.S-1.MUMX": "cP"},
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_piping(
            stream,
            {"from_block_ids": ["B-1"], "to_block_ids": ["B-2"]},
            {"case_id": "CASE-1", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        canonical = result["canonical_match_input"]
        self.assertEqual(canonical["line_number"], "S-1")
        self.assertEqual(canonical["source_endpoint"], "B-1")
        self.assertEqual(canonical["destination_endpoint"], "B-2")
        self.assertEqual(
            canonical["medium_name"],
            "WATER (75 mol%) + METHANOL (25 mol%)",
        )
        self.assertEqual(
            result["pfd_edge_label_data"]["details"]["values"]["medium_name"],
            canonical["medium_name"],
        )
        self.assertTrue(any(
            item.get("target_field") == "medium_name"
            and item.get("source_file_sha256") == derivation.sha256_file(source)
            for item in result["parameter_lineage"]
        ))
        viscosity_lineage = next(
            item
            for item in result["parameter_lineage"]
            if item.get("target_field") == "dynamic_viscosity_mpa_s"
        )
        self.assertEqual(
            viscosity_lineage["source_path"],
            r"\Data\Streams\S-1\Output\STRM_UPP\MUMX\MIXED\LIQUID",
        )
        self.assertEqual(
            result["pipe_entity_scope"],
            "PFD_MATERIAL_STREAM_SEGMENT",
        )
        self.assertEqual(
            result["pipe_entity_id"],
            "PFD_STREAM:S-1",
        )
        self.assertTrue(result["counted_as_physical_pipe"])
        self.assertFalse(result["alias_only"])
        endpoint_audit = result["endpoint_pressure_drop_audit"]
        self.assertEqual(
            endpoint_audit["status"],
            "OPEN_SINGLE_PFD_STREAM_STATE_HAS_NO_ENDPOINT_PAIR",
        )
        self.assertIsNone(
            endpoint_audit["endpoint_pressure_drop_kpa"]
        )
        self.assertFalse(endpoint_audit["endpoint_complete"])
        self.assertFalse(endpoint_audit["formal_acceptance"])

    def test_pipe_entity_classifier_blocks_ambiguous_multi_pipe_state(
        self,
    ) -> None:
        entity = derivation.classify_pfd_stream_pipe_entity(
            stream_id="S-BRIDGE",
            endpoints={
                "from_block_ids": ["PIPE-A"],
                "to_block_ids": ["PIPE-B"],
            },
            physical_pipe_block_ids={"PIPE-A", "PIPE-B"},
        )

        self.assertTrue(entity["alias_only"])
        self.assertFalse(entity["counted_as_physical_pipe"])
        self.assertFalse(entity["classification_complete"])
        self.assertTrue(entity["requires_manual_entity_resolution"])
        self.assertEqual(
            entity["alias_status"],
            "BLOCKED_MULTIPLE_CANONICAL_PHYSICAL_PIPE_BINDINGS",
        )
        self.assertEqual(
            entity["canonical_pipe_entity_ids"],
            [
                "ASPEN_PIPE_BLOCK:PIPE-A",
                "ASPEN_PIPE_BLOCK:PIPE-B",
            ],
        )

    def test_pipe_standard_objects_remain_separate_preliminary_candidates(
        self,
    ) -> None:
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": "S-DN125",
                "stream_record_type": "MATERIAL",
                "phase": "liquid",
                "pressure_mpa": 0.3,
                "temperature_c": 30.0,
                "volumetric_flow_m3_h": 61.0,
                "mass_flow_kg_h": 61_000.0,
                "density_kg_m3": 1_000.0,
                "MUMX": 0.8,
                "aspen_raw_paths": {
                    "MUMX": (
                        r"\Data\Streams\S-DN125\Output\STRM_UPP"
                        r"\MUMX\MIXED\LIQUID"
                    ),
                },
            },
            {"stream.S-DN125.MUMX": "cP"},
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_piping(
            stream,
            {"from_block_ids": ["B-1"], "to_block_ids": ["B-2"]},
            {"case_id": "CASE-DN125", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        specification = result["programmatic_pipe_specification"]
        fields = specification["fields"]
        self.assertEqual(fields["selected_dn"]["value"], 125)
        self.assertEqual(
            fields["selected_dn"]["state"],
            "PROGRAM_PRELIMINARY_HYDRAULIC_DN_CANDIDATE",
        )
        self.assertAlmostEqual(
            fields["dn_catalog_outer_diameter_mm"]["value"],
            141.3,
        )
        self.assertAlmostEqual(
            fields["selected_outer_diameter_mm"]["value"],
            142.0,
        )
        self.assertAlmostEqual(
            fields["dn_od_approximation_mm"]["value"],
            0.7,
        )
        self.assertEqual(
            fields["schedule_designation"]["value"],
            "NON_SCH_METRIC_OD_X_WALL_PRELIMINARY",
        )
        self.assertIn("non-SCH", fields["wall_series"]["value"])
        self.assertNotIn("外径×壁厚系列", fields["wall_series"]["value"])

        selections = specification["standard_selections"]
        self.assertEqual(
            selections["dn"]["standard_object"],
            "steel_butt_welding_seamless_fittings_not_pipe_product",
        )
        self.assertEqual(
            selections["dn"]["record"]["standard_id"],
            "GB/T 12459-2025",
        )
        self.assertEqual(
            selections["wall"]["standard_object"],
            "seamless_steel_pipe_dimensions_shape_mass_and_tolerances",
        )
        self.assertEqual(
            selections["wall"]["standard_id"],
            "GB/T 17395-2024",
        )
        pairing = specification["cross_standard_pairing"]
        self.assertFalse(pairing["single_standard_combination_claim"])
        self.assertEqual(pairing["formal_release_status"], "BLOCKED")
        self.assertIn("APPROXIMATE", pairing["status"])

        self.assertEqual(
            fields["pressure_class"]["state"],
            "PROGRAM_PRELIMINARY_PN_SERIES_CANDIDATE",
        )
        self.assertIn(
            "not a verified pressure-temperature rating",
            fields["pressure_class"]["claim_boundary"],
        )
        self.assertEqual(
            fields["piping_class_candidate_code"]["provenance"],
            "SELECTOR_RULE/PROGRAM_ASSEMBLED_PRELIMINARY_LINE_CLASS",
        )
        self.assertEqual(
            fields["piping_class"]["value"],
            "OPEN_PROJECT_AUTHORITY_GATE",
        )
        self.assertEqual(
            fields["piping_class"]["promotion_cap"],
            "NOT_PROMOTABLE",
        )
        self.assertIn(
            "project_authority_piping_class",
            specification["formal_readiness"]["open_gates"],
        )
        for open_field_id in (
            "stress_analysis_ref",
            "support_design_ref",
        ):
            open_field = fields[open_field_id]
            self.assertIsNone(open_field["value"])
            self.assertEqual(
                open_field["state"],
                "OPEN_FORMAL_EVIDENCE_GATE",
            )
            self.assertEqual(open_field["evidence_class"], "U")
            self.assertEqual(
                open_field["promotion_cap"],
                "NOT_PROMOTABLE",
            )
            self.assertTrue(open_field["display_value"])
            self.assertTrue(open_field["reason"])
            self.assertTrue(open_field["required_action"])
        self.assertIn("程序初选候选", specification["designation"])
        self.assertIn(
            "正式管道等级=OPEN_PROJECT_AUTHORITY_GATE",
            specification["designation"],
        )

        selector_lineage = {
            item["target_field"]: item
            for item in result["parameter_lineage"]
            if item.get("source_object_type") == "programmatic_pipe_selector"
        }
        self.assertIn(
            "GB/T_1048_verified_PN_series_mapping_only",
            selector_lineage["pressure_class"]["equation_chain"],
        )
        self.assertNotIn(
            str(derivation.PIPE_STANDARD_DB_PATH),
            selector_lineage["piping_class"]["source_path"],
        )
        self.assertEqual(
            selector_lineage["piping_class"]["result_status"],
            "OPEN_PROJECT_AUTHORITY_GATE",
        )
        self.assertIn(
            "PROGRAM_ASSEMBLED_PRELIMINARY_LINE_CLASS",
            selector_lineage[
                "piping_class_candidate_code"
            ]["equation_chain"],
        )

    def test_pipe_pressure_gradient_feedback_increases_dn_and_rechecks_wall(
        self,
    ) -> None:
        result = self._derive_test_pipe_stream(
            stream_id="BFW-HIGH-GRADIENT",
            phase="liquid",
            pressure_mpa=0.3,
            flow_m3_h=1.35,
            density_kg_m3=1000.0,
            viscosity_mpa_s=1.0,
        )
        preselection = result["canonical_match_input"][
            "pipe_hydraulic_preselection"
        ]
        specification = result["programmatic_pipe_specification"]
        self.assertEqual(
            preselection["controlling_constraint"],
            "PRESSURE_GRADIENT_SCREEN",
        )
        self.assertEqual(preselection["selected_dn_candidate"], 25)
        self.assertEqual(
            specification["fields"]["selected_dn"]["value"],
            25,
        )
        self.assertLessEqual(
            specification["hydraulic_calculation"][
                "pressure_gradient_kpa_per_100m"
            ],
            50.0,
        )
        self.assertEqual(
            specification["hydraulic_calculation"][
                "hydraulic_acceptance_status"
            ],
            "PRELIMINARY_SINGLE_PHASE_PROGRAM_SCREEN_ONLY",
        )
        target_lineage = next(
            item
            for item in result["parameter_lineage"]
            if item.get("target_field") == "target_velocity_m_s"
        )
        self.assertEqual(target_lineage["evidence_class"], "J")
        self.assertEqual(
            target_lineage["promotion_cap"],
            "TYPE_SCREENING",
        )

    def test_pipe_pressure_regime_ignores_numeric_noise_but_gates_vacuum(
        self,
    ) -> None:
        near = self._derive_test_pipe_stream(
            stream_id="NEAR-ATM",
            phase="liquid",
            pressure_mpa=0.101300,
            flow_m3_h=10.0,
            density_kg_m3=900.0,
            viscosity_mpa_s=0.8,
        )
        near_spec = near["programmatic_pipe_specification"]
        near_regime = near["canonical_match_input"][
            "pipe_pressure_regime_screening"
        ]
        self.assertFalse(near_regime["external_pressure_branch"])
        self.assertTrue(near_regime["near_atmospheric_screening"])
        self.assertAlmostEqual(near_regime["vacuum_margin_kpa"], 0.025)
        self.assertEqual(
            near_spec["fields"]["external_pressure_design_status"]["value"],
            "稳态Aspen未触发显著真空；事故真空仍待项目定义",
        )
        self.assertFalse(
            any(
                item.get("status")
                == "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED"
                for item in near["match_result"].get(
                    "calculation_pending",
                    [],
                )
            )
        )

        vacuum = self._derive_test_pipe_stream(
            stream_id="TRUE-VACUUM",
            phase="liquid",
            pressure_mpa=0.040,
            flow_m3_h=10.0,
            density_kg_m3=900.0,
            viscosity_mpa_s=0.8,
        )
        vacuum_spec = vacuum["programmatic_pipe_specification"]
        vacuum_regime = vacuum["canonical_match_input"][
            "pipe_pressure_regime_screening"
        ]
        self.assertTrue(vacuum_regime["external_pressure_branch"])
        self.assertGreater(vacuum_regime["vacuum_margin_kpa"], 60.0)
        self.assertEqual(
            vacuum_spec["fields"]["external_pressure_design_status"][
                "state"
            ],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )

    def test_dn600_uses_lsa_welded_route_and_open_product_standard(
        self,
    ) -> None:
        result = self._derive_test_pipe_stream(
            stream_id="LARGE-BORE",
            phase="liquid",
            pressure_mpa=0.3,
            flow_m3_h=1400.0,
            density_kg_m3=1000.0,
            viscosity_mpa_s=1.0,
        )
        specification = result["programmatic_pipe_specification"]
        fields = specification["fields"]
        self.assertGreaterEqual(fields["selected_dn"]["value"], 600)
        self.assertEqual(
            fields["equipment_type"]["value"],
            "直缝埋弧焊钢制工艺管道",
        )
        self.assertEqual(
            fields["manufacturing_method"]["value"],
            "钢板卷制 + 纵向对接焊缝 + 双面埋弧焊候选",
        )
        self.assertEqual(
            fields["product_standard"]["value"],
            "OPEN_PROJECT_WELDED_PIPE_PRODUCT_SPECIFICATION_GATE",
        )
        self.assertIn(
            "LSAW",
            fields["piping_class_candidate_code"]["value"],
        )
        self.assertNotIn(
            "CS20",
            fields["piping_class_candidate_code"]["value"],
        )
        self.assertFalse(
            specification["manufacturing_route"][
                "product_standard_scope_established"
            ]
        )
        self.assertEqual(
            specification["standard_selections"]["wall"]["usage_role"],
            "GEOMETRY_REFERENCE_ONLY",
        )
        self.assertFalse(
            specification["standard_selections"]["wall"][
                "product_scope_applicable"
            ]
        )
        recommendation = result["match_result"]["model_recommendation"]
        self.assertEqual(
            recommendation["recommended_type"],
            "直缝埋弧焊钢制工艺管道",
        )
        leading = recommendation["leading_candidate"]
        self.assertEqual(
            leading["specification"]["selected_wall_thickness_mm"][
                "value"
            ],
            fields["selected_wall_thickness_mm"]["value"],
        )
        self.assertNotIn("GB/T 8163", fields["product_standard"]["value"])
        self.assertNotIn("无缝", leading["designation"])

    def test_open_seamless_product_standard_is_not_marked_established(
        self,
    ) -> None:
        result = self._derive_test_pipe_stream(
            stream_id="LOW-TEMPERATURE",
            phase="liquid",
            pressure_mpa=0.3,
            flow_m3_h=10.0,
            density_kg_m3=900.0,
            viscosity_mpa_s=0.8,
            temperature_c=-30.0,
        )
        specification = result["programmatic_pipe_specification"]
        manufacturing = specification["manufacturing_route"]
        self.assertEqual(manufacturing["route_code"], "SEAMLESS")
        self.assertFalse(
            manufacturing["product_standard_scope_established"]
        )
        self.assertIn(
            "pipe_product_standard_and_dimensional_tolerances",
            manufacturing["manufacturing_open_gates"],
        )
        self.assertEqual(
            specification["fields"]["product_standard"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )

    def test_carbon_steel_product_standard_is_catalog_bound_but_open(
        self,
    ) -> None:
        result = self._derive_test_pipe_stream(
            stream_id="CS-PRODUCT-STANDARD",
            phase="liquid",
            pressure_mpa=0.3,
            flow_m3_h=10.0,
            density_kg_m3=900.0,
            viscosity_mpa_s=0.8,
            temperature_c=30.0,
        )
        specification = result["programmatic_pipe_specification"]
        manufacturing = specification["manufacturing_route"]
        evidence = specification["product_standard_evidence"]
        field = specification["fields"]["product_standard"]

        self.assertEqual(field["value"], "GB/T 8163-2018")
        self.assertEqual(
            field["state"],
            "PROGRAM_PRELIMINARY_STANDARD_IDENTITY_CANDIDATE",
        )
        self.assertFalse(manufacturing["product_standard_scope_established"])
        self.assertIn(
            "pipe_product_standard_scope_verification",
            manufacturing["open_gates"],
        )
        self.assertEqual(
            evidence["source_status"],
            "CATALOG_ENTRY_ONLY_NOT_SCOPE_VERIFIED",
        )
        self.assertFalse(evidence["product_scope_verified"])
        self.assertRegex(evidence["inventory_sha256"], r"^[A-F0-9]{64}$")
        self.assertRegex(evidence["entry_sha256"], r"^[A-F0-9]{64}$")
        self.assertRegex(evidence["evidence_sha256"], r"^[A-F0-9]{64}$")
        self.assertNotIn("C:\\Users\\", evidence["inventory_path"])

    def test_aspen_pipe_block_routes_to_concrete_process_piping_type(self) -> None:
        inlet, inlet_errors = derivation.normalize_stream(
            {
                "stream_id": "IN",
                "stream_record_type": "MATERIAL",
                "phase": "liquid",
                "pressure_mpa": 0.8,
                "temperature_c": 20.0,
                "volumetric_flow_m3_h": 25.0,
                "mass_flow_kg_h": 25_000.0,
                "density_kg_m3": 1_000.0,
                "MUMX": 0.8,
                "aspen_raw_paths": {
                    "MUMX": (
                        r"\Data\Streams\IN\Output\STRM_UPP"
                        r"\MUMX\MIXED\LIQUID"
                    ),
                },
                "component_mole_fractions": {
                    "WATER": 0.9,
                    "METHANOL": 0.1,
                },
            },
            {"stream.IN.MUMX": "cP"},
        )
        outlet, outlet_errors = derivation.normalize_stream(
            {
                "stream_id": "OUT",
                "stream_record_type": "MATERIAL",
                "phase": "liquid",
                "pressure_mpa": 0.4,
                "temperature_c": 20.0,
                "volumetric_flow_m3_h": 25.0,
                "mass_flow_kg_h": 25_000.0,
                "density_kg_m3": 1_000.0,
                "MUMX": 0.6,
                "aspen_raw_paths": {
                    "MUMX": (
                        r"\Data\Streams\OUT\Output\STRM_UPP"
                        r"\MUMX\MIXED\LIQUID"
                    ),
                },
                "component_mole_fractions": {
                    "WATER": 0.85,
                    "METHANOL": 0.15,
                },
            },
            {"stream.OUT.MUMX": "cP"},
        )
        block, block_errors = derivation.normalize_block(
            {
                "block_id": "PIPE-1",
                "block_type": "PIPE",
                "inlet_streams": ["IN"],
                "outlet_streams": ["OUT"],
            },
            {},
        )
        self.assertEqual(inlet_errors + outlet_errors + block_errors, [])

        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {},
            {"IN": inlet, "OUT": outlet},
            {"pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
            {"IN": {"from_block_ids": [], "to_block_ids": ["PIPE-1"]},
             "OUT": {"from_block_ids": ["PIPE-1"], "to_block_ids": []}},
        )

        match = result["match_result"]
        recommendation = match["model_recommendation"]
        candidate = recommendation["candidates"][0]
        self.assertEqual(match["status"], "MATCHED")
        self.assertEqual(match["match"]["family_id"], "family_process_piping")
        self.assertEqual(recommendation["recommended_type"], "无缝钢制工艺管道")
        self.assertEqual(candidate["candidate_kind"], "engineered_designation")
        self.assertNotIn("非标准", candidate["designation"])
        self.assertEqual(result["adapter_blockers"], [])
        self.assertAlmostEqual(
            result["canonical_match_input"]["dynamic_viscosity_mpa_s"],
            0.8,
        )
        observations = result["connected_stream_observations"]
        self.assertEqual(
            [(item["port_role"], item["stream_id"]) for item in observations],
            [("inlet", "IN"), ("outlet", "OUT")],
        )
        for observation in observations:
            self.assertTrue(observation["read_only_observation"])
            self.assertFalse(
                observation["adopted_as_equipment_main_input"]
            )
            self.assertEqual(observation["missing_required_groups"], [])
            self.assertTrue({
                "phase",
                "temperature_c",
                "pressure_mpa",
                "volumetric_flow_m3_h",
                "composition",
                "dynamic_viscosity_mpa_s",
            }.issubset(observation["fields"]))
        viscosity_paths = {
            item["port_role"]: item["source_path"]
            for item in result["connected_stream_observation_lineage"]
            if item["target_field"].endswith(".dynamic_viscosity_mpa_s")
        }
        self.assertEqual(
            viscosity_paths,
            {
                "inlet": (
                    r"\Data\Streams\IN\Output\STRM_UPP"
                    r"\MUMX\MIXED\LIQUID"
                ),
                "outlet": (
                    r"\Data\Streams\OUT\Output\STRM_UPP"
                    r"\MUMX\MIXED\LIQUID"
                ),
            },
        )
        self.assertTrue(all(
            item["result_status"]
            == "OBSERVED_NOT_ADOPTED_AS_EQUIPMENT_MAIN_INPUT"
            and item["evidence_scope"]
            == "CONNECTED_STREAM_OBSERVATION_ONLY"
            and not item["adopted_as_equipment_main_input"]
            for item in result["connected_stream_observation_lineage"]
        ))
        parameter_observation_viscosity = {
            item["port_role"]
            for item in result["parameter_lineage"]
            if item.get("source_object_type")
            == "connected_stream_observation"
            and item["target_field"].endswith(
                ".dynamic_viscosity_mpa_s"
            )
        }
        self.assertEqual(
            parameter_observation_viscosity,
            {"inlet", "outlet"},
        )
        self.assertTrue(any(
            item.get("target_field") == "equipment_family"
            and item.get("evidence_scope") == "EQUIPMENT_FAMILY_ROUTING_ONLY"
            for item in result["parameter_lineage"]
        ))
        self.assertEqual(
            result["pipe_entity_scope"],
            "ASPEN_PHYSICAL_PIPE_BLOCK",
        )
        self.assertEqual(
            result["pipe_entity_id"],
            "ASPEN_PIPE_BLOCK:PIPE-1",
        )
        self.assertTrue(result["counted_as_physical_pipe"])
        self.assertFalse(result["alias_only"])
        audit = result["endpoint_pressure_drop_audit"]
        self.assertEqual(
            audit["status"],
            "ASPEN_ENDPOINT_PRESSURE_DIFFERENCE_CALCULATED",
        )
        self.assertTrue(audit["endpoint_complete"])
        self.assertFalse(audit["formal_acceptance"])
        self.assertFalse(
            audit[
                "independent_friction_loss_reconciliation_complete"
            ]
        )
        self.assertEqual(audit["pressure_basis"], "absolute")
        self.assertAlmostEqual(
            audit["endpoint_pressure_drop_kpa"],
            400.0,
        )
        audit_payload = dict(audit)
        audit_sha256 = audit_payload.pop("audit_sha256")
        self.assertEqual(
            audit_sha256,
            derivation._canonical_sha256(audit_payload),
        )
        self.assertAlmostEqual(
            result["canonical_match_input"][
                "aspen_endpoint_pressure_drop_kpa"
            ],
            400.0,
        )

    def test_real_ex2_4_pipe_blocks_own_endpoint_states_without_double_count(
        self,
    ) -> None:
        source = (
            PACKAGE_ROOT
            / "outputs"
            / "real_bkp_stage1_20260723"
            / "exercise2_4_augmented_run"
            / "aspen_equipment_export.json"
        )
        self.assertTrue(source.is_file())
        bundle = json.loads(source.read_text(encoding="utf-8"))

        result = derivation.derive_bundle(bundle, source)

        self.assertEqual(result["status"], "DERIVED")
        reconciliation = result["pipe_entity_reconciliation"]
        self.assertEqual(
            reconciliation["status"],
            "PASS_NO_ENDPOINT_STATE_DOUBLE_COUNT",
        )
        self.assertEqual(
            reconciliation["aspen_physical_pipe_block_count"],
            2,
        )
        self.assertEqual(
            reconciliation["independent_pfd_pipe_segment_count"],
            0,
        )
        self.assertEqual(
            reconciliation["pfd_endpoint_state_alias_count"],
            4,
        )
        self.assertEqual(result["physical_pipe_entity_count"], 2)
        self.assertEqual(result["piping_count"], 0)
        self.assertEqual(result["piping_state_alias_count"], 4)
        row_binding_summary = result[
            "program_generated_record_binding_summary"
        ]
        self.assertEqual(row_binding_summary["status"], "PASS")
        self.assertEqual(row_binding_summary["row_count"], 7)
        self.assertEqual(row_binding_summary["unique_binding_count"], 7)
        lineage_summary = result["final_parameter_lineage_summary"]
        self.assertEqual(lineage_summary["status"], "PASS")
        self.assertEqual(lineage_summary["row_count"], 7)
        self.assertEqual(
            {
                (row["record_kind"], row["identity"])
                for row in lineage_summary["rows"]
            },
            {
                ("equipment", "PUMP"),
                ("physical_pipe_block", "P1"),
                ("physical_pipe_block", "P2"),
                ("pfd_endpoint_state_alias", "IN"),
                ("pfd_endpoint_state_alias", "OUT"),
                ("pfd_endpoint_state_alias", "SHU1"),
                ("pfd_endpoint_state_alias", "SHU2"),
            },
        )
        self.assertEqual(
            {
                item["stream_id"]: tuple(
                    item["canonical_pipe_entity_ids"]
                )
                for item in result["piping_state_aliases"]
            },
            {
                "IN": ("ASPEN_PIPE_BLOCK:P2",),
                "OUT": ("ASPEN_PIPE_BLOCK:P1",),
                "SHU1": ("ASPEN_PIPE_BLOCK:P2",),
                "SHU2": ("ASPEN_PIPE_BLOCK:P1",),
            },
        )
        equipment_by_id = {
            item["aspen_block_id"]: item
            for item in result["equipment"]
        }
        self.assertAlmostEqual(
            equipment_by_id["P1"][
                "endpoint_pressure_drop_audit"
            ]["endpoint_pressure_drop_kpa"],
            407.639946,
            places=6,
        )
        self.assertAlmostEqual(
            equipment_by_id["P2"][
                "endpoint_pressure_drop_audit"
            ]["endpoint_pressure_drop_kpa"],
            1.5469426,
            places=6,
        )
        for item in [
            *result["equipment"],
            *result["piping"],
            *result["piping_state_aliases"],
        ]:
            binding = dict(item["program_generated_record_binding"])
            binding_sha256 = binding.pop("binding_sha256")
            self.assertEqual(
                binding_sha256,
                derivation._canonical_sha256(binding),
            )
            self.assertEqual(
                item["program_generated_record_sha256"],
                binding_sha256,
            )
            provenance = dict(item["input_provenance"])
            provenance_sha256 = provenance.pop(
                "final_snapshot_sha256"
            )
            self.assertEqual(
                provenance_sha256,
                derivation._canonical_sha256(provenance),
            )
            self.assertEqual(
                item["program_generated_record_binding"][
                    "input_provenance_snapshot_sha256"
                ],
                provenance_sha256,
            )
            self.assertEqual(
                item["program_generated_record_binding"][
                    "derivation_chain_sha256"
                ],
                derivation._canonical_sha256(
                    item["derivation_chain"]
                ),
            )
        for pipe_id in ("P1", "P2"):
            pipe = equipment_by_id[pipe_id]
            self.assertEqual(
                pipe["equipment_program_specification_sha256"],
                pipe["program_generated_record_sha256"],
            )
            self.assertEqual(
                pipe["pipe_program_specification_sha256"],
                pipe["program_generated_record_sha256"],
            )
        reconciliation_payload = dict(reconciliation)
        reconciliation_sha256 = reconciliation_payload.pop(
            "reconciliation_sha256"
        )
        self.assertEqual(
            reconciliation_sha256,
            derivation._canonical_sha256(reconciliation_payload),
        )

        customer = customer_delivery.build_customer_delivery(result)
        overview = customer["equipment_overview_table"]
        self.assertEqual(overview["row_count"], 3)
        self.assertEqual(
            {
                (row["equipment_tag"], row["record_kind"])
                for row in overview["rows"]
            },
            {
                ("P1", "piping"),
                ("P2", "piping"),
                ("PUMP", "equipment"),
            },
        )
        p1_overview = next(
            row
            for row in overview["rows"]
            if row["equipment_tag"] == "P1"
        )
        p1_fields = {
            field["field_id"]: field
            for field in p1_overview["all_equipment_fields"]
        }
        self.assertAlmostEqual(
            p1_fields["aspen_endpoint_pressure_drop_kpa"][
                "value"
            ],
            407.639946,
            places=6,
        )
        self.assertEqual(
            p1_fields["aspen_endpoint_pressure_drop_kpa"]["state"],
            "DERIVED_FROM_ASPEN",
        )
        self.assertFalse(
            p1_fields[
                "endpoint_pressure_drop_formal_acceptance"
            ]["value"]
        )
        self.assertEqual(
            p1_fields["endpoint_pressure_drop_status"]["source"][
                "kind"
            ],
            "aspen_parameter_lineage_projection",
        )

    def test_aspen_eng_stream_units_are_normalized_without_data_loss(self) -> None:
        row = {
            "TEMP_OUT": 220.0,
            "PRES_OUT": 20.0,
            "MASSFLMX": 38065.736,
            "VOLFLMX": 827.177279,
            "VOLFLMX_LIQ": 827.177279,
            "density_kg_m3": 46.0188365,
            "MUMX": 0.2730,
        }
        units = {
            "stream.S1.TEMP_OUT": "F",
            "stream.S1.PRES_OUT": "psia",
            "stream.S1.MASSFLMX": "lb/hr",
            "stream.S1.VOLFLMX": "cuft/hr",
            "stream.S1.VOLFLMX_LIQ": "cuft/hr",
            "stream.S1.density_kg_m3": "lb/cuft",
            "stream.S1.MUMX": "cP",
        }
        values, sources, errors = derivation.extract_numeric_fields(
            row,
            derivation.STREAM_ALIASES,
            units,
            "stream",
            "S1",
        )

        self.assertEqual(errors, [])
        self.assertAlmostEqual(values["temperature_c"], 104.4444444444, places=8)
        self.assertAlmostEqual(values["pressure_mpa"], 0.13789514586336, places=10)
        self.assertAlmostEqual(values["mass_flow_kg_h"], 17266.3274080343, places=5)
        self.assertAlmostEqual(values["volumetric_flow_m3_h"], 23.423052113831, places=7)
        self.assertAlmostEqual(values["liquid_volumetric_flow_m3_h"], 23.423052113831, places=7)
        self.assertAlmostEqual(values["density_kg_m3"], 737.151046987504, places=5)
        self.assertAlmostEqual(values["dynamic_viscosity_mpa_s"], 0.2730, places=8)
        self.assertEqual(sources["pressure_mpa"]["source_unit"], "psia")
        self.assertEqual(sources["dynamic_viscosity_mpa_s"]["source_field"], "MUMX")
        self.assertIn("0.006894757293168", sources["pressure_mpa"]["transform"])

    def test_aspen_si_viscosity_converts_to_millipascal_seconds(self) -> None:
        values, sources, errors = derivation.extract_numeric_fields(
            {"stream_id": "S-MU", "MUMX": 0.0008437},
            derivation.STREAM_ALIASES,
            {"stream.S-MU.MUMX": "N-sec/sqm"},
            "stream",
            "S-MU",
        )
        self.assertFalse(errors)
        self.assertAlmostEqual(values["dynamic_viscosity_mpa_s"], 0.8437, places=8)
        self.assertEqual(
            sources["dynamic_viscosity_mpa_s"]["transform"],
            "mu_mPa_s=mu_Pa_s×1000",
        )

    def test_aspen_phase_viscosities_remain_distinct_for_two_phase_service(self) -> None:
        values, sources, errors = derivation.extract_numeric_fields(
            {
                "stream_id": "S-2P",
                "MUMX_LIQUID": 0.45,
                "MUMX_VAPOR": 0.012,
            },
            derivation.STREAM_ALIASES,
            {
                "stream.S-2P.MUMX_LIQUID": "cP",
                "stream.S-2P.MUMX_VAPOR": "cP",
            },
            "stream",
            "S-2P",
        )
        self.assertFalse(errors)
        self.assertNotIn("dynamic_viscosity_mpa_s", values)
        self.assertAlmostEqual(values["liquid_dynamic_viscosity_mpa_s"], 0.45)
        self.assertAlmostEqual(values["vapor_dynamic_viscosity_mpa_s"], 0.012)
        self.assertEqual(
            sources["liquid_dynamic_viscosity_mpa_s"]["source_field"],
            "MUMX_LIQUID",
        )

    @staticmethod
    def _internal_liquid_viscosity_records(
        a_value: float = 1.0e-5,
    ) -> dict[str, dict[str, object]]:
        return {
            "WATER": {
                "molecular_weight_kg_kmol": 18.01528,
                "source": {
                    "source_id": "REGRESSION_RECORD",
                    "citation": "Synthetic source-bound regression record",
                    "sha256": "A" * 64,
                },
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": a_value,
                    "B_K": 1000.0,
                    "temperature_min_k": 250.0,
                    "temperature_max_k": 450.0,
                },
            },
        }

    def test_internal_viscosity_fallback_reaches_pipe_with_j_warning_lineage(
        self,
    ) -> None:
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": "S-INTERNAL-MU",
                "stream_record_type": "MATERIAL",
                "phase": "liquid",
                "temperature_c": 30.0,
                "pressure_mpa": 0.3,
                "volumetric_flow_m3_h": 12.0,
                "mass_flow_kg_h": 12_000.0,
                "density_kg_m3": 1_000.0,
                "component_mole_fractions": {"WATER": 1.0},
            },
            {},
        )
        self.assertEqual(errors, [])
        diagnostic = derivation.enrich_stream_viscosity(
            stream,
            correlation_records=self._internal_liquid_viscosity_records(),
            correlation_registry={"registry_id": "TEST"},
            source_export_sha256="B" * 64,
        )
        self.assertEqual(diagnostic["status"], "PASS_WITH_WARNING")
        self.assertTrue(diagnostic["internal_correlation_used"])
        source = stream["_sources"]["dynamic_viscosity_mpa_s"]
        self.assertEqual(source["origin"], "INTERNAL_CORRELATION_ESTIMATE")
        self.assertEqual(source["evidence_class"], "J")
        self.assertIn("强警告", source["warning"])

        source_path = Path(__file__).resolve()
        result = derivation.derive_piping(
            stream,
            {"from_block_ids": ["B-1"], "to_block_ids": ["B-2"]},
            {"case_id": "CASE-INTERNAL-MU", "pressure_basis": "absolute"},
            source_path,
            derivation.sha256_file(source_path),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )
        lineage = next(
            item
            for item in result["parameter_lineage"]
            if item.get("target_field") == "dynamic_viscosity_mpa_s"
        )
        self.assertEqual(lineage["origin"], "INTERNAL_CORRELATION_ESTIMATE")
        self.assertEqual(lineage["evidence_class"], "J")
        self.assertNotIn("Aspen[", lineage["equation_chain"])
        specification = result["programmatic_pipe_specification"]
        self.assertEqual(
            specification["hydraulic_calculation"]["viscosity_origin"],
            "INTERNAL_CORRELATION_ESTIMATE",
        )
        self.assertEqual(
            specification["hydraulic_calculation"]["status"],
            "CALCULATED_PER_100M_WITH_INTERNAL_VISCOSITY_CORRELATION_WARNING",
        )
        self.assertIn(
            "aspen_or_lab_viscosity_confirmation",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertIn("强警告", specification["designation"])

    def test_aspen_mixture_and_phase_specific_viscosity_precede_internal_formula(
        self,
    ) -> None:
        mixed, mixed_errors = derivation.normalize_stream(
            {
                "stream_id": "S-MIXED-MU",
                "phase": "liquid",
                "temperature_c": 30.0,
                "MUMX": 0.8,
                "component_mole_fractions": {"WATER": 1.0},
            },
            {"stream.S-MIXED-MU.MUMX": "cP"},
        )
        self.assertEqual(mixed_errors, [])
        mixed_diagnostic = derivation.enrich_stream_viscosity(
            mixed,
            correlation_records=self._internal_liquid_viscosity_records(9.0e-5),
            correlation_registry={},
            source_export_sha256="C" * 64,
        )
        self.assertEqual(
            mixed_diagnostic["status"],
            "NOT_NEEDED_EXPORTED_MIXTURE_VISCOSITY_PRESENT",
        )
        self.assertAlmostEqual(mixed["dynamic_viscosity_mpa_s"], 0.8)

        phase_specific, phase_errors = derivation.normalize_stream(
            {
                "stream_id": "S-PHASE-MU",
                "phase": "liquid",
                "temperature_c": 30.0,
                "MUMX_LIQUID": 0.65,
                "component_mole_fractions": {"WATER": 1.0},
            },
            {"stream.S-PHASE-MU.MUMX_LIQUID": "cP"},
        )
        self.assertEqual(phase_errors, [])
        phase_diagnostic = derivation.enrich_stream_viscosity(
            phase_specific,
            correlation_records=self._internal_liquid_viscosity_records(9.0e-5),
            correlation_registry={},
            source_export_sha256="D" * 64,
        )
        self.assertEqual(
            phase_diagnostic["status"],
            "ASPEN_PHASE_SPECIFIC_MUMX_PROMOTED",
        )
        self.assertAlmostEqual(
            phase_specific["dynamic_viscosity_mpa_s"],
            0.65,
        )
        self.assertEqual(
            phase_specific["_sources"]["dynamic_viscosity_mpa_s"]["origin"],
            "ASPEN_EXTRACTED_PHASE_SPECIFIC_PROMOTION",
        )

    def test_two_phase_never_uses_internal_viscosity_correlation(self) -> None:
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": "S-TWO-PHASE-INTERNAL",
                "phase": "two_phase",
                "temperature_c": 30.0,
                "MUMX_LIQUID": 0.65,
                "MUMX_VAPOR": 0.012,
                "component_mole_fractions": {"WATER": 1.0},
            },
            {
                "stream.S-TWO-PHASE-INTERNAL.MUMX_LIQUID": "cP",
                "stream.S-TWO-PHASE-INTERNAL.MUMX_VAPOR": "cP",
            },
        )
        self.assertEqual(errors, [])
        diagnostic = derivation.enrich_stream_viscosity(
            stream,
            correlation_records=self._internal_liquid_viscosity_records(),
            correlation_registry={},
            source_export_sha256="E" * 64,
        )
        self.assertEqual(diagnostic["status"], "BLOCKED")
        self.assertEqual(
            diagnostic["code"],
            "BLOCKED_VISCOSITY_CORRELATION_PHASE",
        )
        self.assertFalse(diagnostic["internal_correlation_used"])
        self.assertNotIn("dynamic_viscosity_mpa_s", stream)

    def test_viscosity_diagnostic_hash_changes_with_bound_coefficient_record(
        self,
    ) -> None:
        diagnostics: list[dict[str, object]] = []
        values: list[float] = []
        for coefficient in (1.0e-5, 2.0e-5):
            stream, errors = derivation.normalize_stream(
                {
                    "stream_id": "S-HASH-MU",
                    "phase": "liquid",
                    "temperature_c": 30.0,
                    "component_mole_fractions": {"WATER": 1.0},
                },
                {},
            )
            self.assertEqual(errors, [])
            diagnostics.append(
                derivation.enrich_stream_viscosity(
                    stream,
                    correlation_records=(
                        self._internal_liquid_viscosity_records(coefficient)
                    ),
                    correlation_registry={},
                    source_export_sha256="F" * 64,
                )
            )
            values.append(float(stream["dynamic_viscosity_mpa_s"]))
        self.assertNotEqual(values[0], values[1])
        self.assertNotEqual(
            diagnostics[0]["diagnostic_sha256"],
            diagnostics[1]["diagnostic_sha256"],
        )
        self.assertNotEqual(
            diagnostics[0]["embedded_correlation_record_set_sha256"],
            diagnostics[1]["embedded_correlation_record_set_sha256"],
        )

    def test_two_phase_pipe_uses_explicit_screening_proxy_and_keeps_phase_lineage(
        self,
    ) -> None:
        liquid_path = (
            r"\Data\Streams\S-2P\Output\STRM_UPP\MUMX\MIXED\LIQUID"
        )
        vapor_path = (
            r"\Data\Streams\S-2P\Output\STRM_UPP\MUMX\MIXED\VAPOR"
        )
        stream, errors = derivation.normalize_stream(
            {
                "stream_id": "S-2P",
                "stream_record_type": "MATERIAL",
                "phase": "two_phase",
                "pressure_mpa": 0.35,
                "temperature_c": 90.0,
                "volumetric_flow_m3_h": 80.0,
                "mass_flow_kg_h": 45_000.0,
                "density_kg_m3": 550.0,
                "MUMX_LIQUID": 0.45,
                "MUMX_VAPOR": 0.012,
                "aspen_raw_paths": {
                    "MUMX_LIQUID": liquid_path,
                    "MUMX_VAPOR": vapor_path,
                },
                "component_mole_fractions": {
                    "WATER": 0.6,
                    "BENZENE": 0.4,
                },
            },
            {
                "stream.S-2P.MUMX_LIQUID": "cP",
                "stream.S-2P.MUMX_VAPOR": "cP",
            },
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_piping(
            stream,
            {"from_block_ids": ["B-1"], "to_block_ids": ["B-2"]},
            {"case_id": "CASE-2P", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        canonical = result["canonical_match_input"]
        self.assertAlmostEqual(
            canonical["liquid_dynamic_viscosity_mpa_s"],
            0.45,
        )
        self.assertAlmostEqual(
            canonical["vapor_dynamic_viscosity_mpa_s"],
            0.012,
        )
        self.assertAlmostEqual(canonical["dynamic_viscosity_mpa_s"], 0.45)
        basis = canonical["two_phase_viscosity_screening_basis"]
        self.assertTrue(basis["not_an_aspen_mixture_property"])
        screening_lineage = next(
            item
            for item in result["parameter_lineage"]
            if item.get("target_field") == "dynamic_viscosity_mpa_s"
        )
        self.assertEqual(
            screening_lineage["result_status"],
            "DERIVED_TWO_PHASE_SCREENING_PROXY",
        )
        screening_paths = json.loads(screening_lineage["source_path"])
        self.assertEqual(
            screening_paths["liquid_dynamic_viscosity_mpa_s"],
            liquid_path,
        )
        self.assertEqual(
            screening_paths["vapor_dynamic_viscosity_mpa_s"],
            vapor_path,
        )
        phase_lineages = {
            item["target_field"]: item
            for item in result["parameter_lineage"]
            if item.get("target_field")
            in {
                "liquid_dynamic_viscosity_mpa_s",
                "vapor_dynamic_viscosity_mpa_s",
            }
        }
        self.assertEqual(
            phase_lineages["liquid_dynamic_viscosity_mpa_s"]["source_path"],
            liquid_path,
        )
        self.assertEqual(
            phase_lineages["vapor_dynamic_viscosity_mpa_s"]["source_path"],
            vapor_path,
        )
        specification = result["programmatic_pipe_specification"]
        self.assertEqual(
            specification["status"],
            "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
        )
        self.assertIn("两相管", specification["designation"])
        self.assertIn(
            "two_phase_flow_regime_holdup_slip_and_pressure_drop",
            specification["formal_readiness"]["open_gates"],
        )
        self.assertEqual(
            specification["hydraulic_calculation"]["status"],
            "ADVISORY_HOMOGENEOUS_TWO_PHASE_PROXY_FORMAL_GATE_OPEN",
        )
        self.assertEqual(
            specification["hydraulic_calculation"][
                "hydraulic_acceptance_status"
            ],
            "NOT_EVALUATED_TWO_PHASE_FORMAL_GATE_OPEN",
        )
        self.assertFalse(
            specification["hydraulic_calculation"][
                "formal_hydraulic_acceptance"
            ]
        )
        self.assertNotIn(
            "PASS",
            specification["hydraulic_calculation"]["status"],
        )
        self.assertNotIn(
            "PASS",
            specification["pressure_wall_screening"]["status"],
        )
        self.assertEqual(
            specification["fields"]["viscosity_basis_status"]["state"],
            "PROGRAM_PRELIMINARY_TWO_PHASE_VISCOSITY_PROXY",
        )
        self.assertEqual(
            specification["fields"]["viscosity_basis_status"][
                "provenance"
            ],
            "CALCULATED_TWO_PHASE_SCREENING_PROXY",
        )
        self.assertIn(
            "非Aspen两相混合黏度",
            specification["fields"]["viscosity_basis_status"]["value"],
        )
        self.assertNotIn(
            "liquid_dynamic_viscosity_mpa_s",
            specification["fields"],
        )
        self.assertNotIn(
            "vapor_dynamic_viscosity_mpa_s",
            specification["fields"],
        )

    def test_common_aspen_eng_block_units_cover_sizing_fields(self) -> None:
        row = {
            "QCALC": 1_000_000.0,
            "AREA": 100.0,
            "BRAKE_POWER": 10.0,
            "HEAD_CAL": 100.0,
            "DELP_CAL": 10.0,
            "VOLUME": 100.0,
            "DIAMETER": 24.0,
            "HEIGHT": 10.0,
        }
        units = {
            "block.B1.QCALC": "Btu/hr",
            "block.B1.AREA": "sqft",
            "block.B1.BRAKE_POWER": "hp",
            "block.B1.HEAD_CAL": "ft",
            "block.B1.DELP_CAL": "psi",
            "block.B1.VOLUME": "cuft",
            "block.B1.DIAMETER": "in",
            "block.B1.HEIGHT": "ft",
        }
        values, _sources, errors = derivation.extract_numeric_fields(
            row,
            derivation.BLOCK_ALIASES,
            units,
            "block",
            "B1",
        )

        self.assertEqual(errors, [])
        self.assertAlmostEqual(values["heat_duty_kw"], 293.071070172, places=8)
        self.assertAlmostEqual(values["heat_transfer_area_m2"], 9.290304, places=8)
        self.assertAlmostEqual(values["shaft_power_kw"], 7.45699871582, places=8)
        self.assertAlmostEqual(values["head_m"], 30.48, places=8)
        self.assertAlmostEqual(values["pressure_drop_kpa"], 68.94757293168, places=8)
        self.assertAlmostEqual(values["volume_m3"], 2.8316846592, places=8)
        self.assertAlmostEqual(values["diameter_mm"], 609.6, places=8)
        self.assertAlmostEqual(values["height_mm"], 3048.0, places=8)

    def test_aspen_metric_technical_units_are_normalized(self) -> None:
        row = {
            "PRES_OUT": 25.0,
            "MASSFLMX": 56.4728022,
        }
        units = {
            "stream.S2.PRES_OUT": "kg/sqcm",
            "stream.S2.MASSFLMX": "tonne/hr",
        }
        values, _sources, errors = derivation.extract_numeric_fields(
            row,
            derivation.STREAM_ALIASES,
            units,
            "stream",
            "S2",
        )

        self.assertEqual(errors, [])
        self.assertAlmostEqual(values["pressure_mpa"], 2.4516625, places=8)
        self.assertAlmostEqual(values["mass_flow_kg_h"], 56472.8022, places=8)
        pressure_drop, _formula = derivation.convert(1.0, "kg/sqcm", "kPa")
        self.assertAlmostEqual(pressure_drop, 98.0665, places=8)

    def test_heatx_four_ports_are_mapped_and_prevent_60c_design_default(
        self,
    ) -> None:
        raw_streams = [
            {
                "stream_id": "HOT-IN",
                "phase": "vapor",
                "temperature_c": 355.39,
                "pressure_mpa": 2.0,
                "mass_flow_kg_h": 10_000.0,
                "volumetric_flow_m3_h": 1_000.0,
                "density_kg_m3": 10.0,
                "dynamic_viscosity_mpa_s": 0.02,
            },
            {
                "stream_id": "HOT-OUT",
                "phase": "liquid",
                "temperature_c": 200.0,
                "pressure_mpa": 1.9,
                "mass_flow_kg_h": 10_000.0,
                "volumetric_flow_m3_h": 12.0,
                "density_kg_m3": 830.0,
                "dynamic_viscosity_mpa_s": 0.3,
            },
            {
                "stream_id": "COLD-IN",
                "phase": "liquid",
                "temperature_c": 40.0,
                "pressure_mpa": 1.5,
                "mass_flow_kg_h": 8_000.0,
                "volumetric_flow_m3_h": 10.0,
                "density_kg_m3": 800.0,
                "dynamic_viscosity_mpa_s": 0.5,
            },
            {
                "stream_id": "COLD-OUT",
                "phase": "liquid",
                "temperature_c": 180.0,
                "pressure_mpa": 1.4,
                "mass_flow_kg_h": 8_000.0,
                "volumetric_flow_m3_h": 10.5,
                "density_kg_m3": 760.0,
                "dynamic_viscosity_mpa_s": 0.3,
            },
        ]
        streams: dict[str, dict[str, object]] = {}
        for raw in raw_streams:
            normalized, errors = derivation.normalize_stream(raw, {})
            self.assertEqual(errors, [])
            streams[normalized["stream_id"]] = normalized
        block, block_errors = derivation.normalize_block(
            {
                "block_id": "E-PORTS",
                "block_type": "HEATX",
                "inlet_streams": ["HOT-IN", "COLD-IN"],
                "outlet_streams": ["HOT-OUT", "COLD-OUT"],
                "port_detail": [
                    {"port": "H(IN)", "direction": "in", "streams": ["HOT-IN"]},
                    {"port": "C(IN)", "direction": "in", "streams": ["COLD-IN"]},
                    {"port": "H(OUT)", "direction": "out", "streams": ["HOT-OUT"]},
                    {"port": "C(OUT)", "direction": "out", "streams": ["COLD-OUT"]},
                ],
                "connections": [
                    {"name": "HOT-IN", "value": "H(IN)"},
                    {"name": "COLD-IN", "value": "C(IN)"},
                    {"name": "HOT-OUT", "value": "H(OUT)"},
                    {"name": "COLD-OUT", "value": "C(OUT)"},
                ],
                "heat_duty_kw": 1_000.0,
                "heat_transfer_area_m2": 50.0,
            },
            {},
        )
        self.assertEqual(block_errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {
                "block_id": "E-PORTS",
                "equipment_tag": "E-PORTS",
                "process_function": "two-stream heat exchange",
            },
            streams,
            {"case_id": "CASE-HEATX", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        mapping = result["heatx_side_mapping"]
        self.assertEqual(
            mapping["status"],
            "EXPLICIT_ASPEN_PORT_ROLE_MAPPING_COMPLETE",
        )
        self.assertEqual(
            mapping["mapped_roles"]["hot_side_inlet"]["stream_id"],
            "HOT-IN",
        )
        self.assertEqual(
            result["canonical_match_input"][
                "cold_side_outlet_temperature_c"
            ],
            180.0,
        )
        self.assertFalse(
            mapping["lmtd_candidates"]["canonical_lmtd_selected"]
        )
        envelope = result["connected_stream_temperature_envelope"]
        self.assertAlmostEqual(envelope["maximum_temperature_c"], 355.39)
        values = (
            result["match_result"]["design_parameter_package"]
            ["selection_context"]["values"]
        )
        self.assertAlmostEqual(values["design_temperature_c"], 375.39)
        self.assertNotEqual(values["design_temperature_c"], 60.0)
        classification = result["heat_transfer_service_classification"]
        self.assertEqual(
            classification["status"],
            "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED",
        )
        self.assertIn(
            "工艺冷凝器",
            classification["recommended_type"],
        )
        model = result["match_result"]["model_recommendation"]
        self.assertEqual(
            model["status"],
            "HEAT_TRANSFER_SERVICE_TYPE_SELECTED_"
            "THERMAL_MECHANICAL_DESIGN_BLOCKED",
        )
        self.assertEqual(
            model["terminal_selection"]["evidence_class"],
            "J",
        )
        self.assertTrue(model["terminal_selection"]["provisional"])
        self.assertFalse(
            model["selection_execution"]["formal_selection_executed"]
        )
    def test_heater_phase_change_selects_condenser_but_remains_screening(
        self,
    ) -> None:
        streams: dict[str, dict[str, object]] = {}
        for raw in (
            {
                "stream_id": "VAP-IN",
                "phase": "vapor",
                "temperature_c": 140.0,
                "pressure_mpa": 0.5,
                "mass_flow_kg_h": 1_000.0,
                "volumetric_flow_m3_h": 300.0,
                "density_kg_m3": 3.333333333,
                "dynamic_viscosity_mpa_s": 0.015,
            },
            {
                "stream_id": "LIQ-OUT",
                "phase": "liquid",
                "temperature_c": 90.0,
                "pressure_mpa": 0.48,
                "mass_flow_kg_h": 1_000.0,
                "volumetric_flow_m3_h": 1.25,
                "density_kg_m3": 800.0,
                "dynamic_viscosity_mpa_s": 0.3,
            },
        ):
            normalized, errors = derivation.normalize_stream(raw, {})
            self.assertEqual(errors, [])
            streams[normalized["stream_id"]] = normalized
        block, block_errors = derivation.normalize_block(
            {
                "block_id": "CND-1",
                "block_type": "HEATER",
                "inlet_streams": ["VAP-IN"],
                "outlet_streams": ["LIQ-OUT"],
                "heat_duty_kw": -250.0,
            },
            {},
        )
        self.assertEqual(block_errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {
                "block_id": "CND-1",
                "equipment_tag": "CND-1",
                "process_function": "process stream cooling",
            },
            streams,
            {"case_id": "CASE-CND", "pressure_basis": "absolute"},
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        classification = result["heat_transfer_service_classification"]
        self.assertEqual(
            classification["phase_transitions"]["process_side"][
                "transition_kind"
            ],
            "full_condensation",
        )
        self.assertIn("全冷凝器", classification["recommended_type"])
        terminal = (
            result["match_result"]["model_recommendation"][
                "terminal_selection"
            ]
        )
        self.assertEqual(
            terminal["status"],
            "PROGRAMMATIC_PHASE_SERVICE_TYPE_SELECTED",
        )
        self.assertEqual(terminal["evidence_class"], "J")
        self.assertTrue(terminal["provisional"])
        self.assertFalse(terminal["formal_model"])

    def test_heatx_nonpositive_terminal_difference_prohibits_arrangement(
        self,
    ) -> None:
        streams: dict[str, dict[str, object]] = {}
        for stream_id, phase, temperature in (
            ("H-I", "liquid", 120.0),
            ("H-O", "liquid", 80.0),
            ("C-I", "liquid", 70.0),
            ("C-O", "liquid", 110.0),
        ):
            normalized, errors = derivation.normalize_stream(
                {
                    "stream_id": stream_id,
                    "phase": phase,
                    "temperature_c": temperature,
                    "pressure_mpa": 0.5,
                    "mass_flow_kg_h": 1_000.0,
                    "volumetric_flow_m3_h": 1.2,
                    "density_kg_m3": 833.333333333,
                    "dynamic_viscosity_mpa_s": 0.4,
                },
                {},
            )
            self.assertEqual(errors, [])
            streams[stream_id] = normalized
        block, errors = derivation.normalize_block(
            {
                "block_id": "E-ARR",
                "block_type": "HEATX",
                "inlet_streams": ["H-I", "C-I"],
                "outlet_streams": ["H-O", "C-O"],
                "port_detail": [
                    {"port": "H(IN)", "streams": ["H-I"]},
                    {"port": "H(OUT)", "streams": ["H-O"]},
                    {"port": "C(IN)", "streams": ["C-I"]},
                    {"port": "C(OUT)", "streams": ["C-O"]},
                ],
            },
            {},
        )
        self.assertEqual(errors, [])
        record: dict[str, object] = {}
        chain: list[dict[str, object]] = []
        source = Path(__file__).resolve()
        mapping = derivation.build_heatx_side_mapping(
            block=block,
            streams=streams,
            record=record,
            chain=chain,
            source_file=source,
            source_sha256=derivation.sha256_file(source),
        )

        lmtd = mapping["lmtd_candidates"]
        self.assertEqual(
            lmtd["arrangement_restriction_status"],
            "OPEN_FLOW_ARRANGEMENT_RESTRICTION_GATE",
        )
        self.assertEqual(lmtd["invalid_arrangements"], ["cocurrent"])
        self.assertIsNone(
            lmtd["candidates"]["cocurrent"]["lmtd_k"]
        )

    def test_heater_large_relative_pressure_drop_triggers_function_gate(
        self,
    ) -> None:
        classification = derivation.classify_heat_transfer_service(
            block_type="HEATER",
            inlets=[{
                "phase": "liquid",
                "pressure_mpa": 1.210,
            }],
            outlets=[{
                "phase": "liquid",
                "pressure_mpa": 0.245166,
            }],
            heatx_side_mapping={},
            pressure_basis="absolute",
        )

        screening = classification["pressure_drop_screening"]
        self.assertAlmostEqual(
            screening["pressure_drop_kpa"],
            964.834,
        )
        self.assertGreater(
            screening["ratio_to_inlet_absolute"],
            0.79,
        )
        self.assertTrue(screening["function_conflict"])
        self.assertEqual(
            screening["status"],
            "BLOCKED_HEAT_TRANSFER_PRESSURE_DROP_FUNCTION_CONFLICT",
        )
        self.assertIn(
            "dedicated_pressure_reduction_device_or_process_data_correction",
            classification["formal_open_gates"],
        )

        match_result = derivation.matcher.match_one(
            {
                "aspen_block_type": "HEATER",
                "process_function": "process heating or cooling",
                "flow_m3_h": 10.0,
                "heat_duty_kw": -600.0,
                "operating_pressure_mpa": 1.210,
                "temperature_c": 120.0,
                "pressure_basis": "absolute",
            },
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )
        derivation.apply_heat_transfer_service_model_gate(
            match_result,
            classification,
        )
        model = match_result["model_recommendation"]
        self.assertEqual(
            model["status"],
            "HEAT_TRANSFER_TYPE_RETAINED_PRESSURE_DROP_FUNCTION_CONFLICT",
        )
        self.assertEqual(
            match_result["model_decision"][
                "generated_candidate_designation"
            ],
            model["leading_candidate"]["designation"],
        )

    def test_heatx_all_liquid_ports_use_liquid_liquid_type_name(
        self,
    ) -> None:
        classification = derivation.classify_heat_transfer_service(
            block_type="HEATX",
            inlets=[],
            outlets=[],
            heatx_side_mapping={
                "mapped_roles": {
                    role: {"phase": "liquid"}
                    for role in (
                        "hot_side_inlet",
                        "hot_side_outlet",
                        "cold_side_inlet",
                        "cold_side_outlet",
                    )
                },
                "lmtd_candidates": {"invalid_arrangements": []},
                "pressure_drop_candidates": {},
            },
        )

        self.assertEqual(
            classification["recommended_type"],
            "卧式管壳式液-液显热流程换热器",
        )
        self.assertEqual(
            classification["selector_rule_id"],
            "HEATX_TWO_SIDE_SINGLE_PHASE_SENSIBLE",
        )

    def test_tower_audit_never_presents_screening_values_as_final_sizes(
        self,
    ) -> None:
        streams: dict[str, dict[str, object]] = {}
        for stream_id, temperature in (("T-IN", 80.0), ("T-OUT", 90.0)):
            normalized, errors = derivation.normalize_stream(
                {
                    "stream_id": stream_id,
                    "phase": "liquid",
                    "temperature_c": temperature,
                    "pressure_mpa": 0.2,
                    "mass_flow_kg_h": 96_000.0,
                    "volumetric_flow_m3_h": 120.0,
                    "density_kg_m3": 800.0,
                    "dynamic_viscosity_mpa_s": 0.4,
                },
                {},
            )
            self.assertEqual(errors, [])
            streams[stream_id] = normalized
        block, errors = derivation.normalize_block(
            {
                "block_id": "T-1",
                "block_type": "RADFRAC",
                "inlet_streams": ["T-IN"],
                "outlet_streams": ["T-OUT"],
                "stage_count": 30,
            },
            {},
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {
                "block_id": "T-1",
                "equipment_tag": "T-1",
                "process_function": "staged separation",
            },
            streams,
            {
                "case_id": "CASE-TOWER",
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
            },
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        audit = result["tower_preliminary_design_audit"]
        self.assertEqual(
            audit["status"],
            "TYPE_SELECTED_HYDRAULIC_SIZING_BLOCKED",
        )
        self.assertEqual(
            audit["diameter_screening"]["basis"],
            "INLET_LIQUID_TRAFFIC_SURROGATE_NOT_CONTROLLING_TRAY_SECTION",
        )
        self.assertFalse(
            audit["diameter_screening"][
                "controlling_tray_section_selected"
            ]
        )
        mechanical = audit["mechanical_thickness_screening"]
        self.assertFalse(mechanical["nominal_shell_thickness_selected"])
        self.assertFalse(mechanical["nominal_head_thickness_selected"])
        self.assertEqual(
            mechanical["claim"],
            "FORMULA_THICKNESS_ONLY_NOT_NOMINAL_THICKNESS",
        )
        model = result["match_result"]["model_recommendation"]
        self.assertEqual(
            model["status"],
            "TOWER_TYPE_SELECTED_HYDRAULIC_SIZING_BLOCKED",
        )
        designation = model["leading_candidate"]["designation"]
        self.assertIn("screening_detail_ref=", designation)
        self.assertIn("Di_formal=OPEN", designation)
        self.assertIn("H_formal=OPEN", designation)
        self.assertNotIn("Di_screen=", designation)
        self.assertNotIn("H_layout_screen=", designation)
        self.assertNotIn("shell_formula_t=", designation)
        self.assertFalse(
            model["selection_execution"]["formal_selection_executed"]
        )
        decision = result["match_result"]["model_decision"]
        for field_id in (
            "candidate_model",
            "generated_candidate_designation",
        ):
            public_text = str(decision.get(field_id) or "")
            self.assertNotIn("Di_screen=", public_text)
            self.assertNotIn("H_layout_screen=", public_text)
            self.assertNotIn("shell_formula_t=", public_text)
        candidates = [
            *model.get("candidates", []),
            model["leading_candidate"],
        ]
        for candidate in candidates:
            if str(candidate.get("status") or "").startswith("REJECTED_"):
                continue
            specification = candidate.get("specification", {})
            self.assertNotIn("inner_diameter_mm", specification)
            self.assertNotIn("height_mm", specification)
            self.assertEqual(
                specification["formal_tower_diameter_status"],
                "OPEN_CONTROLLING_SECTION_HYDRAULICS",
            )
            self.assertEqual(
                specification["formal_tower_height_status"],
                "OPEN_INTERNALS_AND_MECHANICAL_LAYOUT",
            )

    def test_tower_registered_minimum_fallback_has_numeric_screening_value(
        self,
    ) -> None:
        source = Path(__file__).resolve()
        record: dict[str, object] = {
            "aspen_block_type": "RADFRAC",
            "phase": "mixed",
            "stage_count": 20,
        }
        chain: list[dict[str, object]] = []
        audit = derivation.build_tower_preliminary_design_audit(
            record=record,
            chain=chain,
            match_result={
                "derived_parameters": {},
                "calculations": [],
                "design_fallbacks": [
                    {
                        "field_id": "inner_diameter_mm",
                        "value": 600.0,
                        "unit": "mm",
                    },
                    {
                        "field_id": "tower_design_velocity_m_s",
                        "value": 1.0,
                        "unit": "m/s",
                    },
                ],
            },
            source_file=source,
            source_sha256=derivation.sha256_file(source),
        )

        diameter = audit["diameter_screening"]
        self.assertEqual(diameter["value_mm"], 600.0)
        self.assertEqual(
            diameter["basis"],
            "REGISTERED_600_MM_MINIMUM_WITHOUT_TRAFFIC_FLOW",
        )
        self.assertTrue(diameter["minimum_600_mm_floor_applied"])
        self.assertFalse(diameter["controlling_tray_section_selected"])
        self.assertEqual(
            diameter["claim"],
            "DIAMETER_SCREENING_VALUE_ONLY",
        )
        self.assertFalse(audit["formal_ready"])
        self.assertEqual(record["tower_diameter_screening_mm"], 600.0)
        self.assertTrue(
            any(
                row.get("target_field")
                == "tower_diameter_screening_mm"
                and row.get("value") == 600.0
                for row in chain
            )
        )

    def test_rplug_maps_process_and_coolant_ports_without_whole_body_claim(
        self,
    ) -> None:
        streams: dict[str, dict[str, object]] = {}
        for raw in (
            {
                "stream_id": "FEED",
                "phase": "vapor",
                "temperature_c": 350.0,
                "pressure_mpa": 2.45,
                "mass_flow_kg_h": 50_000.0,
                "volumetric_flow_m3_h": 1_300.0,
                "density_kg_m3": 38.46153846,
                "dynamic_viscosity_mpa_s": 0.017,
            },
            {
                "stream_id": "PRODUCT",
                "phase": "vapor",
                "temperature_c": 400.0,
                "pressure_mpa": 2.44,
                "mass_flow_kg_h": 50_000.0,
                "volumetric_flow_m3_h": 1_250.0,
                "density_kg_m3": 40.0,
                "dynamic_viscosity_mpa_s": 0.018,
            },
            {
                "stream_id": "BFW",
                "phase": "liquid",
                "temperature_c": 120.0,
                "pressure_mpa": 0.98,
                "mass_flow_kg_h": 1_200.0,
                "volumetric_flow_m3_h": 1.4,
                "density_kg_m3": 857.142857,
                "dynamic_viscosity_mpa_s": 0.23,
                "component_mole_fractions": {"H2O": 1.0},
            },
            {
                "stream_id": "STEAM",
                "phase": "vapor",
                "temperature_c": 400.0,
                "pressure_mpa": 0.98,
                "mass_flow_kg_h": 1_200.0,
                "volumetric_flow_m3_h": 250.0,
                "density_kg_m3": 4.8,
                "dynamic_viscosity_mpa_s": 0.015,
                "component_mole_fractions": {"H2O": 1.0},
            },
        ):
            normalized, errors = derivation.normalize_stream(raw, {})
            self.assertEqual(errors, [])
            streams[normalized["stream_id"]] = normalized
        block, errors = derivation.normalize_block(
            {
                "block_id": "R-1",
                "block_type": "RPLUG",
                "inlet_streams": ["FEED", "BFW"],
                "outlet_streams": ["PRODUCT", "STEAM"],
                "port_detail": [
                    {"port": "F(IN)", "streams": ["FEED"]},
                    {"port": "P(OUT)", "streams": ["PRODUCT"]},
                    {"port": "C(IN)", "streams": ["BFW"]},
                    {"port": "C(OUT)", "streams": ["STEAM"]},
                ],
                "diameter_mm": 76.3,
                "heat_duty_kw": -930.0,
            },
            {},
        )
        self.assertEqual(errors, [])
        source = Path(__file__).resolve()
        result = derivation.derive_equipment(
            block,
            {
                "block_id": "R-1",
                "equipment_tag": "R-1",
                "process_function": "plug-flow reaction with heat removal",
            },
            streams,
            {
                "case_id": "CASE-RPLUG",
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
            },
            source,
            derivation.sha256_file(source),
            derivation.matcher.load_rules(),
            derivation.matcher.load_graph(),
        )

        audit = result["rplug_preliminary_design_audit"]
        self.assertEqual(
            audit["coolant_phase_transition"],
            "liquid->vapor",
        )
        self.assertTrue(audit["boiling_water_heat_removal_observed"])
        self.assertIn(
            "壳程蒸汽发生兼过热取热候选",
            audit["recommended_type"],
        )
        thermal = audit["coolant_thermal_service_screening"]
        self.assertEqual(
            thermal["status"],
            "STEAM_GENERATION_AND_SUPERHEAT_SCREENED",
        )
        self.assertGreater(thermal["superheat_margin_c"], 200.0)
        self.assertFalse(thermal["formal_two_zone_rating_complete"])
        geometry = audit["geometry_screening"]
        self.assertAlmostEqual(
            geometry["active_tube_inner_diameter_mm"],
            76.3,
        )
        self.assertFalse(geometry["total_reactor_volume_selected"])
        self.assertFalse(geometry["tube_count_selected"])
        self.assertFalse(geometry["shell_inner_diameter_selected"])
        self.assertEqual(
            geometry["claim"],
            "ONE_ACTIVE_TUBE_GEOMETRY_SCREEN_ONLY_"
            "NOT_WHOLE_REACTOR_DIMENSIONS",
        )
        model = result["match_result"]["model_recommendation"]
        self.assertEqual(
            model["status"],
            "RPLUG_TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
        )
        self.assertIn(
            "total_volume/tube_count/shell_D=OPEN",
            model["leading_candidate"]["designation"],
        )


if __name__ == "__main__":
    unittest.main()
