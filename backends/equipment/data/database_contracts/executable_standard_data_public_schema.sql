-- Public structural contract only. Runtime rows remain outside ordinary Git
-- history; their exact database and build manifest hashes are declared in
-- data/database_authority_registry.json.

CREATE TABLE datasets (
  dataset_id TEXT PRIMARY KEY,
  equipment_family TEXT,
  subject TEXT,
  standard_id TEXT,
  standard_version TEXT,
  source_id TEXT,
  source_sha256 TEXT,
  authority_state TEXT,
  lifecycle_state TEXT,
  reuse_class TEXT,
  qa_status TEXT,
  record_count INTEGER,
  source_csv_sha256 TEXT,
  audit_path TEXT,
  audit_sha256 TEXT,
  build_id TEXT
);

CREATE TABLE standard_records (
  dataset_id TEXT,
  record_id TEXT,
  equipment_family TEXT,
  subject TEXT,
  source_record_type TEXT,
  standard_id TEXT,
  standard_version TEXT,
  authority_state TEXT,
  lifecycle_state TEXT,
  source_id TEXT,
  source_sha256 TEXT,
  physical_page TEXT,
  source_section TEXT,
  source_table TEXT,
  source_row_label TEXT,
  source_column_label TEXT,
  source_bbox_pt TEXT,
  raw_value TEXT,
  normalized_value TEXT,
  normalized_number REAL,
  normalized_attributes_json TEXT,
  unit TEXT,
  applicability TEXT,
  source_record_qa_status TEXT,
  source_terminal_class TEXT,
  source_payload_json TEXT,
  reuse_class TEXT,
  qa_status TEXT,
  audit_path TEXT,
  build_id TEXT,
  record_sha256 TEXT,
  PRIMARY KEY (dataset_id, record_id)
);

CREATE TABLE figure_datasets (
  dataset_id TEXT PRIMARY KEY,
  equipment_family TEXT,
  subject TEXT,
  representation_type TEXT,
  standard_id TEXT,
  standard_version TEXT,
  source_id TEXT,
  source_sha256 TEXT,
  authority_state TEXT,
  lifecycle_state TEXT,
  reuse_class TEXT,
  qa_status TEXT,
  record_count INTEGER,
  source_csv_sha256 TEXT,
  audit_path TEXT,
  audit_sha256 TEXT,
  vision_disabled_replay_status TEXT,
  build_id TEXT
);

CREATE TABLE figure_records (
  dataset_id TEXT,
  figure_record_id TEXT,
  figure_id TEXT,
  equipment_family TEXT,
  subject TEXT,
  representation_type TEXT,
  record_kind TEXT,
  entity_id TEXT,
  parent_entity_id TEXT,
  standard_id TEXT,
  standard_version TEXT,
  authority_state TEXT,
  lifecycle_state TEXT,
  source_id TEXT,
  source_sha256 TEXT,
  physical_page TEXT,
  source_figure TEXT,
  raw_label TEXT,
  normalized_value TEXT,
  normalized_number REAL,
  unit TEXT,
  payload_json TEXT,
  applicability TEXT,
  error_bound TEXT,
  relation_from_entity_id TEXT,
  relation_to_entity_id TEXT,
  direction TEXT,
  condition_text TEXT,
  reuse_class TEXT,
  qa_status TEXT,
  audit_path TEXT,
  build_id TEXT,
  record_sha256 TEXT,
  PRIMARY KEY (dataset_id, figure_record_id)
);

CREATE INDEX idx_standard_records_family
  ON standard_records(equipment_family, subject, source_record_type);

CREATE INDEX idx_figure_records_family
  ON figure_records(equipment_family, subject, representation_type, record_kind);

CREATE INDEX idx_figure_records_figure
  ON figure_records(figure_id, record_kind);
