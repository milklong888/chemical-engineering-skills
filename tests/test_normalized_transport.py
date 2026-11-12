"""Real stdio integration of the existing expert MCP and nine offline operations."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(os.environ.get("CHEMICAL_MODULE_TEST_RUNTIME",Path(__file__).resolve().parents[1]))
SKILLS=Path(os.environ.get("CHEMICAL_MODULE_TEST_SKILLS",ROOT/"plugins/chemical-engineering-skills/skills"))


class NormalizedTransportTests(unittest.TestCase):
    def test_nine_operations_and_numeric_rejection_over_actual_stdio(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def run():
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                data=b"synthetic payload\n"
                (root/"payload.txt").write_bytes(data)
                manifest=root/"manifest.json"
                manifest.write_text(json.dumps({"files":[{"path":"payload.txt","size":len(data),"sha256":hashlib.sha256(data).hexdigest()}]}),encoding="utf-8")
                csv=root/"grid.csv"
                csv.write_text("time,value\n0,1\n1,2\n2,3\n",encoding="utf-8")
                history=root/"history.his"
                history.write_text("NO ERRORS OR WARNINGS GENERATED\n",encoding="ascii")
                grid=dict(csv_path=str(csv),time_column="time",interval=1,start=0,end=2,time_abs_tolerance=0,numeric_columns=["value"])
                cat=json.loads((SKILLS/"aspen-plus-operations/scripts/dynamics_tools/tool_catalog.json").read_text(encoding="utf-8"))
                chosen=next(x for x in cat["tools"] if x["category"]!="local-python-library")
                external=root/"external"
                entry=external/chosen["entry"]
                entry.parent.mkdir(parents=True)
                entry.write_text("raise RuntimeError('must never be executed')\n",encoding="utf-8")
                settings=root/"settings.json"
                settings.write_text(json.dumps({"paths":{chosen["id"]:str(external)},"interpreters":{chosen["id"]:sys.executable}}),encoding="utf-8")
                params=StdioServerParameters(command=sys.executable,args=["-B","-X","utf8",str(ROOT/"tools/expert_mcp.py")],cwd=str(ROOT))
                async with stdio_client(params) as (read,write):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        names={x.name for x in (await session.list_tools()).tools}
                        self.assertTrue({"module_catalog","module_check","knowledge_search","equipment_calculate"}<=names)

                        async def request(tool,inputs):
                            result=await session.call_tool("module_check",{"tool":tool,"inputs":inputs})
                            self.assertFalse(result.isError,result)
                            structured=result.structuredContent
                            if structured is None:
                                structured=json.loads(next(x.text for x in result.content if x.type=="text"))
                            self.assertEqual(structured["engineering_acceptance"],"not_assessed")
                            return structured

                        manifest_result=await request("dynamics.verify_package_manifest",dict(root=str(root),manifest_path=str(manifest)))
                        self.assertTrue(manifest_result["result"]["matches"])
                        self.assertTrue((await request("dynamics.check_csv_grid",grid))["result"]["matches"])
                        parsed=await request("dynamics.inspect_history",dict(history_path=str(history)))
                        self.assertEqual(parsed["result"]["status"],"ok")
                        self.assertFalse(parsed["result"]["strict_simulation_passed"])
                        self.assertTrue(parsed["result"]["owner_identity_verified"])
                        await request("dynamics.list_external_tools",dict(settings_path=str(settings)))
                        plan=await request("dynamics.plan_external_invocation",dict(tool_id=chosen["id"],settings_path=str(settings)))
                        self.assertFalse(plan["result"]["execution_performed"])
                        self.assertFalse(plan["result"]["external_process_started"])
                        examples=SKILLS/"aspen-edr-rating-delivery/examples/offline_checks"
                        for tool,file in (("screen_pipe_candidates","pipe"),("check_exchanger_basis","exchanger"),
                                          ("check_packed_beds","packed"),("audit_edr_geometry","geometry")):
                            inputs=json.loads((examples/f"{file}.json").read_text(encoding="utf-8"))
                            answer=await request("edr."+tool,inputs)
                            self.assertEqual(answer["result"]["diagnostic_status"],"pass")
                        for bad in (True,"1",5e-324):
                            answer=await request("dynamics.check_csv_grid",{**grid,"interval":bad})
                            self.assertEqual(answer["result"]["status"],"invalid_or_unavailable")
                        # Read-only success/failure calls preserve the explicit input files.
                        self.assertEqual((root/"payload.txt").read_bytes(),data)
                        self.assertEqual(entry.read_text(encoding="utf-8"),"raise RuntimeError('must never be executed')\n")
        asyncio.run(run())


if __name__=="__main__":
    unittest.main()
