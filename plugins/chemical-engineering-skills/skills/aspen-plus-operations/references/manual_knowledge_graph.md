# User-Provided Aspen Help Access

This public package does **not** include the commercial Aspen manual body,
the source machine's help-derived node set, or historical tested cases.
`manual_knowledge_graph.json` deliberately has an empty `nodes` list and
`content_status=LOCAL_USER_HELP_REQUIRED`; it is a dependency contract,
not a populated manual or an implemented substitute.

Use the bundled read-only `scripts/search_aspen_help.py` only after locating
the user's legally installed, version-specific help root. A configured local
graph may be queried with `scripts/query_manual_knowledge.py`; until the user
supplies qualified nodes, that query correctly returns no match/nonzero status.
Do not call an empty graph a successful knowledge lookup.

Before using fragile reaction, property, geometry, phase, unit, control or
file-I/O cards, record the current help version, source path/hash and page or
field location. Bind any card conversion to the current project ledger and
same-version exported evidence. A missing licensed/local source is an explicit
dependency; never pad values from a historical case or a search hit.

User-supplied V10/textbook graphs are optional local assets under the configured
`{CHEM_WORKSPACE}`. No chapter text, figure, full-text index or vector payload
is part of this release. Basic software field identifiers and search terms may
guide discovery but do not supply project kinetics, phase assumptions or
acceptance evidence.

