> Main-library relocation: plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/dynamics_tools. Source and transformations: [RELOCATION.json](RELOCATION.json). Historical source/admission statements below retain their original scope; current parent skill owns routing and acceptance.

# Aspen Dynamics offline tool facade 1.1.0

This module contains working offline CLI/Python tools and an **actual optional
FastMCP stdio server** around the same functions. It does not contain a native
Dynamics interface. The original catalog's five services remain separately
installed external dependencies; catalog/plan never starts them.

Python 3.10+ is required. Offline diagnostics use only the standard library.
Keep the repository's public `../aspen_evidence.py` owner beside this directory
for the default history bridge. See [dependencies and license sources](DEPENDENCIES.md)
and [rules and limits](RULES.md).

## Offline CLI and Python

Run from this directory, or use the script's absolute path:

```powershell
python -B -X utf8 toolpack.py catalog
python -B -X utf8 toolpack.py plan chemical-expert-cli --settings local_settings.json
python -B -X utf8 toolpack.py manifest <root> <manifest.json>
python -B -X utf8 toolpack.py grid <export.csv> --time-column <column> --interval <step> --start <start> --end <end> --time-abs-tol <explicit-time-tolerance>
python -B -X utf8 toolpack.py history <captured.his>
```

`--numeric-column` may be repeated for grid checks. Time units and diagnostic
tolerance must be supplied for the selected CSV; nothing writes solver settings.
History defaults to the pinned existing public parser. If that sibling is missing,
use an explicitly approved installed owner with BOTH
`--operations-root <owner-root>` and `--expected-owner-sha256 <raw-byte-sha256>`.
`--verified-encoding` is only for independently verified fallback encodings.
The resolved parser path, actual raw SHA256 and LF-normalized SHA256 are returned.

The Python facade is `offline_facade.py`; its five functions are also the MCP tools:

| Export | Required inputs | Implemented scope |
|---|---|---|
| verify_package_manifest | root, manifest_path | Listed bytes only; no complete dependency inventory |
| check_csv_grid | csv_path, time_column, interval, start, end, time_abs_tolerance; optional numeric_columns | Explicit supplied CSV grid only |
| inspect_history | history_path; optional operations_root, verified_encoding, expected_owner_sha256 | Existing public parser; offline text only |
| list_external_tools | optional settings_path | External source/path presence only |
| plan_external_invocation | tool_id; optional settings_path | argv/cwd only; never executes the planned tool |

Facade invalid inputs return `status=invalid_or_unavailable`. `status=ok` means a
structured result, not necessarily `matches=true`. All facade results retain
`strict_simulation_passed=false`, `engineering_acceptance=not_assessed`, and
`native_calculation_acceptance=not_assessed`. CLI exit 0 means its declared check
matched or a plan was produced; exit 2 means mismatch, invalid input or unavailable
dependency. Neither is engineering acceptance.

## Optional MCP server

Install the optional pinned SDK into the environment you explicitly select:

```powershell
python -m pip install -r requirements-mcp.txt
python -B -X utf8 mcp_server.py
```

The second command starts **only this offline facade** on stdio. It is intended
for a trusted local MCP client; it is not an interactive terminal command.
`create_server()` constructs the real FastMCP server without starting transport.
Importing `mcp_server` does not start it. The server registers exactly the five
functions listed above; all delegate to `toolpack.py`. The MCP grid adapter
requires strict JSON numbers for interval/start/end/time_abs_tolerance: integers
and floats are accepted, booleans/strings/containers are rejected before coercion.
An arithmetic overflow in a supplied grid request returns the existing structured
invalid-input receipt in both CLI and facade; no grid threshold is changed. No client configuration
or server registration is changed automatically. The external Plus/expert MCP
servers are neither bundled nor launched. A transport test is a separate scope
from offline function tests; consult the actual validation receipt.

## Synthetic runnable examples and tests

```powershell
python -B -X utf8 examples/demo_offline.py
python -B -X utf8 -m unittest discover -s tests -v
```

The example creates and removes its own synthetic files. Its external entry and
Python file are deliberate non-executable fixtures: the plan is printed and never
run. It exercises all five facade calls; the history fixture is synthetic text,
not a real `.his` from Aspen. Each exported tool has success and invalid-input
regressions. The real cross-module history tests load the public parser and check
warning/incomplete-table rejection and import-before-hash protection.

Copy `local_settings.example.json` only when external tool paths are needed.
Fill `paths` and `interpreters` by catalog id. Do not publish your filled local
settings. Path existence does not prove imports, service health or native capability.

## Provenance and packaging

Ten original public files were restored individually from public branch commit
`21c33df8da1a44169770e6a69c7afe08bcfae6c6`; only this directory was extended.
No private archive source, case audit, model, log, controller setting or licensed
manual was imported. Public source identity, validation scope and remaining
external dependencies are recorded in `SOURCE_METADATA.json`, `PACKAGE_STATUS.json`
and `PUBLIC_MANIFEST.json`. The manifest covers every other shipped module file;
it records file identity, not native success. Retain the sibling public parser or
use the explicit identity-bound fallback; this directory alone does not include it.

Code is MIT; original documentation is CC BY 4.0. Optional SDK and public parser
keep their own licenses. Aspen software, licenses and third-party backends are
not distributed or relicensed by this module.
