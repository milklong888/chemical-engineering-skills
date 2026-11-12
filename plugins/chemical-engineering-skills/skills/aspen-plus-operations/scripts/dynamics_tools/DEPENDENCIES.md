# Dependency and license boundary

The offline code requires Python 3.10+ and its standard library. It does not
need Aspen, pywin32, numpy, or an MCP SDK for in-process file diagnostics.

The optional **actual MCP server** is `mcp_server.py`. It uses
`mcp.server.fastmcp.FastMCP` from the MCP Python SDK, declared as
`mcp>=1.28.1,<2` (Python >=3.10, MIT). Install separately using
`requirements-mcp.txt`. The locally inspected clean environment has SDK 1.28.1;
its `add_tool(function, annotations=..., structured_output=True)` and
`run(transport="stdio")` signatures were read directly from that installed SDK.
No separate `fastmcp` distribution is required or imported. The optional adapter
uses `pydantic.Field(strict=True)` from the SDK dependency to preserve JSON-number
input types; the offline core/facade still has no pydantic import or requirement. This is a version
constraint, not a complete transitive lock. SDK distributions and license files
are not vendored here. Optional transport validation is reported separately from
the standard-library offline regression suite.

## Public history parser

`toolpack.history_report` prefers the repository's existing sibling
`../aspen_evidence.py`; that owner carries its own source
metadata, MIT license, notices and tests. Do not copy a second parser here.

Pinned public code identity, after explicitly reported CRLF-to-LF normalization:
`7465d04fc8d1114d65a9f64c94abda32fa885b7a6c8e493aec4b90034e9a3f31`.
The actual raw-byte hash and resolved path are always returned. An optional
expected raw hash is an additional assertion, checked before import. A changed
public parser is rejected until its dependency identity is reviewed. This does
not authenticate external source authors or certify engineering results.

Public source: `milklong888/chemical-engineering-skills`, code commit
`fdd6a1e6d56279e6376dada934a230aea3be85ab`, original path
`plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/aspen_evidence.py`.
The sibling's source metadata records MIT declaration commit
`98a2ea53a127cad7e2fecd0df447a89f5ca014a0`. Those public records govern that
dependency; this module's license does not relicense it.

If the sibling is unavailable, an explicitly supplied `operations_root`
may locate `scripts/aspen_evidence.py`. Fallback requires the caller's independently
approved **raw-byte** `expected_owner_sha256` before importing any owner code.
Fallback must also match the pinned public parser after explicit LF normalization;
a different implementation/version is rejected pending source review. The caller
is responsible for that source's permission and applicability.
No automatic search or unverified installed-owner fallback is performed.

## Catalog entries remain external

The catalog's original five entries are **external dependencies**, not five
servers bundled or validated by this module. `entry_exists` means only file
presence. A printed plan does not prove package installation or service health.

| Entry | Required separate source/runtime | Status in this module |
|---|---|---|
| aspenplus-mcp | Licensed complete Plus MCP; its own package and dependencies | Not bundled; redistribution permission incomplete; not a Dynamics interface |
| chemical-expert-mcp | Complete expert runtime, backends, equipment gateway, knowledge/rules and dedicated Python | Not bundled or tested |
| chemical-expert-cli | The same complete expert runtime | Not bundled or tested |
| operations-evidence | Public sibling parser; explicit identity-bound installed-owner fallback | Only offline text scope is exercised |
| plus-clean-audit | Complete licensed operations owner/runtime and authorized Windows/Aspen environment | Not bundled or run |

No archive snapshot, private model, log, case script, license, controller setting
or licensed manual was copied to complete these dependencies.
