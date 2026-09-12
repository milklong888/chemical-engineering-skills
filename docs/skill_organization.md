# Read-only Skill organization and change review

`tools/skill_organization.py` inventories the product's existing Skill entries and
observed local file references. Its `impact` command returns files and related
Skills to review after named files change. It does not edit Skills, refresh
documentation, import scanned modules, run Aspen, assign factual rule ownership,
or certify a complete dependency graph.

The existing `CANONICAL_RULE_OWNERSHIP.md` remains the factual ownership map.
Directory membership in this report only identifies a related Skill. It does
not give a coordinating Skill authority over referenced specialist rules.

## Commands

Run with the project's supported Python interpreter and disable bytecode writes:

```text
python -B -X utf8 tools/skill_organization.py inventory --root .
python -B -X utf8 tools/skill_organization.py impact --root . --changed tools/design_stage.py
python -B -X utf8 tools/skill_organization.py impact --root . --changed tools/design_stage.py --changed tools/product_contract.py
```

`python` above denotes the configured compatible interpreter, not an instruction
to replace a workspace's dedicated Python. Both commands emit JSON on stdout.
The caller may preserve stdout in its own project audit directory. There is no
output-file option and no source-file writer. Importing this tool from another
program should likewise use `-B`/`PYTHONDONTWRITEBYTECODE` to keep Python's loader
from writing bytecode. The direct CLI disables helper bytecode writes itself.

The root defaults to the directory above `tools`, regardless of current working
directory. This inventory targets a **complete source or release directory**.
After installation, `chemical-engineering-runtime/tools` and the installed
Skills are separate trees: invoking the installed tool therefore requires
`--root <complete-source-or-release-directory>`. The installed runtime alone is
not a valid inventory root; this tool does not discover or merge disjoint
installation roots. Missing product directories or zero `SKILL.md` entries
produce error JSON/exit 2, never a successful zero-Skill inventory.

`--root` can also select an independent development checkout.
No release manifest, signature, Git command, or sealed release is required.
The source must contain entries at the existing
`plugins/chemical-engineering-skills/skills/<skill_id>/SKILL.md` location. Entry
names are checked against directory names. The observed count is reported beside
the product's expected count of 19; a mismatch is visible, not silently repaired.
It does not count unrelated installed/system Skills or invent missing entries.

Changed paths must be portable repository-relative **files**, using `/`. Repeat
`--changed` for several files. A deleted or newly proposed file may be named;
`changed_missing` records absence, and explicit missing references can still
identify its consumers. Existing directories cannot stand in for file changes.

## What an edge means

Each edge points from a source file to a file it references. It records source,
line, reference, type, target, resolution status/reason and possible candidate
targets. Types remain separate:

| Type | Recognized syntax | Interpretation |
|---|---|---|
| `markdown_link` | Simple relative inline links/images | Textual reference, including optional fragments |
| `markdown_reference_definition` | Relative reference-link definitions | Definition exists; its use is not proven |
| `markdown_code_path` | Single-backtick, whitespace-free file paths | Possible textual dependency; can be an illustrative path |
| `python_import` | AST `import` / `from ... import ...` | Local file candidate, not proven runtime import resolution |
| `python_import_member` | A `from ... import name` member without an existing file candidate | Unresolved exported attribute or missing submodule; a present package initializer does not hide it |
| `python_package_init` | Existing package initializers along a local candidate | Possible import initialization dependency |
| `python_path_definition` | Simple module-level file-anchored path assignments | Declared path, which may never be consumed |
| `python_file_reference` | Recognized `Path`, `open`, `read_text`, `read_bytes`, `run_path`, `spec_from_file_location` expressions | Static anchored file, or an explicitly unresolved dynamic/CWD-dependent expression |
| `python_dynamic_import` | `import_module` / `__import__` calls | Unresolved; the module is never loaded to discover its target |

Markdown links are relative to the Markdown source directory. Prose code paths
are checked against that directory and the repository root: a unique existing
file is a static candidate; multiple matches remain ambiguous, and missing
paths retain candidate locations without guessing an anchor. Fragments are
discarded and percent-encoded paths decoded once before boundary checks. Simple
fenced examples are skipped. External URL links are outside this file graph.
This is intentionally not a complete Markdown parser: HTML, nested markup,
complex link destinations and implicit Skill IDs need additional review.

Python imports are checked against the repository root and importing file's
directory; relative imports use their explicit package level. Multiple existing
local locations stay ambiguous. Standard-library imports are outside the local
graph; third-party or missing local imports remain visible as unresolved.
Simple `Path(__file__)`, `.parent`, `.parents[n]`, `/`, `joinpath` and module-level
path aliases can produce a file-anchored reference. Rebound/globally mutable
path names and their dependent aliases stay unresolved, with up to 32 lexical
path combinations retained as candidates. Their presence does not select a
future assignment or determine which branch executed; a candidate limit is
reported explicitly. Function-local shadowing prevents borrowing a global
alias's identity. Literal paths dependent on runtime
CWD, custom path APIs, computed strings, altered `sys.path`, runtime assignments
and generated code are not guessed. Syntactic matches are conservative review
candidates, not proof that `Path` or a call name has its usual runtime meaning.

Only Markdown and Python files are parsed. Referenced JSON, models and other
payloads can be file targets; their content is not loaded or interpreted.
Knowledge meaning, shell commands, COM state, implicit host loading, package
installation mirrors and internal hash-lock consumers are not automatically
recovered by this graph. An empty impact result does not prove no impact.

## Reading the JSON

`inventory` returns `skills`, fingerprinted text `files`, typed `edges`, all
`unresolved_edges`, parse/size/name `issues`, coverage and explicit `blind_spots`.
Directory references have `directory_not_expanded` status; no implicit edge is
added to every descendant. File `sha256` values identify bytes read, not semantic
acceptance. All artifact paths are relative to the supplied root.

`impact` additionally returns:

- `changed` and `changed_missing`;
- `direct_consumers` and transitive `affected_files` from reverse explicit edges;
- one `propagation_witnesses` edge for each newly reached consumer;
- `related_skills`, based on directory membership of changed/reached files;
- unresolved edges in reached files, plus possible consumers whose unresolved
  candidate paths touch the reached set.

Traversal uses a visited set, so valid document/import cycles terminate.
Ambiguous candidates are exposed separately rather than silently propagated as
resolved edges. Global unresolved edges remain present even if their source was
not reached: they may hide additional consumers. Consumers of a registry or
central document can make the textual review set broad; this must not be
reported as observed execution of all those Skills.

## Filesystem and operational boundaries

The tool is read-only. It rejects symlinks, junctions/reparse points, nonregular
entries, unsafe changed paths, root escapes and nonportable file names. Unsafe
source references are recorded without reading their targets. Root and source
paths use the existing release safety helpers; no seal or release verification
is invoked. Actual source reads recheck the path. As with other filesystem
audits, this is not an atomic lock against concurrent replacement: freeze/recheck
file identities before applying a reviewed change.

`.git`, caches, environment/dependency directories and named raw-source trees
are excluded from traversal/parsing. Limits are 20,000 enumerated files, 2 MiB
per parsed file and 64 MiB total parsed text. Oversized/decode/parse failures are
visible; they never count as complete coverage. CLI runtime/path errors produce
error JSON and exit code 2. Argument syntax errors follow argparse conventions.

Verification is in `tests/test_skill_organization.py`: real dependency chains,
cycles, unrelated-module isolation, missing/ambiguous/dynamic references,
package initialization, file-anchored paths, read-only CLI use, input boundaries,
link rejection and the actual 19-entry product inventory. These are software
checks, not Aspen, Skill behavior or engineering-performance evidence.
