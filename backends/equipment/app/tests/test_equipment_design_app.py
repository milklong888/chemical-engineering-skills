from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import equipment_design_app
import equipment_design_agent


class EquipmentDesignAppAspenTests(unittest.TestCase):
    def test_report_status_sidecar_accepts_normal_deterministic_report(self) -> None:
        with TemporaryDirectory() as temporary_text:
            temporary = Path(temporary_text)
            report_path = temporary / "report.html"
            request_path = temporary / "request.json"
            response_path = temporary / "response.json"
            status_path = temporary / "status.json"
            request = {
                "schema": "equipment-design-agent-request-v1",
                "request_id": "REPORT-STATUS-PASS",
                "operation": "render_report",
                "payload": {
                    "input": {
                        "operation": "manual_match",
                        "payload": {
                            "selection_id": "block:PUMP",
                            "values": {
                                "equipment_tag": "P-REPORT-STATUS",
                                "phase": "liquid",
                                "pressure_basis": "absolute",
                                "flow_m3_h": 20,
                                "inlet_pressure_mpa": 0.2,
                                "outlet_pressure_mpa": 0.6,
                                "density_kg_m3": 900,
                                "efficiency_percent": 75,
                            },
                        },
                    },
                    "format": "html",
                    "output_path": str(report_path),
                },
            }
            request_path.write_text(
                json.dumps(request, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            response, exit_code = equipment_design_agent.execute_request(request)
            self.assertEqual(exit_code, 0, response)
            response_path.write_text(
                json.dumps(response, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            status = equipment_design_app.write_report_status(
                status_path,
                request_path,
                response_path,
                process_exit_code=exit_code,
            )

            self.assertEqual(status["schema"], "equipment-design-report-status-v1")
            self.assertEqual(status["status"], "PASS")
            self.assertTrue(status["normal_content"])
            self.assertEqual(status["content_summary"]["equipment_count"], 1)
            self.assertGreater(status["content_summary"]["parameter_group_count"], 0)
            self.assertTrue(report_path.is_file())
            self.assertEqual(
                status["report"]["sha256"],
                equipment_design_app._sha256_file(report_path),
            )
            persisted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "PASS")

    def test_report_status_sidecar_fails_closed_on_missing_response(self) -> None:
        with TemporaryDirectory() as temporary_text:
            temporary = Path(temporary_text)
            request_path = temporary / "request.json"
            response_path = temporary / "missing-response.json"
            status_path = temporary / "status.json"
            request_path.write_text(
                json.dumps({
                    "schema": "equipment-design-agent-request-v1",
                    "operation": "render_report",
                    "payload": {},
                })
                + "\n",
                encoding="utf-8",
            )

            status = equipment_design_app.write_report_status(
                status_path,
                request_path,
                response_path,
                process_exit_code=8,
                execution_error="simulated failure",
            )

            self.assertEqual(status["status"], "FAIL")
            self.assertFalse(status["normal_content"])
            self.assertTrue(status["errors"])
            self.assertFalse(status["response"]["exists"])

    def test_import_rejects_missing_pressure_basis_before_creating_session(self) -> None:
        api = equipment_design_app.EquipmentDesignApi()
        fixture = APP_DIR / "fixtures" / "mock_aspen_pump.json"
        output = PACKAGE_ROOT / "outputs" / "app_test_runs" / f"app_missing_basis_{uuid.uuid4().hex[:10]}"
        response = api.import_aspen({
            "mock_fixture": str(fixture),
            "output_dir": str(output),
            "pressure_basis": "",
        })
        self.assertFalse(response["ok"])
        self.assertIn("程序不默认", response["error"])
        self.assertFalse(output.exists())

    def test_import_rejects_gauge_without_atmosphere_before_creating_session(self) -> None:
        api = equipment_design_app.EquipmentDesignApi()
        fixture = APP_DIR / "fixtures" / "mock_aspen_pump.json"
        output = PACKAGE_ROOT / "outputs" / "app_test_runs" / f"app_gauge_no_atmosphere_{uuid.uuid4().hex[:10]}"
        response = api.import_aspen({
            "mock_fixture": str(fixture),
            "output_dir": str(output),
            "pressure_basis": "gauge",
            "atmospheric_pressure_mpa": "",
        })
        self.assertFalse(response["ok"])
        self.assertIn("必须填写当地大气压", response["error"])
        self.assertFalse(output.exists())

    def test_import_mock_absolute_atmosphere_reaches_worker_and_result(self) -> None:
        api = equipment_design_app.EquipmentDesignApi()
        fixture = APP_DIR / "fixtures" / "mock_aspen_pump.json"
        output = PACKAGE_ROOT / "outputs" / "app_test_runs" / f"app_absolute_atmosphere_{uuid.uuid4().hex[:10]}"
        response = api.import_aspen({
            "mock_fixture": str(fixture),
            "output_dir": str(output),
            "pressure_basis": "absolute",
            "atmospheric_pressure_mpa": "0.101325",
            "run": False,
            "timeout_s": 60,
        })
        self.assertTrue(response["ok"], response.get("error"))
        worker = response["value"]
        self.assertEqual(worker["status"], "PASS_MOCK")
        canonical = worker["result"]["equipment"][0]["canonical_match_input"]
        self.assertEqual(canonical["pressure_basis"], "absolute")
        self.assertAlmostEqual(canonical["atmospheric_pressure_mpa"], 0.101325)
        persisted = json.loads((output / "worker_result.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["status"], "PASS_MOCK")
        self.assertEqual(api.active_worker_count(), 0)


if __name__ == "__main__":
    unittest.main()
