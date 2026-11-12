"""Synthetic demonstration of all five facade tools; no services are started."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dynamics_tools.offline_facade import (verify_package_manifest, check_csv_grid, inspect_history,
                            list_external_tools, plan_external_invocation)


def main():
    with tempfile.TemporaryDirectory(prefix="synthetic-offline-facade-") as directory:
        root = Path(directory)
        csv = root / "synthetic.csv"
        csv.write_text("t,x\n0,1\n2,2\n4,3\n", encoding="utf-8")
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({"files": [{"path": csv.name,
            "size": csv.stat().st_size, "sha256": hashlib.sha256(csv.read_bytes()).hexdigest()}]}), encoding="utf-8")
        history = root / "synthetic.his"
        history.write_text("\n".join(["Summary of Simulation Errors", "Physical",
            "Property System Simulation", "Terminal Errors 0 0 0", "Severe Errors 0 0 0",
            "Errors 0 0 0", "Warnings 0 0 0", "NO ERRORS OR WARNINGS GENERATED", ""]), encoding="utf-8")
        external = root / "synthetic-external"
        (external / "tools").mkdir(parents=True)
        (external / "tools/expert_mcp.py").write_text("# synthetic fixture: never executed\n", encoding="utf-8")
        python = root / "synthetic-python.exe"
        python.write_bytes(b"Not an executable; this is a plan-only fixture")
        settings = root / "synthetic-settings.json"
        settings.write_text(json.dumps({"paths": {"chemical-expert-mcp": str(external)},
            "interpreters": {"chemical-expert-mcp": str(python)}}), encoding="utf-8")
        results = {
            "synthetic_only": True,
            "manifest": verify_package_manifest(str(root), str(manifest)),
            "grid": check_csv_grid(str(csv), "t", 2, 0, 4, 0, ["x"]),
            "history": inspect_history(str(history)),
            "catalog": list_external_tools(str(settings)),
            "plan": plan_external_invocation("chemical-expert-mcp", str(settings)),
        }
        print(json.dumps(results, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
