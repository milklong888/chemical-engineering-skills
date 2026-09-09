# Original equipment backend, 2.4.0 migration

This is the existing deterministic equipment implementation, not a simplified
replacement matcher. It retains the 17-family parameter/units/formula chain,
registered type and connection selection, Agent protocol 1.9, pure-JSON Aspen
derivation/PFD/replay, report data projection, and the optional isolated Aspen
COM worker. GUI code/executables are not distributed.

## Agent invocation

Run `python -B -X utf8 app/equipment_design_agent.py` from this directory and
send one `equipment-design-agent-request-v1` JSON object on stdin. The response
is `equipment-design-agent-response-v1`. File arguments `--request`/`--output`
and a resident `--session-jsonl` session are also supported.

```json
{"schema":"equipment-design-agent-request-v1","request_id":"OFFLINE_CHECK","operation":"selftest","payload":{}}
```

```json
{"schema":"equipment-design-agent-request-v1","request_id":"STANDARD_QUERY","operation":"knowledge_search","payload":{"query":"GB/T 17395","limit":4,"package_ids":["design_standards"]}}
```

Discover exact fields through `capabilities`, `catalog` and `schema_get`.
`manual_match`, `manual_batch`, `auto_match`, `aspen_derive` and data PFD operations
do not need Aspen or a network. The COM implementation is retained but does not
launch by default: `--allow-com` explicitly permits this optional branch for
the current process, and installed Aspen/pywin32 are still required. The direct
Python API equivalent is explicit `EQUIPMENT_BACKEND_ALLOW_COM=1`. Missing or
unauthorized COM does not erase manual/JSON capabilities. Remote LLM assistance
remains optional and is not used by the offline tests.

Python API: add this backend's `app` and `scripts` directories to the module
path, then use `equipment_design_agent.execute_request(request)` for the full
governed protocol. The lower-level read-only data APIs are
`projected_standard_store.search_facts(backend_root, query, limit)` and
`projected_standard_store.load_pipe_store(backend_root)`.

## Actual bundled data

`data/standard_facts.sqlite.gz` contains 24,887 structured standard records,
1,844 figure records, 24 table-dataset declarations and 14 figure-dataset
declarations. It is verified before in-memory SQLite deserialization; no raw
database is extracted into a source-machine workspace. Python SQLite must
support `deserialize` (the tested runtime does). Both compressed and original
projection hashes are in `data/standard_facts_manifest.json`.

The projection retains original source/record IDs and hashes, standard version,
page/table/row/column, quantities/units, conditions, relationships, and original
QA/reuse/lifecycle states. Long original paragraphs and private paths are
excluded with field-level hashes/reasons. Projection hashes are new identities,
not substitutes for the parent database hash. Original `VERIFIED` describes
source QA, not a new claim of general engineering acceptance.

Only the original pipe consumer's qualified datasets feed pipe calculations:
12 PN records and 5,620 dimension/weight records. Every actual output field
except the deliberately replaced raw source-payload JSON is checked against
the original store. All other facts/figures are retrieval context and still
require an applicable calculation consumer and same-duty evidence.

The original small pump/DN catalogs, family/model/parameter rules and HG/T
computational CSVs are preserved. HG/T source paragraphs are replaced only by
source locators/hashes under an explicit new package manifest. Run its
`validate_package.py --runtime-only --json` for computational validation; this
returns `PASS_RUNTIME_ONLY`, never paragraph or formal-design acceptance.
Full source validation additionally needs the user's exact original
`--source-text-csv`, whose hash is checked. The builder retains its original
algorithm and accepts an explicit user `--source-root` and new `--output-root`.

## Valuable legacy audit scripts remain

`scripts/equipment_calc.py` retains every original function, including general
parsing/audit/report logic. Generic formulas work directly. Legacy project
values, report text and fixed case-table IDs have been externalized, not replaced
with new values. To run that case audit, supply `--case-profile`, its exact
`--case-profile-sha256`, `--source-root`, and a disjoint `--output-root`.
Private original profiles are not distributed. Missing profiles/tables are
dependencies, not zero values or successful audits; no output is created when
the required profile is absent.

## Verification boundary

The original 22-file source identity is retained in `origin/`; this backend has
its own source manifest. The original source verifier and authority-revision
checks remain active. A required runtime manifest binds the actual data/rules/
schemas and rejects missing, extra or changed assets. Do not disable verification
after editing code or replace projected data with an old DB under its filename.

Portable tests: `python -B -X utf8 ../../tests/test_equipment_backend.py` from
this backend directory (or invoke the repository test path directly). Synthetic
test success is not a real process, EDR, SW6 or vendor acceptance result.
