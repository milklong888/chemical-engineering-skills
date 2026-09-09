from __future__ import annotations

import copy
import io
import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import equipment_design_agent as agent


class EquipmentDesignAgentTests(unittest.TestCase):
    def test_jsonl_session_reuses_one_api_and_returns_one_response_per_request(self) -> None:
        requests = [
            {
                "schema": "equipment-design-agent-request-v1",
                "request_id": "SESSION-1",
                "operation": "capabilities",
                "payload": {},
            },
            {
                "schema": "equipment-design-agent-request-v1",
                "request_id": "SESSION-2",
                "operation": "catalog",
                "payload": {},
            },
        ]
        observed_api_ids: list[int] = []

        def fake_execute(request: object, api: object = None) -> tuple[dict[str, object], int]:
            self.assertIsNotNone(api)
            observed_api_ids.append(id(api))
            request_id = request["request_id"]  # type: ignore[index]
            return {
                "schema": "equipment-design-agent-response-v1",
                "request_id": request_id,
                "ok": True,
                "status": "PASS",
                "exit_code": 0,
            }, 0

        input_stream = io.StringIO("".join(json.dumps(item) + "\n" for item in requests))
        output_stream = io.StringIO()
        with (
            patch.object(agent, "execute_request", side_effect=fake_execute),
            patch.object(sys, "stdin", input_stream),
            patch.object(sys, "stdout", output_stream),
        ):
            code = agent.main(["--session-jsonl"])

        responses = [json.loads(line) for line in output_stream.getvalue().splitlines()]
        self.assertEqual(code, 0)
        self.assertEqual([item["request_id"] for item in responses], ["SESSION-1", "SESSION-2"])
        self.assertEqual(len(set(observed_api_ids)), 1)

    def test_jsonl_session_accepts_utf8_bom_on_first_request_line(self) -> None:
        request = {
            "schema": "equipment-design-agent-request-v1",
            "request_id": "SESSION-BOM-1",
            "operation": "capabilities",
            "payload": {},
        }
        input_stream = io.StringIO("\ufeff" + json.dumps(request) + "\n")
        output_stream = io.StringIO()

        def fake_execute(parsed: object, api: object = None) -> tuple[dict[str, object], int]:
            self.assertIsNotNone(api)
            return {
                "schema": "equipment-design-agent-response-v1",
                "request_id": parsed["request_id"],  # type: ignore[index]
                "ok": True,
                "status": "PASS",
                "exit_code": 0,
            }, 0

        with (
            patch.object(agent, "execute_request", side_effect=fake_execute),
            patch.object(sys, "stdin", input_stream),
            patch.object(sys, "stdout", output_stream),
        ):
            code = agent.main(["--session-jsonl"])

        response = json.loads(output_stream.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(response["ok"])
        self.assertEqual(response["request_id"], "SESSION-BOM-1")
        self.assertEqual(response["exit_code"], 0)

    def test_direct_bkp_cli_constructs_aspen_import_without_request_json(self) -> None:
        captured: dict[str, object] = {}

        def fake_execute(request: object, api: object = None) -> tuple[dict[str, object], int]:
            self.assertIsInstance(request, dict)
            captured.update(request)  # type: ignore[arg-type]
            return {
                "schema": "equipment-design-agent-response-v1",
                "ok": True,
                "status": "PASS",
            }, 0

        output = io.StringIO()
        with patch.object(agent, "execute_request", side_effect=fake_execute), patch.object(sys, "stdout", output):
            code = agent.main([
                "--bkp", str(PACKAGE_ROOT / "case.bkp"),
                "--pressure-basis", "absolute",
                "--no-run",
                "--output", "-",
            ])
        self.assertEqual(code, 0)
        self.assertEqual(captured["operation"], "aspen_import")
        payload = captured["payload"]
        self.assertEqual(payload["source_path"], str((PACKAGE_ROOT / "case.bkp").resolve()))
        self.assertEqual(payload["pressure_basis"], "absolute")
        self.assertFalse(payload["run"])
        self.assertEqual(json.loads(output.getvalue())["status"], "PASS")

    def test_capabilities_require_no_gui_llm_or_com(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "request_id": "CAP-1",
            "operation": "capabilities",
            "payload": {},
        })
        self.assertEqual(code, 0)
        self.assertEqual(response["status"], "PASS")
        self.assertFalse(response["engine"]["gui_required"])
        self.assertFalse(response["engine"]["llm_required"])
        self.assertFalse(response["engine"]["com_required"])
        self.assertIn("hybrid_run", response["result"]["operations"])
        self.assertEqual(
            response["result"]["hybrid"]["fixed_api_key_env"],
            "EQUIPMENT_DESIGN_LLM_API_KEY",
        )
        self.assertFalse(response["result"]["hybrid"]["arbitrary_environment_variable_lookup_allowed"])
        self.assertTrue(response["result"]["knowledge_packages"]["packages"])
        self.assertTrue(response["result"]["runtime_bundle"]["verified"])
        self.assertIn(
            response["result"]["verification_status"],
            {"PASS", "NOT_APPLICABLE_SOURCE_TREE"},
        )
        self.assertIn("bundle_revision", response["result"])
        self.assertIn("manifest_sha256", response["result"])
        self.assertTrue(
            response["result"]["runtime_bundle"]["source_code_manifest"]["verified"]
        )
        self.assertEqual(response["machine_state"]["state"], "COMPLETED")

    def test_runtime_bundle_verification_failure_is_fail_closed(self) -> None:
        verification = {
            "verified": False,
            "verification_status": "FAILED",
            "bundle_revision": "A" * 64,
            "manifest_sha256": "B" * 64,
            "issues": [{"code": "RUNTIME_ASSET_HASH_MISMATCH", "path": "data/example.csv"}],
        }
        with patch.object(
            agent.app_core,
            "require_runtime_bundle",
            side_effect=agent.app_core.runtime_bundle.RuntimeBundleError("tampered"),
        ), patch.object(agent.app_core, "runtime_bundle_verification", return_value=verification):
            response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "request_id": "TAMPER-1",
                "operation": "capabilities",
                "payload": {},
            })
        self.assertEqual(code, 9)
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "RUNTIME_BUNDLE_VERIFICATION_FAILED")
        self.assertEqual(response["errors"][0]["details"], verification)

    def test_manual_fixture_returns_machine_equation_chain(self) -> None:
        request = agent.load_json_file(APP_DIR / "fixtures" / "agent_manual_pump_request.json")
        response, code = agent.execute_request(request)
        self.assertEqual(code, 0)
        self.assertEqual(response["status"], "PASS")
        result = response["result"]["result"]
        self.assertEqual(result["match"]["family_id"], "family_pump")
        self.assertEqual(result["model_recommendation"]["leading_candidate"]["standard_marking"], "65-40-200")
        self.assertTrue(result["model_decision"]["generated_candidate_model"])
        chains = [item["equation_chain"] for item in result["calculations"]]
        self.assertTrue(all(chain.count(" = ") == 3 for chain in chains))

    def test_manual_pump_stdin_stdout_protocol_is_utf8_under_gbk_stdio(self) -> None:
        fixture = APP_DIR / "fixtures" / "agent_manual_pump_request.json"
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "cp936"
        environment["PYTHONUTF8"] = "0"
        completed = subprocess.run(
            [
                sys.executable,
                str(APP_DIR / "equipment_design_agent.py"),
                "--request",
                "-",
                "--output",
                "-",
            ],
            input=fixture.read_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            timeout=60,
            check=False,
        )
        stderr = completed.stderr.decode("utf-8", errors="replace")
        self.assertEqual(completed.returncode, 0, stderr)
        self.assertNotIn("UnicodeEncodeError", stderr)
        stdout = completed.stdout.decode("utf-8")
        self.assertIn("m³/h", stdout)
        response = json.loads(stdout)
        self.assertEqual(response["schema"], "equipment-design-agent-response-v1")
        self.assertEqual(response["result"]["result"]["match"]["family_id"], "family_pump")

    def test_manual_batch_preserves_item_count(self) -> None:
        item = agent.load_json_file(APP_DIR / "fixtures" / "agent_manual_pump_request.json")["payload"]
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "manual_batch",
            "payload": {"items": [item, item]},
        })
        self.assertEqual(code, 0)
        self.assertEqual(response["result"]["count"], 2)

    def test_render_report_outputs_parameter_and_candidate_tables_without_llm(self) -> None:
        manual_request = agent.load_json_file(APP_DIR / "fixtures" / "agent_manual_pump_request.json")
        output = PACKAGE_ROOT / "outputs" / "app_test_runs" / f"report_{uuid.uuid4().hex[:10]}.html"
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "report.render",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": manual_request["payload"],
                },
                "format": "html",
                "output_path": str(output),
            },
        })
        self.assertEqual(code, 0, response)
        presentation = response["result"]["presentation"]
        self.assertEqual(presentation["schema"], "equipment-design-presentation-v1")
        self.assertEqual(presentation["equipment_count"], 1)
        self.assertTrue(presentation["equipment"][0]["parameter_groups"])
        self.assertTrue(presentation["equipment"][0]["candidates"])
        text = output.read_text(encoding="utf-8")
        self.assertIn("参数卡", text)
        self.assertIn("候选型号", text)
        self.assertFalse(presentation["llm_used"])

    def test_render_report_rejects_forged_result_and_recalculates_input(self) -> None:
        forged = {
            "schema": "equipment-deterministic-match-result-v1",
            "status": "MATCHED",
            "model_decision": {"model_status": "final_model"},
            "model_recommendation": {
                "status": "final_model",
                "recommended_type": "FORGED-TYPE",
                "candidates": [{"formal_model": "FORGED-FINAL-MODEL"}],
            },
        }
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "report.render",
            "payload": {"deterministic_result": forged, "format": "json"},
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "UNEXPECTED_PAYLOAD_FIELDS")

        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "render_report",
            "payload": {
                "input": {
                    "operation": "aspen_import",
                    "payload": {"case_path": "untrusted.bkp"},
                },
                "format": "json",
            },
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "HYBRID_SOURCE_NOT_REPLAYABLE")

        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "report.render",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {
                        "selection_id": "block:PUMP",
                        "values": {
                            "equipment_tag": "P-REPORT-STRICT",
                            "phase": "liquid",
                            "flow_m3_h": 20,
                            "head_m": 45,
                            "density_kg_m3": 900,
                            "efficiency_percent": 75,
                            "final_model": "FORGED-FINAL-MODEL",
                        },
                    },
                },
                "format": "json",
            },
        })
        self.assertEqual(code, 0, response)
        self.assertTrue(response["machine_state"]["deterministic_authority"])
        rendered = json.dumps(response["result"]["presentation"], ensure_ascii=False)
        self.assertNotIn("FORGED-FINAL-MODEL", rendered)

    def test_auto_match_one_field_returns_candidates_without_llm(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "equipment.match",
            "payload": {"values": {"flow_m3_h": 20}, "policy": {"llm_allowed": False}},
        })
        self.assertEqual(code, 0, response)
        progress = response["result"]["progress"]
        self.assertEqual(progress["state"], "NEEDS_IDENTITY")
        self.assertGreater(progress["candidate_count"], 1)
        self.assertFalse(progress["llm_used"])

    def test_llm_apply_rejects_raw_legacy_proposal(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_apply",
            "payload": {
                "proposal": {"changes": [
                    {"field": "equipment_type", "value": "离心泵"},
                    {"field": "design_pressure_mpa", "value": "9.9"}
                ]},
                "approval": {
                    "approved": True,
                    "approved_change_ids": ["change_001"],
                    "approved_by": "unit-test",
                    "context_sha256": "A" * 64,
                    "orchestration_sha256": "B" * 64
                }
            }
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "STRICT_ORCHESTRATION_REQUIRED")

    def test_llm_apply_without_explicit_approval_is_rejected(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_apply",
            "payload": {
                "proposal": {"changes": [{"field": "equipment_type", "value": "离心泵"}]},
            },
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "EXPLICIT_APPROVAL_REQUIRED")

    def test_literal_api_key_is_rejected_without_network(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_review",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}}
                },
                "config": {"api_key": "secret", "model": "x"}
            }
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "API_KEY_LITERAL_FORBIDDEN")

    def test_arbitrary_api_key_environment_name_is_rejected_before_network(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_run",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}}
                },
                "knowledge": {"enabled": False},
                "llm": {
                    "enabled": True,
                    "config": {
                        "provider": "openai_compatible",
                        "model": "review-model",
                        "api_key_env": "PATH",
                    },
                },
            },
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "API_KEY_ENV_NOT_ALLOWLISTED")
        self.assertNotIn(os.environ.get("PATH", ""), json.dumps(response))

    def test_agent_remote_base_url_cannot_be_overridden_by_request(self) -> None:
        with patch.dict(os.environ, {
            "EQUIPMENT_DESIGN_LLM_API_KEY": "SENTINEL-KEY",
            "EQUIPMENT_DESIGN_LLM_BASE_URL": "https://trusted.example/v1",
        }, clear=False):
            response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "hybrid_run",
                "payload": {
                    "input": {
                        "operation": "manual_match",
                        "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}},
                    },
                    "knowledge": {"enabled": False},
                    "llm": {
                        "enabled": True,
                        "config": {
                            "provider": "openai_compatible",
                            "base_url": "https://attacker.example/v1",
                            "model": "review-model",
                        },
                    },
                },
            })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "LLM_BASE_URL_LITERAL_FORBIDDEN")
        self.assertNotIn("SENTINEL-KEY", json.dumps(response))

    def test_no_llm_hybrid_needs_no_key_or_endpoint_profile(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EQUIPMENT_DESIGN_LLM_API_KEY", None)
            os.environ.pop("EQUIPMENT_DESIGN_LLM_BASE_URL", None)
            response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "hybrid_run",
                "payload": {
                    "input": {
                        "operation": "manual_match",
                        "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}},
                    },
                    "knowledge": {"enabled": False},
                    "llm": {"enabled": False},
                },
            })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["machine_state"]["state"], "COMPLETED_DETERMINISTIC_ONLY")

    def test_missing_remote_profile_falls_back_to_deterministic_result(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("EQUIPMENT_DESIGN_LLM_BASE_URL", None)
            response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "hybrid_run",
                "payload": {
                    "input": {
                        "operation": "manual_match",
                        "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}},
                    },
                    "knowledge": {"enabled": False},
                    "llm": {"enabled": True, "config": {"provider": "openai_compatible", "model": "x"}},
                },
            })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["machine_state"]["state"], "FALLBACK_DETERMINISTIC")
        self.assertEqual(response["result"]["fallback"]["errors"][0]["code"], "LLM_BASE_URL_PROFILE_MISSING")
        self.assertIsNotNone(response["result"]["deterministic_result"])

    def test_blank_remote_model_id_falls_back_without_network(self) -> None:
        with patch.dict(os.environ, {
            "EQUIPMENT_DESIGN_LLM_BASE_URL": "https://trusted.example/v1",
        }, clear=False):
            os.environ.pop("EQUIPMENT_DESIGN_LLM_MODEL_ID", None)
            with patch.object(agent.llm_bridge, "_request_step_output") as provider_call:
                response, code = agent.execute_request({
                    "schema": "equipment-design-agent-request-v1",
                    "operation": "hybrid_run",
                    "payload": {
                        "input": {
                            "operation": "manual_match",
                            "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}},
                        },
                        "knowledge": {"enabled": False},
                        "llm": {"enabled": True, "config": {"provider": "openai_compatible"}},
                    },
                })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["machine_state"]["state"], "FALLBACK_DETERMINISTIC")
        self.assertEqual(response["result"]["fallback"]["errors"][0]["code"], "LLM_MODEL_ID_MISSING")
        provider_call.assert_not_called()

    def test_agent_model_id_environment_is_the_remote_default(self) -> None:
        with patch.dict(os.environ, {
            "EQUIPMENT_DESIGN_LLM_BASE_URL": "https://trusted.example/v1",
            "EQUIPMENT_DESIGN_LLM_MODEL_ID": "deepseek-chat",
        }, clear=False):
            config = agent._agent_provider_config({"provider": "openai_compatible"})
        self.assertEqual(config["model"], "deepseek-chat")
        self.assertEqual(config["base_url"], "https://trusted.example/v1")

    def test_capabilities_exposes_nonsensitive_model_environment_contract(self) -> None:
        with patch.dict(os.environ, {"EQUIPMENT_DESIGN_LLM_MODEL_ID": "audit-model"}, clear=False):
            response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "capabilities",
                "payload": {},
            })
        self.assertEqual(code, 0, response)
        hybrid = response["result"]["hybrid"]
        self.assertEqual(hybrid["fixed_model_id_env"], "EQUIPMENT_DESIGN_LLM_MODEL_ID")
        self.assertEqual(hybrid["configured_default_model_id"], "audit-model")
        self.assertNotIn('"api_key":', json.dumps(hybrid).casefold())

    def test_openai_http_400_and_refusal_fall_back_without_mutating_result(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {
                    "equipment_tag": "P-PROVIDER-FALLBACK",
                    "phase": "liquid",
                    "flow_m3_h": 20,
                    "head_m": 45,
                    "density_kg_m3": 900,
                    "efficiency_percent": 75,
                },
            },
        }
        deterministic_response, deterministic_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "manual_match",
            "payload": source_input["payload"],
        })
        self.assertEqual(deterministic_code, 0, deterministic_response)
        expected = deterministic_response["result"]

        class RefusalResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read() -> bytes:
                return json.dumps({
                    "choices": [{"message": {"refusal": "cannot review"}}],
                }).encode("utf-8")

        cases = {
            "http_400": agent.llm_bridge.urllib.error.HTTPError(
                "https://api.openai.com/v1/chat/completions",
                400,
                "bad schema",
                {},
                io.BytesIO(b'{"error":"provider rejected schema"}'),
            ),
            "refusal": RefusalResponse(),
        }
        self.addCleanup(cases["http_400"].close)
        for label, provider_result in cases.items():
            with self.subTest(label=label), patch.dict(
                os.environ,
                {"EQUIPMENT_DESIGN_LLM_API_KEY": "SENTINEL-KEY"},
                clear=False,
            ):
                if isinstance(provider_result, Exception):
                    provider_patch = patch.object(
                        agent.llm_bridge.urllib.request,
                        "urlopen",
                        side_effect=provider_result,
                    )
                else:
                    provider_patch = patch.object(
                        agent.llm_bridge.urllib.request,
                        "urlopen",
                        return_value=provider_result,
                    )
                with provider_patch:
                    response, code = agent.execute_request({
                        "schema": "equipment-design-agent-request-v1",
                        "operation": "hybrid_run",
                        "payload": {
                            "input": source_input,
                            "knowledge": {"enabled": False},
                            "injection_point": "audit",
                            "context_scope": "minimum",
                            "llm": {
                                "enabled": True,
                                "config": {"provider": "openai", "model": "review-model"},
                            },
                        },
                    })
            self.assertEqual(code, 0, response)
            hybrid = response["result"]
            self.assertEqual(hybrid["machine_state"]["state"], "FALLBACK_DETERMINISTIC")
            self.assertTrue(hybrid["fallback"]["used"])
            self.assertEqual(hybrid["deterministic_result"], expected)
            self.assertNotIn("SENTINEL-KEY", json.dumps(response))

    def test_legacy_llm_review_name_returns_strict_result_consumable_by_apply(self) -> None:
        manual_values = {
            "equipment_tag": "P-STRICT-LEGACY",
            "phase": "liquid",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }
        deterministic = agent.app_core.manual_match("block:PUMP", manual_values)
        prepared_response = agent.EquipmentDesignApi().hybrid_prepare(
            deterministic,
            {"enabled": False},
            "semantic_extraction",
            "minimum",
        )
        self.assertTrue(prepared_response["ok"])
        prepared = prepared_response["value"]
        step_output = {
            "schema": agent.llm_bridge.STEP_OUTPUT_SCHEMA,
            "injection_point": "semantic_extraction",
            "context_sha256": prepared["context_pack"]["context_sha256"],
            "summary": "strict compatibility review",
            "citations": [],
            "proposed_changes": [{
                "field": "process_function",
                "value": "液体输送",
                "reason": "manual service text",
                "citations": ["deterministic_result"],
            }],
            "condition_assessments": [],
            "calculation_assists": [],
            "retrieval_plan": [],
            "ambiguity_decision": None,
            "audit_findings": [],
            "output_composition": {
                "title": "Strict compatibility review",
                "blocks": [
                    {
                        "block_id": "summary", "operation": "explain_result",
                        "section_ref": "summary", "heading": "Summary",
                        "citations": ["deterministic_result"],
                    },
                    {
                        "block_id": "proposed_changes", "operation": "propose_descriptive_change",
                        "section_ref": "proposed_changes", "heading": "Descriptive change",
                        "citations": ["deterministic_result"],
                    },
                ],
            },
        }
        review_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_review",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {"selection_id": "block:PUMP", "values": manual_values},
                },
                "knowledge": {"enabled": False},
                "injection_point": "semantic_extraction",
                "context_scope": "minimum",
                "config": {"provider": "mock", "mock_response": step_output},
            },
        })
        self.assertEqual(code, 0, review_response)
        orchestration = review_response["result"]
        self.assertEqual(orchestration["schema"], agent.llm_bridge.ORCHESTRATION_SCHEMA)
        apply_response, apply_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_apply",
            "payload": {
                "proposal": orchestration,
                "approval": {
                    "approved": True,
                    "approved_change_ids": ["change_001"],
                    "approved_by": "unit-test",
                    "context_sha256": orchestration["context_sha256"],
                    "orchestration_sha256": orchestration["orchestration_sha256"],
                },
            },
        })
        self.assertEqual(apply_code, 0, apply_response)
        self.assertEqual(apply_response["result"]["applied_draft"]["process_function"], "液体输送")

    def test_hybrid_manual_run_can_be_fully_agent_owned_without_llm(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "request_id": "HYBRID-MANUAL-1",
            "operation": "hybrid_run",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {
                        "selection_id": "block:PUMP",
                        "values": {
                            "equipment_tag": "P-HYBRID-1",
                            "phase": "liquid",
                            "flow_m3_h": 20,
                            "head_m": 45,
                            "density_kg_m3": 900,
                            "efficiency_percent": 75
                        }
                    }
                },
                "knowledge": {"enabled": False},
                "llm": {"enabled": False}
            }
        })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["operation"], "hybrid_run")
        self.assertEqual(response["machine_state"]["state"], "COMPLETED_DETERMINISTIC_ONLY")
        hybrid = response["result"]
        self.assertEqual(hybrid["schema"], "equipment-design-hybrid-result-v2")
        self.assertEqual(
            hybrid["deterministic_result"]["result"]["match"]["family_id"],
            "family_pump",
        )
        self.assertEqual(hybrid["llm_review"]["status"], "NOT_REQUESTED")

    def test_hybrid_run_rejects_literal_api_key(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_run",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {"selection_id": "block:PUMP", "values": {"flow_m3_h": 20}}
                },
                "knowledge": {"enabled": False},
                "llm": {"enabled": True, "config": {"api_key": "must-not-enter-json"}}
            }
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "API_KEY_LITERAL_FORBIDDEN")
        self.assertNotIn("must-not-enter-json", json.dumps(response))

    def test_mock_aspen_import_runs_in_worker_and_returns_artifact(self) -> None:
        parent = PACKAGE_ROOT / "outputs" / "app_test_runs"
        parent.mkdir(parents=True, exist_ok=True)
        output = parent / f"agent_mock_{uuid.uuid4().hex[:10]}"
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "aspen_import",
            "payload": {
                "mock_fixture": str(APP_DIR / "fixtures" / "mock_aspen_pump.json"),
                "output_dir": str(output),
                "pressure_basis": "absolute",
                "timeout_s": 30
            }
        })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["status"], "PASS_MOCK")
        self.assertTrue(response["artifacts"])
        self.assertTrue(all(len(item["sha256"]) == 64 for item in response["artifacts"]))
        self.assertTrue((output / "worker_result.json").is_file())

    def test_direct_aspen_export_derivation_needs_no_com(self) -> None:
        source = PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
        output = PACKAGE_ROOT / "outputs" / "app_test_runs" / f"derive_{uuid.uuid4().hex[:10]}.json"
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "aspen.export.derive",
            "payload": {"export_path": str(source), "output_path": str(output)},
        })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["equipment"][0]["match_result"]["match"]["family_id"], "family_pump")
        self.assertTrue(output.is_file())

    def test_customer_export_accepts_aspen_derivation_and_returns_authoritative_overview_row(self) -> None:
        source = PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "customer_export",
            "payload": {
                "input": {
                    "operation": "aspen_derive",
                    "payload": {"export_path": str(source)},
                }
            },
        })
        self.assertEqual(code, 0, response)
        delivery = response["result"]["customer_delivery"]
        overview = delivery["equipment_overview_table"]
        self.assertTrue(delivery["deterministic"])
        self.assertFalse(delivery["llm_used"])
        self.assertEqual(overview["authority_contract"], "3-2-equipment-selection-overview-v1")
        self.assertEqual(overview["row_count"], 3)
        equipment_rows = [
            item
            for item in overview["rows"]
            if item.get("record_kind") == "equipment"
        ]
        piping_rows = [
            item
            for item in overview["rows"]
            if item.get("record_kind") == "piping"
        ]
        self.assertEqual(len(equipment_rows), 1)
        self.assertEqual(len(piping_rows), 2)
        self.assertTrue(
            all(
                item["selection_specificity_gate"]["selection_identity"][
                    "detailed_designation"
                ]
                for item in piping_rows
            )
        )
        self.assertTrue(
            all(
                item["selection_specificity_gate"]["state"] == "BLOCKED"
                and {
                    "medium_name",
                    "dynamic_viscosity_mpa_s",
                }.issubset(item["selection_specificity_gate"]["blocking_fields"])
                for item in piping_rows
            )
        )
        row = equipment_rows[0]
        self.assertEqual(row["authority_table_id"], "T01")
        self.assertTrue(row["authority_columns"])
        self.assertEqual(len(row["authority_cells"]), len(row["authority_columns"]))
        self.assertTrue(row["equipment_type"])
        self.assertTrue(row["model_or_specification"])
        self.assertTrue(row["model_or_specification_status"])
        datasheet = delivery["equipment_family_datasheet"]["equipment"][0]
        self.assertRegex(datasheet["service_profile_context_sha256"], r"^[A-F0-9]{64}$")
        self.assertEqual(datasheet["automatic_service_summary"]["module.intent"], "liquid_pressure_increase")
        evidence_kinds = {
            item["evidence_kind"]
            for item in delivery["equipment_evidence_index"]["records"]
        }
        self.assertIn("automatic_service_profile", evidence_kinds)
        self.assertIn("connection_component_selection_package", evidence_kinds)

    def test_customer_export_projects_valve_into_complete_additive_x05_row(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "customer_export",
            "payload": {
                "input": {
                    "operation": "manual_match",
                    "payload": {
                        "selection_id": "block:VALVE",
                        "values": {
                            "equipment_tag": "XV-101",
                            "pressure_drop_kpa": 80.0,
                            "operating_pressure_mpa": 0.8,
                        },
                    },
                }
            },
        })
        self.assertEqual(code, 0, response)
        row = response["result"]["customer_delivery"]["equipment_overview_table"]["rows"][0]
        self.assertEqual(row["authority_table_id"], "X05")
        self.assertTrue(row["authority_columns"])
        self.assertEqual(len(row["authority_cells"]), len(row["authority_columns"]))
        explicitly_open = {
            "cv",
            "quantity_count",
            "flashing_check_ref",
            "cavitation_check_ref",
            "noise_check_ref",
            "vendor_datasheet_ref",
        }
        self.assertEqual(
            set(row["authority_missing_fields"]),
            explicitly_open,
        )
        self.assertEqual(
            row["authority_completeness"]["state"],
            "COMPLETE_WITH_EXPLICIT_OPEN_GATES",
        )
        authority = {item["field_id"]: item for item in row["authority_cells"]}
        for field_id in (
            "dn_nps", "pressure_temperature_rating", "maximum_pressure_drop_kpa",
            "body_material_grade", "internals_material_grade", "seat_material_grade",
            "connection_type", "leakage_class", "actuator_type", "fail_position",
            "operating_range_and_rangeability",
        ):
            self.assertIsNotNone(authority[field_id]["value"], field_id)
        for field_id in explicitly_open:
            self.assertIsNone(authority[field_id]["value"], field_id)
            self.assertEqual(
                authority[field_id]["state"],
                "OPEN_FORMAL_EVIDENCE_GATE",
            )
            self.assertEqual(
                authority[field_id]["source"]["evidence_class"],
                "U",
            )
            self.assertEqual(
                authority[field_id]["promotion_cap"],
                "NOT_PROMOTABLE",
            )
        self.assertEqual(authority["fail_position"]["source"]["evidence_class"], "J")
        self.assertTrue(row["equipment_type"])
        self.assertTrue(row["model_or_specification"])

    def test_flange_component_selector_populates_customer_fields_and_rejects_free_gasket_text(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "manual_match",
            "payload": {
                "selection_id": "family:family_flange_gasket",
                "values": {
                    "equipment_tag": "FG-CUSTOMER",
                    "selected_dn": "DN50",
                    "pressure_class": "PN16",
                    "flange_face": "RF",
                    "gasket_material": "invented foam gasket",
                    "phase": "liquid",
                },
            },
        })
        self.assertEqual(code, 0, response)
        result = response["result"]["result"]
        self.assertNotIn(
            "invented foam gasket",
            result["model_recommendation"]["leading_candidate"]["designation"],
        )
        datasheet = result["customer_delivery"]["equipment_family_datasheet"]["equipment"][0]
        fields = {item["field_id"]: item for item in datasheet["fields"]}
        self.assertEqual(fields["flange_type"]["source"]["kind"], "deterministic_connection_selector")
        self.assertIn("WN", fields["flange_type"]["value"])
        self.assertEqual(fields["flange_face"]["value"], "RF")
        self.assertEqual(fields["gasket_type_code"]["value"], "D")
        self.assertIn("FULL-STUD", fields["fastener_specification"]["value"])

    def test_headless_selftest_passes(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "system.selftest",
            "payload": {},
        })
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["status"], "PASS")
        self.assertIn("bundle_revision", response["result"])
        self.assertIn("manifest_sha256", response["result"])
        self.assertIn(
            response["result"]["verification_status"],
            {"PASS", "NOT_APPLICABLE_SOURCE_TREE"},
        )
        self.assertTrue(response["ok"])
        self.assertEqual(response["exit_code"], 0)

    def test_all_families_return_a_concrete_deterministic_type_without_placeholders(self) -> None:
        fixture = agent.load_json_file(
            APP_DIR / "fixtures" / "all_family_minimum_meaningful_inputs.json"
        )
        observed: dict[str, tuple[str, str]] = {}
        for case in fixture["cases"]:
            matched = agent.app_core.auto_match({
                "equipment_family": case["family_id"],
                **case["values"],
            })["result"]
            leading = matched["model_recommendation"]["leading_candidate"]
            family_id = case["family_id"]
            with self.subTest(family_id=family_id):
                self.assertEqual(
                    leading["candidate_kind"],
                    case["expected_candidate_kind"],
                )
                self.assertNotEqual(
                    leading["candidate_kind"],
                    "generic_type_placeholder",
                )
                self.assertEqual(
                    leading["recommended_type"],
                    case["expected_recommended_type"],
                )
                self.assertTrue(
                    leading["type_name_quality"]["is_concrete"],
                    leading["type_name_quality"],
                )
                self.assertTrue(leading["designation"])
                self.assertFalse(leading["formal_model"])
                self.assertFalse(leading["is_vendor_model"])
                observed[family_id] = (
                    leading["candidate_kind"],
                    leading["recommended_type"],
                )
        self.assertEqual(len(observed), fixture["expected_family_count"])
        self.assertEqual(
            observed["family_process_piping"],
            ("engineered_designation", "无缝钢制工艺管道"),
        )
        self.assertEqual(
            observed["family_pipe_fitting"],
            ("component_marking", "对焊钢制管件"),
        )
        self.assertEqual(
            observed["family_flange_gasket"],
            ("component_marking", "带颈对焊法兰配缠绕垫片"),
        )

    def test_request_id_contract_is_strict(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "request_id": "bad id with spaces",
            "operation": "capabilities",
            "payload": {},
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "INVALID_REQUEST_ID")

    def test_hybrid_prepare_rejects_naked_deterministic_result(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "deterministic_result": {
                    "status": "MATCHED",
                    "final_model": "FORGED-MODEL",
                },
            },
        })
        self.assertEqual(code, 2)
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "UNEXPECTED_PAYLOAD_FIELDS")
        self.assertIsNone(response["result"])

    def test_hybrid_continue_rejects_prepared_and_replay_tampering(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {
                    "equipment_tag": "P-TAMPER",
                    "phase": "liquid",
                    "flow_m3_h": 20,
                    "head_m": 45,
                    "density_kg_m3": 900,
                    "efficiency_percent": 75,
                },
            },
        }
        prepared_response, prepare_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(prepare_code, 0, prepared_response)
        prepared = prepared_response["result"]
        step_output = {
            "schema": agent.llm_bridge.STEP_OUTPUT_SCHEMA,
            "injection_point": "audit",
            "context_sha256": prepared["context_pack"]["context_sha256"],
            "summary": "checked",
            "citations": [],
            "proposed_changes": [],
            "condition_assessments": [],
            "calculation_assists": [],
            "retrieval_plan": [],
            "ambiguity_decision": None,
            "audit_findings": [],
            "output_composition": {
                "title": "Checked",
                "blocks": [{
                    "block_id": "summary", "operation": "explain_result",
                    "section_ref": "summary", "heading": "Summary",
                    "citations": ["deterministic_result"],
                }],
            },
        }

        tampered_prepared = copy.deepcopy(prepared)
        tampered_prepared["context_pack"]["sources"][0]["content"]["status"] = "FORGED"
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": tampered_prepared, "step_output": step_output},
        })
        self.assertEqual(code, 3)
        self.assertEqual(response["errors"][0]["code"], "HYBRID_PREPARED_HASH_MISMATCH")

        tampered_replay = copy.deepcopy(prepared)
        tampered_replay["replay_contract"]["input"]["payload"]["values"]["flow_m3_h"] = 999
        tampered_replay["prepared_sha256"] = agent.sha256_json({
            key: value for key, value in tampered_replay.items() if key != "prepared_sha256"
        })
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": tampered_replay, "step_output": step_output},
        })
        self.assertEqual(code, 3)
        self.assertEqual(response["errors"][0]["code"], "HYBRID_DETERMINISTIC_REPLAY_MISMATCH")

    def test_authority_revision_binds_all_schemas_and_blocks_schema_drift_continue_apply(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {
                    "equipment_tag": "P-AUTHORITY",
                    "phase": "liquid",
                    "flow_m3_h": 20,
                    "head_m": 45,
                    "density_kg_m3": 900,
                    "efficiency_percent": 75,
                },
            },
        }
        prepared_response, prepare_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "semantic_extraction",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(prepare_code, 0, prepared_response)
        prepared = prepared_response["result"]
        revision = prepared["authority_revision"]
        self.assertEqual(
            revision,
            prepared["replay_contract"]["authority_revision"],
        )
        self.assertEqual(revision["agent_protocol_version"], agent.PROTOCOL_VERSION)
        self.assertEqual(revision["runtime_manifest"]["status"], "NOT_PACKAGED")
        self.assertIsNone(revision["runtime_manifest"]["manifest_sha256"])
        expected_schema_paths = {
            f"app/schemas/{path.name}"
            for path in (APP_DIR / "schemas").glob("*.json")
        }
        self.assertEqual(
            set(revision["schema_asset_sha256"]),
            expected_schema_paths,
        )
        self.assertEqual(
            revision["schema_asset_set_sha256"],
            agent.authority_revision.canonical_sha256(
                revision["schema_asset_sha256"]
            ),
        )
        self.assertEqual(
            set(revision["source_code_sha256"]),
            set(agent.authority_revision.source_code_manifest.CORE_SOURCE_PATHS),
        )
        self.assertEqual(
            revision["source_code_set_sha256"],
            agent.authority_revision.canonical_sha256(
                revision["source_code_sha256"]
            ),
        )
        self.assertEqual(
            revision["source_code_manifest"]["status"],
            "SOURCE_TREE_VERIFIED",
        )
        self.assertEqual(
            revision["source_code_manifest"]["file_count"],
            len(agent.authority_revision.source_code_manifest.CORE_SOURCE_PATHS),
        )
        expected_source_runtime_revision = agent.authority_revision.canonical_sha256({
            "core_asset_set_sha256": revision["core_asset_set_sha256"],
            "schema_asset_set_sha256": revision["schema_asset_set_sha256"],
            "source_code_set_sha256": revision["source_code_set_sha256"],
        })
        self.assertEqual(
            revision["runtime_manifest"]["bundle_revision"],
            expected_source_runtime_revision,
        )
        self.assertEqual(
            revision["authority_revision_sha256"],
            agent.authority_revision.canonical_sha256({
                key: value
                for key, value in revision.items()
                if key != "authority_revision_sha256"
            }),
        )
        step_output = {
            "schema": agent.llm_bridge.STEP_OUTPUT_SCHEMA,
            "injection_point": "semantic_extraction",
            "context_sha256": prepared["context_pack"]["context_sha256"],
            "summary": "checked under one deterministic authority revision",
            "citations": [],
            "proposed_changes": [{
                "field": "process_function",
                "value": "液体输送",
                "reason": "manual service text",
                "citations": ["deterministic_result"],
            }],
            "condition_assessments": [],
            "calculation_assists": [],
            "retrieval_plan": [],
            "ambiguity_decision": None,
            "audit_findings": [],
            "output_composition": {
                "title": "Authority-bound review",
                "blocks": [
                    {
                        "block_id": "summary", "operation": "explain_result",
                        "section_ref": "summary", "heading": "Summary",
                        "citations": ["deterministic_result"],
                    },
                    {
                        "block_id": "proposed_changes", "operation": "propose_descriptive_change",
                        "section_ref": "proposed_changes", "heading": "Descriptive change",
                        "citations": ["deterministic_result"],
                    },
                ],
            },
        }
        continue_response, continue_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": prepared, "step_output": step_output},
        })
        self.assertEqual(continue_code, 0, continue_response)
        orchestration = continue_response["result"]
        self.assertEqual(orchestration["authority_revision"], revision)
        self.assertEqual(
            orchestration["replay_contract"]["authority_revision"],
            revision,
        )

        drifted = copy.deepcopy(revision)
        drifted_schema_path = sorted(drifted["schema_asset_sha256"])[0]
        old_schema_hash = drifted["schema_asset_sha256"][drifted_schema_path]
        drifted["schema_asset_sha256"][drifted_schema_path] = (
            "B" * 64 if old_schema_hash == "A" * 64 else "A" * 64
        )
        drifted["schema_asset_set_sha256"] = agent.authority_revision.canonical_sha256(
            drifted["schema_asset_sha256"]
        )
        drifted["runtime_manifest"]["bundle_revision"] = (
            agent.authority_revision.canonical_sha256({
                "core_asset_set_sha256": drifted["core_asset_set_sha256"],
                "schema_asset_set_sha256": drifted["schema_asset_set_sha256"],
                "source_code_set_sha256": drifted["source_code_set_sha256"],
            })
        )
        drifted["authority_revision_sha256"] = agent.authority_revision.canonical_sha256({
            key: value
            for key, value in drifted.items()
            if key != "authority_revision_sha256"
        })
        with patch.object(
            agent.authority_revision,
            "current_authority_revision",
            return_value=drifted,
        ):
            drift_continue, drift_continue_code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "hybrid_continue",
                "payload": {"prepared": prepared, "step_output": step_output},
            })
            self.assertEqual(drift_continue_code, 3)
            self.assertEqual(
                drift_continue["errors"][0]["code"],
                "HYBRID_AUTHORITY_REVISION_MISMATCH",
            )
            drift_apply, drift_apply_code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "llm_apply",
                "payload": {
                    "proposal": orchestration,
                    "approval": {
                        "approved": True,
                        "approved_change_ids": ["change_001"],
                        "approved_by": "unit-test",
                        "context_sha256": orchestration["context_sha256"],
                        "orchestration_sha256": orchestration["orchestration_sha256"],
                    },
                },
            })
            self.assertEqual(drift_apply_code, 3)
            self.assertEqual(
                drift_apply["errors"][0]["code"],
                "HYBRID_AUTHORITY_REVISION_MISMATCH",
            )

        forged = copy.deepcopy(revision)
        forged["core_asset_sha256"]["rules"] = "A" * 64
        forged["core_asset_set_sha256"] = agent.authority_revision.canonical_sha256(
            forged["core_asset_sha256"]
        )
        forged["runtime_manifest"]["bundle_revision"] = agent.authority_revision.canonical_sha256({
            "core_asset_set_sha256": forged["core_asset_set_sha256"],
            "schema_asset_set_sha256": forged["schema_asset_set_sha256"],
            "source_code_set_sha256": forged["source_code_set_sha256"],
        })
        forged["authority_revision_sha256"] = agent.authority_revision.canonical_sha256({
            key: value
            for key, value in forged.items()
            if key != "authority_revision_sha256"
        })
        tampered = copy.deepcopy(prepared)
        tampered["authority_revision"] = forged
        tampered["replay_contract"]["authority_revision"] = forged
        tampered["prepared_sha256"] = agent.sha256_json({
            key: value
            for key, value in tampered.items()
            if key != "prepared_sha256"
        })
        tamper_response, tamper_code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": tampered, "step_output": step_output},
        })
        self.assertEqual(tamper_code, 3)
        self.assertEqual(
            tamper_response["errors"][0]["code"],
            "HYBRID_AUTHORITY_REVISION_MISMATCH",
        )

    def test_invalid_phase_is_blocked_by_deterministic_matcher(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {
                    "equipment_tag": "P-BANANA",
                    "phase": "banana",
                    "flow_m3_h": 20,
                    "head_m": 45,
                    "density_kg_m3": 900,
                    "efficiency_percent": 75,
                },
            },
        })
        self.assertEqual(code, 0, response)
        deterministic = response["result"]["result"]
        self.assertEqual(deterministic["status"], "BLOCKED_INVALID_PARAMETERS")
        self.assertEqual(deterministic["parameter_errors"][0]["code"], "INVALID_PHASE")
        self.assertNotIn("model_recommendation", deterministic)

    def test_schema_get_and_unknown_top_level_field_are_strict(self) -> None:
        capabilities, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "capabilities",
            "payload": {},
        })
        self.assertEqual(code, 0, capabilities)
        self.assertIn(
            "equipment-design-authority-revision-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        self.assertIn(
            "equipment-design-source-code-manifest-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        self.assertIn(
            "equipment-design-report-status-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        self.assertIn(
            "equipment-service-profile-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        self.assertIn(
            "aspen-equipment-export-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        self.assertIn(
            "equipment-formula-trace-v1",
            {item["schema_id"] for item in capabilities["result"]["schemas"]},
        )
        catalog_entry = next(
            item for item in capabilities["result"]["schemas"]
            if item["schema_id"] == "equipment-design-llm-step-output-v1"
        )
        schema_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "schema_get",
            "payload": {"schema_id": "equipment-design-llm-step-output-v1"},
        })
        self.assertEqual(code, 0, schema_response)
        self.assertEqual(schema_response["result"]["sha256"], catalog_entry["sha256"])
        self.assertEqual(
            schema_response["result"]["document"]["$id"],
            "equipment-design-llm-step-output-v1",
        )

        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "capabilities",
            "payload": {},
            "unexpected": True,
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "UNEXPECTED_REQUEST_FIELDS")

    def test_unknown_operation_has_nonzero_exit_code(self) -> None:
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "click_the_gui",
            "payload": {},
        })
        self.assertEqual(code, 2)
        self.assertEqual(response["status"], "FAILED")
        self.assertEqual(response["errors"][0]["code"], "UNSUPPORTED_OPERATION")


if __name__ == "__main__":
    unittest.main()
