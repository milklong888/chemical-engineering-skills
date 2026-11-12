# Public tool-maintenance scope

This module ships independent catalog/planning and offline file diagnostics,
plus a real optional FastMCP server facade over those same functions. It does not
ship native Dynamics automation or the five external services listed in the
catalog. Public history parsing reuses the canonical parent operations aspen_evidence.py
owner; a hash-bound explicit installed-owner fallback is available.

All shipped paths except this generated manifest's own identity are enumerated
in PUBLIC_MANIFEST.json. Source metadata, dependency declarations, scope rules,
synthetic example and tests are included. No private local settings, archived
source snapshots, models, logs, case tools, review conversations, parameters,
controller settings, acceptance exceptions or licensed manual pages are included.

The code reads selected local files, performs existing checks or prints plans.
Only explicit execution of mcp_server.py starts this module's stdio facade;
no external server/COM/browser/client registration is started or changed.
Synthetic offline tests, MCP transport tests and native engineering acceptance
have separate scopes. Neither examples nor packaging constitute experience
inbox admission or an engineering-success claim.

Original code is MIT. Original documentation is CC BY 4.0. Optional SDK and public
parser licenses remain separate; see DEPENDENCIES.md. No third-party license or
permission is inferred from a private source snapshot.
