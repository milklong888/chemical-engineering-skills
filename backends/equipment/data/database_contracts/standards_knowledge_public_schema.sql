-- Public structural contract only. The copyrighted/source-derived row payloads
-- are not stored in Git. The runtime SQLite is hash-bound in
-- data/database_authority_registry.json and distributed inside release assets.

CREATE TABLE documents (
  doc_id TEXT PRIMARY KEY,
  canonical_doc_id TEXT,
  relative_path TEXT,
  source_pdf_path TEXT,
  source_pdf_sha256 TEXT,
  family TEXT,
  source_kind TEXT,
  evidence_default TEXT,
  duplicate_of TEXT,
  language TEXT,
  priority TEXT,
  page_count INTEGER,
  chunk_count INTEGER,
  table_count INTEGER,
  figure_count INTEGER,
  manual_review_page_count INTEGER,
  package_status TEXT,
  package_path TEXT
);

CREATE TABLE chunks (
  chunk_id TEXT PRIMARY KEY,
  doc_id TEXT,
  chunk_order INTEGER,
  relative_path TEXT,
  source_pdf_path TEXT,
  source_pdf_sha256 TEXT,
  family TEXT,
  source_kind TEXT,
  evidence_default TEXT,
  page_start INTEGER,
  page_end INTEGER,
  section_path TEXT,
  extraction_methods TEXT,
  quality_score REAL,
  char_count INTEGER,
  text_sha256 TEXT,
  block_refs_json TEXT,
  location_status TEXT,
  text TEXT
);

CREATE TABLE tables_data (
  table_id TEXT PRIMARY KEY,
  doc_id TEXT,
  page_id TEXT,
  page_1based INTEGER,
  table_order INTEGER,
  method TEXT,
  structure_confidence REAL,
  bbox_json TEXT,
  caption TEXT,
  row_count INTEGER,
  column_count INTEGER,
  nonempty_cells INTEGER,
  key_table INTEGER,
  csv_path TEXT,
  csv_absolute_path TEXT,
  source_pdf_path TEXT,
  source_pdf_sha256 TEXT,
  cell_text TEXT,
  structure_mode TEXT,
  numeric_reuse_allowed INTEGER,
  geometry_preserved INTEGER,
  common_spec_cells INTEGER,
  cell_audit_absolute_path TEXT,
  asset_label TEXT,
  asset_qa_status TEXT,
  structure_override INTEGER
);

CREATE TABLE figures_data (
  figure_id TEXT PRIMARY KEY,
  doc_id TEXT,
  page_id TEXT,
  page_1based INTEGER,
  figure_order INTEGER,
  method TEXT,
  bbox_json TEXT,
  caption TEXT,
  key_figure INTEGER,
  image_path TEXT,
  image_absolute_path TEXT,
  source_pdf_path TEXT,
  source_pdf_sha256 TEXT
);

CREATE TABLE formulas_data (
  formula_id TEXT PRIMARY KEY,
  doc_id TEXT,
  page_id TEXT,
  page_1based INTEGER,
  formula_order INTEGER,
  label TEXT,
  caption TEXT,
  bbox_json TEXT,
  raw_text TEXT,
  method TEXT,
  qa_status TEXT,
  image_path TEXT,
  image_absolute_path TEXT,
  source_pdf_path TEXT,
  source_pdf_sha256 TEXT
);

-- The production database additionally contains FTS5 and trigram virtual
-- tables with SQLite-managed shadow tables. They index chunks, table cell
-- text, figure captions and formula text; they do not constitute a second
-- authority data source.
