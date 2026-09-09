# Official Codex Plugin Migration

## Sources checked

- Current Codex manual, fetched 2026-07-17 through the official manual helper:
  plugin build, structure, marketplace, skills, MCP, and app sections.
- OpenAI's public plugin examples: <https://github.com/openai/plugins>.
- OpenAI's role-specific plugin templates:
  <https://github.com/openai/role-specific-plugins>.
- The bundled OpenAI `plugin-creator` scaffold and validator shipped with this
  Codex environment.

## Architecture decision

The canonical expert workflow remains one skill under
`skill_packages/chemical-engineering-expert`. Its installable distribution is:

```text
plugins/chemical-engineering-expert/
├── .codex-plugin/plugin.json
├── skills/chemical-engineering-expert/
├── scripts/sync_from_workspace_skill.py
├── scripts/retrieval_bridge.py
├── plugin.lock.json
└── README.md
```

This mirrors OpenAI's official role-plugin pattern: manifest at
`.codex-plugin/plugin.json`, workflows under `skills/`, optional root scripts,
and connectors/MCP only when they really exist.

## Boundary

- The plugin skill is a generated, SHA256-locked mirror; it is not a second
  editable authority.
- Large knowledge graphs and project artifacts remain in the workspace. The
  plugin uses the asset registry and read-only retrieval bridge rather than
  freezing another stale snapshot.
- `.app.json` is omitted because no connector is required for local files.
- `.mcp.json` is omitted in v0.2.0 because no validated MCP server/runtime is
  bundled. A placeholder MCP declaration would create a false capability.
- Plugin-local hooks are not used in this release. The current bundled
  validator/runtime support is narrower than some documentation examples; hard
  release gates stay in deterministic validation scripts and `AGENTS.md`.

## Reliable build method

1. Edit only the canonical skill and workspace retrieval scripts.
2. Run `sync_from_workspace_skill.py`; refuse unowned plugin-skill files.
3. Compare the complete relative-path/SHA256 manifest and write
   `plugin.lock.json`.
4. Run skill quick validation and official plugin validation.
5. Rebuild the workspace index and pass all positive and negative retrieval
   regressions.
6. Run behavioral forward tests for method lock, derivation-before-missing,
   feasible-vs-good classification, flowsheet ordering, recycle/terminal
   closure, high-grade-utility preheat/MVR boundaries, semantic disambiguation,
   and scope isolation.
7. Only then add a marketplace entry/install and test in a fresh task.

## Retrieval method

Use the pipeline in `VECTOR_KNOWLEDGE_BASE_DESIGN.md`: hard scope filter first,
then lexical and future dense recall, rank fusion, graph expansion, authority
rerank, and exact source verification. Expose retrieval through an MCP tool
only after the backend, schemas, annotations, read-only behavior, and evals are
stable. Until then, the plugin's subprocess bridge is simpler and auditable.
