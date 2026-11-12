> Relocated method reference under aspen-plus-operations. Original candidate/discovery statements below are historical source context, not installation or independent skill metadata. Current owner rules take precedence.


# Aspen Dynamics offline facade

Read [README.md](README.md), [RULES.md](RULES.md) and
[DEPENDENCIES.md](DEPENDENCIES.md). `toolpack.py` is the only checking implementation;
`offline_facade.py` supplies typed structured results and `mcp_server.py` registers
those same functions with FastMCP. No new physics, evidence parser or native
Dynamics control interface is implemented here.

Use `manifest`, `grid` and `history` for the stated offline scopes. History prefers
the public sibling parser, checks its identity before importing it, and reports
resolved path/raw hash/LF-normalized hash. An explicit installed-owner fallback
requires an independently approved raw-byte expected hash. Missing evidence stays
unknown; synthetic tests are not native software validation or inbox admission.

Use `catalog` and `plan` only to locate external tools or print argv/cwd. Their
five original services are external dependencies, not implementations shipped
here. Do not run a plan or register a client without the active task's authority.
Importing the MCP entry does not start it; explicit main execution starts only
this module's stdio facade.

For native export, initialization, control, disturbances, product checks or exact
file delivery, enter the current authorized operations owner and version-specific
workflow. Do not inherit project parameters, warning waivers, solver tolerances
or control settings from examples. No case material is included in this module.
