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

The canonical Skill source tree is
`plugins/chemical-engineering-skills/skills/`; the expert entrypoint is
`plugins/chemical-engineering-skills/skills/chemical-engineering-expert/`. The
plugin manifest and Skill tree are kept together in the checkout:

```text
plugins/chemical-engineering-skills/
├── .codex-plugin/plugin.json
├── skills/chemical-engineering-expert/
└── skills/<other-skill>/
```

The sealed release is the complete repository tree. Its root release records
are `RELEASE_MANIFEST.json` and `SHA256SUMS.txt`; the repository-root tools are
`tools/build_release.py`, `tools/verify_release.py`, and `tools/install.py`.
The current layout has no separate source mirror or per-plugin lock file;
release-wide identity is recorded only at the repository root.

This keeps the official plugin shape—manifest at `.codex-plugin/plugin.json`
and workflows under `skills/`—without inventing a second source mirror or
connector that is not present.

## Boundary

- The checkout at `plugins/chemical-engineering-skills/skills/` is the editable
  Skill authority. Release-wide SHA256 records are generated at seal time;
  installed Skills are separate copies, not a second source authority.
- The release includes the admitted `knowledge/` and `backends/` payloads with
  their manifests and identity records; `tools/install.py` copies them into
  `<workspace>/chemical-engineering-runtime/`. Original source pages, private
  project artifacts, and optional local extensions remain outside the public
  release and are not conflated with the bundled payload.
- `.app.json` is omitted because no connector is required for local files.
- `.mcp.json` is not present in this plugin tree. The local MCP entrypoint is
  `tools/expert_mcp.py` in the checkout and
  `chemical-engineering-runtime/tools/expert_mcp.py` after installation; do
  not add a placeholder plugin declaration.
- Plugin-local hooks are not used in this release. The current bundled
  validator/runtime support is narrower than some documentation examples; hard
  release gates stay in deterministic validation scripts and `AGENTS.md`.

## Reliable build method

1. Edit the canonical files under `plugins/chemical-engineering-skills/skills/`;
   keep private mapping logs outside the publication repository.
2. When reviewed external sources must be copied into the release, run
   `python -B -X utf8 tools/build_release.py stage --sources <manifest> --repository <repo> --log-dir <private-log-dir>`.
   Staging accepts only the explicit, hash-checked source table and does not
   upload anything.
3. Seal the reviewed repository with
   `python -B -X utf8 tools/build_release.py seal --repository <repo> --output-dir <outside-dir> --release-name <name> --release-version <version>`
   (add `--sources <manifest>` when supplying the reviewed source manifest).
   `seal` writes the root `RELEASE_MANIFEST.json` and `SHA256SUMS.txt`, verifies
   the frozen inventory, and creates the ZIP plus its SHA256 sidecar outside
   the repository; it does not upload.
4. Check a sealed checkout or extracted release with
   `python -B -X utf8 tools/verify_release.py --repository <repo>` (or
   `--root <repo>`). It verifies the manifest, hashes, plugin structure, 19
   Skills, and required release tools.
5. Install only from that verified release using
   `python -B -X utf8 tools/install.py --repository <release-root> --workspace-root <workspace> --skills-root <skills-root> --dry-run`,
   then rerun without `--dry-run` after review. `--replace` and
   `--backup-root` are explicit conflict-handling options. Skills are copied to
   the Skills root, while backends, knowledge, tools, and other runtime assets
   go to `<workspace>/chemical-engineering-runtime/`.
6. Keep the clone/source checkout, installed Skills, and installed runtime as
   separate trees. Cloning or updating the repository does not update an
   installation; do not use the installed runtime alone as a source/release
   root.

## Retrieval method

Use the pipeline in `VECTOR_KNOWLEDGE_BASE_DESIGN.md`: hard scope filter first,
then lexical and future dense recall, rank fusion, graph expansion, authority
rerank, and exact source verification. Expose retrieval through the existing
local `tools/expert_mcp.py` only when the backend, schemas, annotations,
read-only behavior, and evals are stable; otherwise use the same local CLI
entrypoints directly. Retrieval remains separate from release/install state.
