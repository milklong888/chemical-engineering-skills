from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import aspen_com_import as aspen  # noqa: E402


def child_values(node: Any) -> list[Any]:
    return [aspen.node_value(child) for child in aspen.node_elements(node)]


def set_value(tree: Any, path: str, value: Any) -> None:
    node = aspen.find_node(tree, path)
    if node is None:
        raise RuntimeError(f"missing COM node after record creation: {path}")
    node.Value = value


def append_list_value(node: Any, value: Any) -> Any:
    elements = node.Elements
    location = int(elements.RowCount(0))
    elements.InsertRow(0, location)
    row = elements.Item(location)
    row.Value = value
    return row


def append_named_row(node: Any, name: str) -> Any:
    elements = node.Elements
    location = int(elements.RowCount(0))
    elements.InsertRow(0, location)
    elements.SetItemName(location, 0, False, name)
    return elements.Item(name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Isolated proof that Aspen transport reporting can be added directly through COM."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--property-set-name", default="EDGMU001")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise SystemExit(f"source does not exist: {source}")
    prop_set_name = str(args.property_set_name).strip().upper()
    if not prop_set_name or not prop_set_name.replace("_", "").isalnum():
        raise SystemExit("invalid property-set name")

    import pythoncom

    app = None
    previous_cwd = Path.cwd()
    work = Path(tempfile.mkdtemp(prefix="EquipmentDesignAspenMutationProof_"))
    staged = work / f"SOURCE{source.suffix.lower()}"
    shutil.copy2(source, staged)
    aspen.stage_aspen_sidecars(source, staged)
    source_sha_before = aspen.sha256(source)
    lock = aspen.WORKSPACE_ROOT / "_aspen_com_global.lock"
    aspen.WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema": "aspen-com-direct-transport-mutation-proof-v1",
        "source_path": str(source),
        "source_sha256_before": source_sha_before,
        "original_source_read_only": True,
        "source_bkp_mutated": False,
        "property_set_name": prop_set_name,
        "operations": [],
    }
    try:
        with aspen.AspenLock(lock):
            pythoncom.CoInitialize()
            os.chdir(work)
            app, progid = aspen.create_aspen()
            open_method, open_errors = aspen.open_case(app, staged)
            manifest.update({
                "progid": progid,
                "open_method": open_method,
                "open_errors": open_errors,
            })

            prop_sets = aspen.find_node(app.Tree, r"\Data\Properties\Prop-Sets")
            if prop_sets is None:
                raise RuntimeError("BLOCKED_COM_PROP_SETS_NODE_NOT_FOUND")
            if aspen.find_node(
                app.Tree,
                rf"\Data\Properties\Prop-Sets\{prop_set_name}",
            ) is not None:
                raise RuntimeError("BLOCKED_TEST_PROPERTY_SET_ALREADY_EXISTS")
            created = prop_sets.Elements.Add(prop_set_name)
            manifest["operations"].append({
                "operation": "Prop-Sets.Elements.Add",
                "argument": prop_set_name,
                "returned_name": aspen.node_name(created),
            })

            base = rf"\Data\Properties\Prop-Sets\{prop_set_name}\Input"
            for field, value in (
                ("DESCRIPTION", "Dynamic viscosity requested by EquipmentDesignApp"),
                ("SUBSTREAM", "MIXED"),
                ("SYSPRES", "YES"),
                ("SYSTEMP", "YES"),
            ):
                set_value(app.Tree, base + "\\" + field, value)
                manifest["operations"].append({
                    "operation": "set_value",
                    "path": base + "\\" + field,
                    "value": value,
                })

            phase = aspen.find_node(app.Tree, base + r"\PHASE")
            if phase is None:
                raise RuntimeError("BLOCKED_COM_PHASE_NODE_NOT_FOUND")
            for value in ("V", "L"):
                row = append_list_value(phase, value)
                row.Value = value
                manifest["operations"].append({
                    "operation": "PHASE.Elements.Add",
                    "value": value,
                    "returned_name": aspen.node_name(row),
                })

            units = aspen.find_node(app.Tree, base + r"\UNITS")
            if units is None:
                raise RuntimeError("BLOCKED_COM_UNITS_NODE_NOT_FOUND")
            property_node = append_named_row(units, "MUMX")
            manifest["operations"].append({
                "operation": "UNITS.Elements.Add",
                "argument": "MUMX",
                "returned_name": aspen.node_name(property_node),
            })

            report_properties = aspen.find_node(
                app.Tree,
                r"\Data\Setup\Main\Input\PROPERTIES",
            )
            if report_properties is None:
                raise RuntimeError("BLOCKED_COM_REPORT_PROPERTIES_NODE_NOT_FOUND")
            report_row = append_list_value(report_properties, prop_set_name)
            manifest["operations"].append({
                "operation": "Setup.Main.PROPERTIES.Elements.Add",
                "value": prop_set_name,
                "returned_name": aspen.node_name(report_row),
            })

            manifest["after_tree"] = {
                "property_set_exists": aspen.find_node(
                    app.Tree,
                    rf"\Data\Properties\Prop-Sets\{prop_set_name}",
                ) is not None,
                "phase_values": child_values(phase),
                "property_names": [
                    aspen.node_name(child)
                    for child in aspen.node_elements(units)
                ],
                "report_property_sets": child_values(report_properties),
            }
            exported = out_dir / "direct_com_transport_proof.inp"
            app.Export(4, str(exported))
            manifest["export"] = {
                "path": exported.name,
                "sha256": aspen.sha256(exported),
            }
    finally:
        aspen.close_aspen(app)
        os.chdir(previous_cwd)
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        shutil.rmtree(work, ignore_errors=True)

    source_sha_after = aspen.sha256(source)
    manifest["source_sha256_after"] = source_sha_after
    manifest["source_bkp_mutated"] = source_sha_after != source_sha_before
    if manifest["source_bkp_mutated"]:
        raise RuntimeError("BLOCKED_ORIGINAL_SOURCE_HASH_CHANGED")
    manifest["status"] = "PASS"
    output = out_dir / "direct_com_transport_proof_manifest.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": manifest["status"],
        "manifest": str(output),
        "after_tree": manifest["after_tree"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
