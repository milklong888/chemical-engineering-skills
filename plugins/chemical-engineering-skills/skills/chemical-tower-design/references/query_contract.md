# Scripted query contract

This skill wrapper is a tower-specific caller of the top-level `设备设计图谱与脚本`. Its backend is the `standards_graph` evidence sublayer; the wrapper does not make the skill the parent of that graph.

Use the wrapper from the skill directory:

```powershell
python scripts/query_tower_sources.py "降液管 面积" --scope all --limit 10
```

Useful filters:

```powershell
python scripts/query_tower_sources.py "塔式容器" --doc-id std_nb_t_47041_2014 --page 31
python scripts/query_tower_sources.py "受液盘" --scope chunks --evidence S1 --format jsonl
python scripts/query_tower_sources.py "开孔率" --scope tables --format csv
```

The wrapper locates the active workspace and calls the standards source-layer query engine. It defaults to the `tower` family but allows `--family` to be supplied for cross-family material, flange, foundation, vessel, or exchanger evidence.

Each hit must expose:

- `doc_id`, family, source kind, and evidence class;
- `package_state`, remaining manual-review-page count, and `extraction_status`;
- `reuse_boundary`, explicitly distinguishing source evidence, method/routing-only material, review-required material, and forbidden automatic numeric/quotation reuse;
- source PDF absolute path and SHA-256;
- physical PDF page and bounding box for text/asset hits;
- `location_status`; legacy text recovery may be `page_level_only_no_glyph_bbox`, which allows routing/search but forbids automatic quotation or numeric reuse until the original page is visually checked;
- extraction method and quality indicator;
- table CSV or figure image path when applicable;
- a short excerpt, not an untraceable paraphrase.

Supported output formats are `text`, `json`, `jsonl`, and `csv`. Prefer `jsonl` for agent pipelines and `csv` for batch review. A zero-result query is not permission to invent a value: broaden synonyms, remove family filters, query the equipment graph, or record the item as unresolved.
