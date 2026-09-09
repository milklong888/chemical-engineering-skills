from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping


FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT).resolve()
    APP_DIR = PACKAGE_ROOT / "app"
else:
    APP_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import app_core  # noqa: E402
import authority_revision  # noqa: E402
import llm_bridge  # noqa: E402
import result_presentation  # noqa: E402
import customer_delivery  # noqa: E402
import aspen_pfd  # noqa: E402
from equipment_design_app import EquipmentDesignApi  # noqa: E402


PROTOCOL_VERSION = authority_revision.AGENT_PROTOCOL_VERSION
REQUEST_SCHEMA = APP_DIR / "schemas" / "equipment_design_agent_request.schema.json"
RESPONSE_SCHEMA = APP_DIR / "schemas" / "equipment_design_agent_response.schema.json"
PRESENTATION_SCHEMA = APP_DIR / "schemas" / "equipment_design_presentation.schema.json"
REPORT_STATUS_SCHEMA = APP_DIR / "schemas" / "equipment_design_report_status.schema.json"
ORGANIZED_ANSWER_SCHEMA = APP_DIR / "schemas" / "equipment_agent_organized_answer.schema.json"
LLM_CONTEXT_SCHEMA = APP_DIR / "schemas" / "equipment_design_llm_context_pack.schema.json"
LLM_STEP_SCHEMA = APP_DIR / "schemas" / "equipment_design_llm_step_output.schema.json"
LLM_PREPARED_SCHEMA = APP_DIR / "schemas" / "equipment_design_llm_prepared.schema.json"
LLM_ORCHESTRATION_SCHEMA = APP_DIR / "schemas" / "equipment_design_llm_orchestration.schema.json"
HYBRID_RESULT_SCHEMA = APP_DIR / "schemas" / "equipment_design_hybrid_result.schema.json"
INTERLEAVED_TIMELINE_SCHEMA = APP_DIR / "schemas" / "equipment_design_interleaved_timeline.schema.json"
AUTHORITY_REVISION_SCHEMA = APP_DIR / "schemas" / "equipment_design_authority_revision.schema.json"
SOURCE_CODE_MANIFEST_SCHEMA = APP_DIR / "schemas" / "equipment_design_source_code_manifest.schema.json"
CUSTOMER_PROFILE_SCHEMA = APP_DIR / "schemas" / "equipment_customer_output_profiles.schema.json"
CUSTOMER_DELIVERY_BUNDLE_SCHEMA = APP_DIR / "schemas" / "equipment_customer_delivery_bundle.schema.json"
EQUIPMENT_OVERVIEW_SCHEMA = APP_DIR / "schemas" / "equipment_overview_table.schema.json"
EQUIPMENT_FAMILY_DATASHEET_SCHEMA = APP_DIR / "schemas" / "equipment_family_datasheet.schema.json"
EQUIPMENT_EVIDENCE_INDEX_SCHEMA = APP_DIR / "schemas" / "equipment_evidence_index.schema.json"
PFD_MAPPING_SCHEMA = APP_DIR / "schemas" / "equipment_design_pfd_mapping.schema.json"
FORMULA_TRACE_SCHEMA = APP_DIR / "schemas" / "equipment_formula_trace.schema.json"
PARAMETER_PACKAGE_SCHEMA = PACKAGE_ROOT / "knowledge_graph" / "equipment_design_parameter_package.schema.json"
CONNECTION_SELECTION_SCHEMA = PACKAGE_ROOT / "knowledge_graph" / "equipment_connection_selection_package.schema.json"
SERVICE_PROFILE_SCHEMA = PACKAGE_ROOT / "knowledge_graph" / "equipment_service_profile.schema.json"
ASPEN_EQUIPMENT_EXPORT_SCHEMA = PACKAGE_ROOT / "knowledge_graph" / "aspen_equipment_export.schema.json"
CANONICAL_OPERATIONS = (
    "capabilities",
    "schema_get",
    "catalog",
    "auto_match",
    "manual_match",
    "manual_batch",
    "render_report",
    "organize_answer",
    "customer_export",
    "knowledge_search",
    "aspen_derive",
    "aspen_import",
    "pfd_build",
    "pfd_override",
    "pfd_recalculate",
    "hybrid_prepare",
    "hybrid_continue",
    "hybrid_run",
    "llm_review",
    "llm_apply",
    "selftest",
)
OPERATION_ALIASES = {
    "system.capabilities": "capabilities",
    "schema.get": "schema_get",
    "catalog.get": "catalog",
    "equipment.match": "auto_match",
    "report.render": "render_report",
    "answer.organize": "organize_answer",
    "equipment.customer.export": "customer_export",
    "knowledge.query": "knowledge_search",
    "aspen.export.derive": "aspen_derive",
    "aspen.case.import": "aspen_import",
    "aspen.pfd.build": "pfd_build",
    "aspen.pfd.override": "pfd_override",
    "aspen.pfd.recalculate": "pfd_recalculate",
    "workflow.hybrid.prepare": "hybrid_prepare",
    "workflow.hybrid.continue": "hybrid_continue",
    "workflow.hybrid": "hybrid_run",
    "review.llm": "llm_review",
    "review.apply": "llm_apply",
    "system.selftest": "selftest",
}
OPERATIONS = tuple(dict.fromkeys((*CANONICAL_OPERATIONS, *OPERATION_ALIASES)))
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
FIXED_LLM_API_KEY_ENV = "EQUIPMENT_DESIGN_LLM_API_KEY"
FIXED_LLM_BASE_URL_ENV = "EQUIPMENT_DESIGN_LLM_BASE_URL"
FIXED_LLM_MODEL_ID_ENV = "EQUIPMENT_DESIGN_LLM_MODEL_ID"
HYBRID_SOURCE_OPERATIONS = {"auto_match", "manual_match", "manual_batch", "aspen_derive", "aspen_import"}
REPLAYABLE_HYBRID_SOURCE_OPERATIONS = HYBRID_SOURCE_OPERATIONS - {"aspen_import"}
STRICT_OPERATION_PAYLOAD_KEYS: dict[str, set[str]] = {
    "capabilities": set(),
    "schema_get": {"schema_id"},
    "catalog": set(),
    "selftest": set(),
    "render_report": {"input", "format", "output_path"},
    "organize_answer": {"input", "format", "output_path"},
    "customer_export": {"input", "output_path"},
    "pfd_build": {"bundle_path", "overrides", "output_path"},
    "pfd_override": {"bundle_path", "overrides", "block_id", "selection_id", "output_path"},
    "pfd_recalculate": {
        "bundle_path", "overrides", "parameter_overrides", "block_id",
        "values", "clear", "output_path",
    },
    "hybrid_prepare": {"input", "knowledge", "injection_point", "context_scope"},
    "hybrid_continue": {"prepared", "prepared_path", "step_output", "step_output_path"},
    "hybrid_run": {"input", "knowledge", "injection_point", "context_scope", "llm"},
    "llm_review": {"input", "knowledge", "injection_point", "context_scope", "config", "policy"},
    "llm_apply": {"proposal", "proposal_path", "approval"},
}

SCHEMA_PATHS: dict[str, Path] = {
    "equipment-design-agent-request-v1": REQUEST_SCHEMA,
    "equipment-design-agent-response-v1": RESPONSE_SCHEMA,
    "equipment-design-presentation-v1": PRESENTATION_SCHEMA,
    "equipment-design-report-status-v1": REPORT_STATUS_SCHEMA,
    "equipment-agent-organized-answer-v1": ORGANIZED_ANSWER_SCHEMA,
    "equipment-design-llm-context-pack-v1": LLM_CONTEXT_SCHEMA,
    "equipment-design-llm-step-output-v1": LLM_STEP_SCHEMA,
    "equipment-design-llm-prepared-v1": LLM_PREPARED_SCHEMA,
    "equipment-design-app-llm-orchestration-v1": LLM_ORCHESTRATION_SCHEMA,
    "equipment-design-hybrid-result-v2": HYBRID_RESULT_SCHEMA,
    "equipment-design-interleaved-timeline-v1": INTERLEAVED_TIMELINE_SCHEMA,
    "equipment-design-authority-revision-v1": AUTHORITY_REVISION_SCHEMA,
    "equipment-design-source-code-manifest-v1": SOURCE_CODE_MANIFEST_SCHEMA,
    "equipment-design-parameter-package-v1": PARAMETER_PACKAGE_SCHEMA,
    "equipment-connection-selection-package-v1": CONNECTION_SELECTION_SCHEMA,
    "equipment-service-profile-v1": SERVICE_PROFILE_SCHEMA,
    "aspen-equipment-export-v1": ASPEN_EQUIPMENT_EXPORT_SCHEMA,
    "equipment-customer-output-profiles-v1": CUSTOMER_PROFILE_SCHEMA,
    "equipment-customer-delivery-bundle-v1": CUSTOMER_DELIVERY_BUNDLE_SCHEMA,
    "equipment-overview-table-v1": EQUIPMENT_OVERVIEW_SCHEMA,
    "equipment-family-datasheet-v1": EQUIPMENT_FAMILY_DATASHEET_SCHEMA,
    "equipment-evidence-index-v1": EQUIPMENT_EVIDENCE_INDEX_SCHEMA,
    "equipment-design-pfd-mapping-v1": PFD_MAPPING_SCHEMA,
    "equipment-formula-trace-v1": FORMULA_TRACE_SCHEMA,
}


class AgentRequestError(ValueError):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class AgentOperationError(RuntimeError):
    def __init__(self, code: str, message: str, details: Any = None, exit_code: int = 3) -> None:
        super().__init__(message)
        self.code = code
        self.details = details
        self.exit_code = exit_code


def _agent_provider_config(raw_config: Any) -> dict[str, Any]:
    """Bind credentials to a human-configured provider endpoint profile."""
    if not isinstance(raw_config, dict):
        raise AgentRequestError("LLM_CONFIG_INVALID", "LLM config 必须是对象。")
    config = dict(raw_config)
    if "api_key" in config:
        raise AgentRequestError(
            "API_KEY_LITERAL_FORBIDDEN",
            "请求 JSON 不得保存 API Key；请在固定环境变量 EQUIPMENT_DESIGN_LLM_API_KEY 中提供。",
        )
    provider = str(config.get("provider", "openai_compatible")).strip()
    if provider not in llm_bridge.SUPPORTED_PROVIDERS:
        raise AgentRequestError("LLM_PROVIDER_INVALID", f"不支持的 LLM provider：{provider}。")
    requested_env = str(config.pop("api_key_env", FIXED_LLM_API_KEY_ENV)).strip()
    if requested_env and requested_env != FIXED_LLM_API_KEY_ENV:
        raise AgentRequestError(
            "API_KEY_ENV_NOT_ALLOWLISTED",
            f"api_key_env 只能省略或固定为 {FIXED_LLM_API_KEY_ENV}。",
        )
    supplied_base_url = str(config.pop("base_url", "")).strip()
    if provider == "openai":
        if supplied_base_url:
            raise AgentRequestError(
                "LLM_BASE_URL_LITERAL_FORBIDDEN",
                "Agent 请求不能覆盖 OpenAI endpoint；provider=openai 固定使用 api.openai.com。",
            )
        config["base_url"] = "https://api.openai.com/v1"
        config["api_key"] = os.environ.get(FIXED_LLM_API_KEY_ENV, "")
    elif provider == "openai_compatible":
        if supplied_base_url:
            raise AgentRequestError(
                "LLM_BASE_URL_LITERAL_FORBIDDEN",
                f"Agent 请求不能携带远程 base_url；请由人类在 {FIXED_LLM_BASE_URL_ENV} 中绑定 endpoint。",
            )
        bound_base_url = os.environ.get(FIXED_LLM_BASE_URL_ENV, "").strip()
        if not bound_base_url:
            raise AgentRequestError(
                "LLM_BASE_URL_PROFILE_MISSING",
                f"provider=openai_compatible 需要预先设置 {FIXED_LLM_BASE_URL_ENV}。",
            )
        config["base_url"] = bound_base_url
        config["api_key"] = os.environ.get(FIXED_LLM_API_KEY_ENV, "")
    elif provider == "local_openai_compatible":
        config["base_url"] = supplied_base_url or llm_bridge.SUPPORTED_PROVIDERS[provider]["default_base_url"]
        config["api_key"] = ""
    else:  # offline mock
        config.pop("base_url", None)
        config["api_key"] = ""
    request_model = str(config.get("model") or "").strip()
    bound_model = request_model or os.environ.get(FIXED_LLM_MODEL_ID_ENV, "").strip()
    if provider != "mock" and not bound_model:
        raise AgentRequestError(
            "LLM_MODEL_ID_MISSING",
            f"LLM 模型 ID 不能为空；请在请求的 model 字段或 {FIXED_LLM_MODEL_ID_ENV} 中填写准确模型 ID。",
        )
    config["model"] = bound_model or "offline-mock"
    return config


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _schema_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for schema_id, path in SCHEMA_PATHS.items():
        resolved = path.resolve()
        if not resolved.is_file():
            raise AgentOperationError("SCHEMA_FILE_MISSING", f"协议 schema 不存在：{schema_id}", {"path": str(resolved)})
        catalog.append({
            "schema_id": schema_id,
            "sha256": sha256_file(resolved),
            "size_bytes": resolved.stat().st_size,
        })
    return catalog


def _schema_document(schema_id: str) -> dict[str, Any]:
    path = SCHEMA_PATHS.get(schema_id)
    if path is None:
        raise AgentRequestError(
            "UNKNOWN_SCHEMA_ID",
            f"未知 schema_id：{schema_id}",
            {"allowed": sorted(SCHEMA_PATHS)},
        )
    document = load_json_file(path)
    if not isinstance(document, dict):
        raise AgentOperationError("SCHEMA_DOCUMENT_INVALID", f"schema 不是 JSON 对象：{schema_id}")
    return {
        "schema_id": schema_id,
        "sha256": sha256_file(path),
        "document": document,
    }


def _artifact_manifest(paths: list[str] | None) -> list[dict[str, Any]]:
    manifest: list[dict[str, Any]] = []
    for raw in paths or []:
        root = Path(raw).expanduser().resolve()
        if root.is_file():
            manifest.append({
                "kind": "file",
                "artifact_root": str(root.parent),
                "relative_path": root.name,
                "sha256": sha256_file(root),
                "size_bytes": root.stat().st_size,
            })
            continue
        if root.is_dir():
            for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
                manifest.append({
                    "kind": "file",
                    "artifact_root": str(root),
                    "relative_path": path.relative_to(root).as_posix(),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                })
    return manifest


def _provenance() -> dict[str, Any]:
    paths = {
        "rules": Path(app_core.matcher.RULES_PATH),
        "model_rules": Path(app_core.matcher.MODEL_RULES_PATH),
        "parameter_templates": Path(app_core.matcher.PARAMETER_TEMPLATES_PATH),
        "customer_output_profiles": Path(app_core.matcher.CUSTOMER_OUTPUT_PROFILES_PATH),
        "pump_standard_points": Path(app_core.matcher.PUMP_STANDARD_POINTS_PATH),
        "pipe_standard_dn_od": Path(app_core.matcher.PIPE_STANDARD_DN_OD_PATH),
        "graph": Path(app_core.matcher.GRAPH_PATH),
        "request_schema": REQUEST_SCHEMA,
        "response_schema": RESPONSE_SCHEMA,
        "presentation_schema": PRESENTATION_SCHEMA,
        "llm_context_schema": LLM_CONTEXT_SCHEMA,
        "llm_step_schema": LLM_STEP_SCHEMA,
        "llm_prepared_schema": LLM_PREPARED_SCHEMA,
        "llm_orchestration_schema": LLM_ORCHESTRATION_SCHEMA,
        "hybrid_result_schema": HYBRID_RESULT_SCHEMA,
        "parameter_package_schema": PARAMETER_PACKAGE_SCHEMA,
        "connection_selection_schema": CONNECTION_SELECTION_SCHEMA,
        "service_profile_schema": SERVICE_PROFILE_SCHEMA,
        "aspen_equipment_export_schema": ASPEN_EQUIPMENT_EXPORT_SCHEMA,
        "customer_profile_schema": CUSTOMER_PROFILE_SCHEMA,
        "customer_delivery_bundle_schema": CUSTOMER_DELIVERY_BUNDLE_SCHEMA,
        "equipment_overview_schema": EQUIPMENT_OVERVIEW_SCHEMA,
        "equipment_family_datasheet_schema": EQUIPMENT_FAMILY_DATASHEET_SCHEMA,
        "equipment_evidence_index_schema": EQUIPMENT_EVIDENCE_INDEX_SCHEMA,
        "pfd_mapping_schema": PFD_MAPPING_SCHEMA,
    }
    result: dict[str, Any] = {
        "agent_protocol_version": PROTOCOL_VERSION,
        "matcher_engine_version": getattr(app_core.matcher, "ENGINE_VERSION", "unknown"),
    }
    bundle = app_core.runtime_bundle_verification()
    result.update({
        "bundle_revision": bundle.get("bundle_revision"),
        "manifest_sha256": bundle.get("manifest_sha256"),
        "verification_status": bundle.get("verification_status"),
    })
    for name, path in paths.items():
        resolved = path.expanduser().resolve()
        result[f"{name}_path"] = str(resolved)
        result[f"{name}_sha256"] = sha256_file(resolved) if resolved.is_file() else None
    return result


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, value: Any, pretty: bool = False) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(rendered, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_text(path: Path, value: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )
    try:
        temporary.write_text(
            value,
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _object_from_payload(payload: dict[str, Any], inline_key: str, path_key: str) -> dict[str, Any]:
    inline = payload.get(inline_key)
    path_value = str(payload.get(path_key, "")).strip()
    if isinstance(inline, dict) and path_value:
        raise AgentRequestError("AMBIGUOUS_INPUT", f"{inline_key} 与 {path_key} 只能提供一个。")
    if isinstance(inline, dict):
        return inline
    if path_value:
        path = Path(path_value).expanduser().resolve()
        if not path.is_file():
            raise AgentRequestError("INPUT_FILE_NOT_FOUND", f"输入文件不存在：{path}")
        loaded = load_json_file(path)
        if not isinstance(loaded, dict):
            raise AgentRequestError("INPUT_NOT_OBJECT", f"{path_key} 必须指向 JSON 对象。")
        return loaded
    raise AgentRequestError("MISSING_INPUT", f"必须提供 {inline_key} 或 {path_key}。")


def _pfd_bundle_from_payload(payload: dict[str, Any]) -> tuple[Path, dict[str, Any], str]:
    """Load one immutable Aspen export bundle for a PFD operation."""

    path_value = str(payload.get("bundle_path", "")).strip()
    if not path_value:
        raise AgentRequestError("PFD_BUNDLE_PATH_REQUIRED", "PFD 操作需要 bundle_path。")
    path = Path(path_value).expanduser().resolve()
    if path.suffix.casefold() != ".json":
        raise AgentRequestError(
            "PFD_BUNDLE_PATH_NOT_JSON",
            "bundle_path 必须指向 .json 文件。",
            {"path": str(path)},
        )
    if not path.is_file():
        raise AgentRequestError(
            "PFD_BUNDLE_FILE_NOT_FOUND",
            f"Aspen 导出 bundle 不存在：{path}",
            {"path": str(path)},
        )
    source_hash = sha256_file(path)
    try:
        value = load_json_file(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        details: dict[str, Any] = {"path": str(path)}
        if isinstance(exc, json.JSONDecodeError):
            details.update({"line": exc.lineno, "column": exc.colno})
        raise AgentRequestError(
            "PFD_BUNDLE_JSON_INVALID",
            f"Aspen 导出 bundle 不是有效 JSON：{path}",
            details,
        ) from exc
    if not isinstance(value, dict):
        raise AgentRequestError(
            "PFD_BUNDLE_JSON_NOT_OBJECT",
            "Aspen 导出 bundle 顶层必须是 JSON 对象。",
            {"path": str(path)},
        )
    return path, value, source_hash


def _pfd_derivation_context(
    bundle: dict[str, Any],
    source_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Replay the one authoritative Aspen-unit adapter for every PFD caller."""

    import aspen_equipment_derivation

    derived = aspen_equipment_derivation.derive_bundle(dict(bundle), source_path)
    canonical_blocks = aspen_pfd.canonical_parameters_by_block(derived)
    canonical_streams = aspen_pfd.canonical_parameters_by_stream(derived)
    issue_source = derived.get("normalization_diagnostics")
    if not isinstance(issue_source, list):
        issue_source = derived.get("errors", [])
    issues = [dict(item) for item in issue_source if isinstance(item, Mapping)]
    return derived, canonical_blocks, canonical_streams, issues


def _pfd_overrides(payload: dict[str, Any]) -> dict[str, str]:
    value = payload.get("overrides", {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise AgentRequestError("PFD_OVERRIDES_INVALID", "overrides 必须是 block_id -> selection_id 对象。")
    normalized: dict[str, str] = {}
    for raw_block_id, raw_selection_id in value.items():
        if not isinstance(raw_block_id, str) or not raw_block_id.strip():
            raise AgentRequestError("PFD_OVERRIDES_INVALID", "overrides 包含空 block_id。")
        if not isinstance(raw_selection_id, str) or not raw_selection_id.strip():
            raise AgentRequestError(
                "PFD_OVERRIDES_INVALID",
                "overrides 的 selection_id 必须是非空字符串；恢复自动请使用 pfd_override.selection_id=AUTO。",
                {"block_id": raw_block_id},
            )
        normalized[raw_block_id.strip()] = raw_selection_id.strip()
    return dict(sorted(normalized.items()))


def _pfd_parameter_state(
    payload: dict[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    value = payload.get("parameter_overrides", {})
    try:
        return aspen_pfd.normalize_parameter_overrides(bundle, value)
    except aspen_pfd.AspenPFDMappingError as exc:
        raise AgentRequestError(exc.code, exc.message, exc.details) from exc


def _pfd_output_path(payload: dict[str, Any], source_path: Path) -> Path | None:
    output_value = str(payload.get("output_path", "")).strip()
    if not output_value:
        return None
    output_path = Path(output_value).expanduser().resolve()
    if output_path.suffix.casefold() != ".json":
        raise AgentRequestError(
            "PFD_OUTPUT_PATH_NOT_JSON",
            "PFD output_path 必须使用 .json 后缀。",
            {"path": str(output_path)},
        )
    if output_path == source_path:
        raise AgentRequestError(
            "PFD_OUTPUT_OVERWRITES_SOURCE_FORBIDDEN",
            "PFD 输出不得覆盖输入 Aspen bundle。",
            {"bundle_path": str(source_path), "output_path": str(output_path)},
        )
    if output_path.exists() and not output_path.is_file():
        raise AgentRequestError(
            "PFD_OUTPUT_PATH_INVALID",
            "PFD output_path 已存在且不是普通文件。",
            {"path": str(output_path)},
        )
    return output_path


def _pfd_operation_result(
    *,
    action: str,
    source_path: Path,
    source_hash: str,
    mapping: dict[str, Any],
    output_path: Path | None,
) -> tuple[dict[str, Any], list[str]]:
    if output_path is not None:
        try:
            atomic_write_json(output_path, mapping, pretty=True)
        except OSError as exc:
            raise AgentOperationError(
                "PFD_OUTPUT_WRITE_FAILED",
                f"PFD mapping 写入失败：{output_path}",
                {"path": str(output_path), "error": str(exc)},
                exit_code=3,
            ) from exc
    # The mapper and writer are read-only with respect to the source.  Check
    # again so a future refactor cannot silently turn an override into a
    # bundle/BKP mutation route.
    final_source_hash = sha256_file(source_path)
    if final_source_hash != source_hash:
        raise AgentOperationError(
            "PFD_SOURCE_MUTATION_DETECTED",
            "PFD 操作期间输入 bundle 发生变化；输出已隔离，结果拒绝使用。",
            {"path": str(source_path), "before": source_hash, "after": final_source_hash},
            exit_code=6,
        )
    summary = aspen_pfd.summarize_pfd_mapping(mapping)
    result = {
        "schema": "equipment-design-agent-pfd-operation-result-v1",
        "action": action,
        "bundle_path": str(source_path),
        "bundle_file_sha256": source_hash,
        "mapping_sha256": mapping.get("mapping_sha256"),
        "summary": summary,
        "overrides": mapping.get("overrides", {}),
        "output_path": str(output_path) if output_path else None,
        "mapping": mapping,
        "source_mutated": False,
        "decision_boundary": (
            "PFD type override changes only the deterministic routing choice. "
            "It does not modify the Aspen bundle/BKP and is not model or mechanical-design evidence."
        ),
    }
    return result, [str(output_path)] if output_path else []


def _pfd_recalculation_operation_result(
    *,
    source_path: Path,
    source_hash: str,
    output_path: Path | None,
    updated: Mapping[str, Any],
    selection_id: str | None,
    base_input: Mapping[str, Any],
    merged_input: Mapping[str, Any],
    deterministic_recalculation: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    mapping = dict(updated.get("mapping", {}))
    deterministic_match = (
        deterministic_recalculation.get("result")
        if isinstance(deterministic_recalculation, Mapping)
        and isinstance(deterministic_recalculation.get("result"), Mapping)
        else {}
    )
    model_decision = (
        deterministic_match.get("model_decision")
        if isinstance(deterministic_match, Mapping)
        and isinstance(deterministic_match.get("model_decision"), Mapping)
        else {}
    )
    verification_missing = (
        list(model_decision.get("verification_missing_fields", []))
        if isinstance(model_decision.get("verification_missing_fields"), list)
        else []
    )
    model_status = str(model_decision.get("model_status") or "")
    if deterministic_recalculation is None:
        recalculation_status = "WAITING_UNIQUE_TYPE_OR_CANONICAL_INPUT"
    elif verification_missing and model_status.casefold() not in {"final_model", "same_equipment_verified"}:
        recalculation_status = "RECALCULATED_WAITING_FORMAL_EVIDENCE"
    elif any(token in model_status.upper() for token in ("WAIT", "PENDING", "NOT_READY", "INCOMPLETE")):
        recalculation_status = "RECALCULATED_WAITING_CALCULATED_PARAMETERS"
    else:
        recalculation_status = "RECALCULATED"
    result = {
        "schema": "equipment-design-agent-pfd-recalculation-result-v1",
        "action": updated.get("action"),
        "bundle_path": str(source_path),
        "bundle_file_sha256": source_hash,
        "block_id": updated.get("block_id"),
        "selection_id": selection_id,
        "parameter_overrides": updated.get("parameter_overrides", {}),
        "effective_parameter_overrides": updated.get("effective_values", {}),
        "base_canonical_match_input": dict(base_input),
        "merged_match_input": dict(merged_input),
        "input_provenance": {
            "base": "ASPEN_DERIVED_PROCESS_SIDE",
            "parameter_overrides": "USER_SUPPLIED_PER_BLOCK_NOT_EVIDENCE_BY_ITSELF",
            "source_bundle_mutated": False,
        },
        "deterministic_recalculation": dict(deterministic_recalculation) if deterministic_recalculation else None,
        "recalculation_status": recalculation_status,
        "formal_evidence_status": {
            "model_status": model_status or None,
            "verification_missing_fields": verification_missing,
            "waiting": recalculation_status == "RECALCULATED_WAITING_FORMAL_EVIDENCE",
        },
        "change_impact": updated.get("change_impact", {}),
        "mapping_sha256": mapping.get("mapping_sha256"),
        "mapping": mapping,
        "summary": aspen_pfd.summarize_pfd_mapping(mapping),
        "source_mutated": False,
        "llm_used": False,
        "decision_boundary": (
            "Per-block parameter overrides are user inputs in a separate layer. They do not mutate the "
            "Aspen bundle/BKP and are not mechanical, vendor or final-model evidence by themselves."
        ),
        "output_path": str(output_path) if output_path else None,
    }
    if output_path is not None:
        try:
            atomic_write_json(output_path, result, pretty=True)
        except OSError as exc:
            raise AgentOperationError(
                "PFD_OUTPUT_WRITE_FAILED",
                f"PFD 参数重算结果写入失败：{output_path}",
                {"path": str(output_path), "error": str(exc)},
                exit_code=3,
            ) from exc
    final_source_hash = sha256_file(source_path)
    if final_source_hash != source_hash:
        raise AgentOperationError(
            "PFD_SOURCE_MUTATION_DETECTED",
            "PFD 参数重算期间输入 bundle 发生变化；结果拒绝使用。",
            {"path": str(source_path), "before": source_hash, "after": final_source_hash},
            exit_code=6,
        )
    return result, [str(output_path)] if output_path else []


def _hybrid_deterministic_input(
    payload: dict[str, Any],
    api: EquipmentDesignApi,
    *,
    allow_aspen_import: bool = True,
) -> tuple[dict[str, Any], list[str], str, dict[str, Any]]:
    if isinstance(payload.get("deterministic_result"), dict) or str(payload.get("deterministic_result_path", "")).strip():
        raise AgentRequestError(
            "UNTRUSTED_DETERMINISTIC_RESULT_FORBIDDEN",
            "Agent 混合协议不接受裸 deterministic_result/path；必须提供 input.operation + input.payload 并由当前引擎重跑。",
        )
    source = payload.get("input")
    if not isinstance(source, dict):
        raise AgentRequestError(
            "HYBRID_INPUT_REQUIRED",
            "混合编排必须提供 input.operation + input.payload，由当前确定性引擎执行。",
        )
    requested_source = str(source.get("operation", "")).strip()
    source_operation = OPERATION_ALIASES.get(requested_source, requested_source)
    if source_operation not in HYBRID_SOURCE_OPERATIONS:
        raise AgentRequestError(
            "HYBRID_SOURCE_OPERATION_INVALID",
            f"hybrid input.operation 只允许：{', '.join(sorted(HYBRID_SOURCE_OPERATIONS))}。",
        )
    if source_operation == "aspen_import" and not allow_aspen_import:
        raise AgentRequestError(
            "HYBRID_SOURCE_NOT_REPLAYABLE",
            "跨进程 prepare/continue 不直接接受 aspen_import；请先导出工件，再以 aspen_derive 重放，或使用单次 hybrid_run。",
        )
    source_payload = source.get("payload", {})
    if not isinstance(source_payload, dict):
        raise AgentRequestError("HYBRID_SOURCE_PAYLOAD_INVALID", "hybrid input.payload 必须是对象。")
    deterministic, artifacts = _execute(source_operation, source_payload, api)
    if not isinstance(deterministic, dict):
        raise AgentOperationError("HYBRID_DETERMINISTIC_RESULT_INVALID", "确定性操作未返回 JSON 对象。")
    frozen_input = {
        "operation": source_operation,
        "payload": json.loads(json.dumps(source_payload, ensure_ascii=False)),
    }
    return deterministic, artifacts, source_operation, frozen_input


def _hybrid_options(payload: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    knowledge = payload.get("knowledge", {})
    if not isinstance(knowledge, dict):
        raise AgentRequestError("HYBRID_KNOWLEDGE_INVALID", "hybrid knowledge 必须是对象。")
    injection_point = str(payload.get("injection_point", "audit")).strip()
    if injection_point not in llm_bridge.INJECTION_POINT_POLICIES:
        raise AgentRequestError(
            "HYBRID_INJECTION_POINT_INVALID",
            f"injection_point 只允许：{', '.join(sorted(llm_bridge.INJECTION_POINT_POLICIES))}。",
        )
    context_scope = str(payload.get("context_scope", "minimum")).strip()
    if context_scope == "full":
        context_scope = "full_bundle"
    if context_scope not in {"minimum", "routed", "full_family", "full_bundle"}:
        raise AgentRequestError("HYBRID_CONTEXT_SCOPE_INVALID", "context_scope 无效。")
    return knowledge, injection_point, context_scope


def _require_current_authority_revision(value: Any, location: str) -> dict[str, Any]:
    try:
        embedded = authority_revision.validate_authority_revision(value)
        current = authority_revision.current_authority_revision()
    except authority_revision.AuthorityRevisionError as exc:
        raise AgentOperationError(
            "HYBRID_AUTHORITY_REVISION_INVALID",
            f"{location} 的 authority_revision 无效。",
            {"location": location, "reason": str(exc)},
        ) from exc
    if embedded != current:
        raise AgentOperationError(
            "HYBRID_AUTHORITY_REVISION_MISMATCH",
            f"{location} 绑定的确定性权威版本与当前运行时不一致；旧审核或旧批准不得跨版本复用。",
            {
                "location": location,
                "expected_current": current["authority_revision_sha256"],
                "actual_submitted": embedded["authority_revision_sha256"],
                "current_agent_protocol_version": current["agent_protocol_version"],
                "submitted_agent_protocol_version": embedded["agent_protocol_version"],
                "current_matcher_engine_version": current["matcher_engine_version"],
                "submitted_matcher_engine_version": embedded["matcher_engine_version"],
            },
        )
    return embedded


def _replay_contract(
    source_input: dict[str, Any],
    knowledge: dict[str, Any],
    injection_point: str,
    context_scope: str,
    deterministic_result: dict[str, Any],
) -> dict[str, Any]:
    source_operation = str(source_input.get("operation", "")).strip()
    return {
        "schema": "equipment-design-deterministic-replay-v1",
        "replayable": source_operation in REPLAYABLE_HYBRID_SOURCE_OPERATIONS,
        "authority_revision": authority_revision.current_authority_revision(),
        "input": json.loads(json.dumps(source_input, ensure_ascii=False)),
        "knowledge": json.loads(json.dumps(knowledge, ensure_ascii=False)),
        "injection_point": injection_point,
        "context_scope": context_scope,
        "deterministic_result_sha256": sha256_json(deterministic_result),
    }


def _build_prepared_from_replay_contract(
    replay: Any,
    api: EquipmentDesignApi,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str]:
    if not isinstance(replay, dict) or replay.get("schema") != "equipment-design-deterministic-replay-v1":
        raise AgentRequestError(
            "HYBRID_REPLAY_CONTRACT_REQUIRED",
            "操作只接受由 Agent hybrid_prepare 生成的确定性 replay_contract。",
        )
    if replay.get("replayable") is not True:
        raise AgentRequestError("HYBRID_REPLAY_NOT_ALLOWED", "该 prepared 的确定性来源不可跨进程安全重放。")
    _require_current_authority_revision(
        replay.get("authority_revision"),
        "replay_contract",
    )
    source_input = replay.get("input")
    knowledge = replay.get("knowledge")
    if not isinstance(source_input, dict) or not isinstance(knowledge, dict):
        raise AgentRequestError("HYBRID_REPLAY_CONTRACT_INVALID", "replay_contract 的 input/knowledge 无效。")
    deterministic, _artifacts, source_operation, rebuilt_input = _hybrid_deterministic_input(
        {"input": source_input},
        api,
        allow_aspen_import=False,
    )
    actual_result_hash = sha256_json(deterministic)
    expected_result_hash = str(replay.get("deterministic_result_sha256", "")).strip().upper()
    if actual_result_hash != expected_result_hash:
        raise AgentOperationError(
            "HYBRID_DETERMINISTIC_REPLAY_MISMATCH",
            "确定性输入重放结果与 prepared 绑定哈希不一致。",
            {"expected": expected_result_hash, "actual": actual_result_hash},
        )
    prepare_response = api.hybrid_prepare(
        deterministic,
        knowledge,
        str(replay.get("injection_point", "audit")),
        str(replay.get("context_scope", "minimum")),
    )
    if not prepare_response.get("ok"):
        raise AgentOperationError(
            "HYBRID_REPLAY_PREPARE_FAILED",
            str(prepare_response.get("error", "确定性重放后无法重建 prepared。")),
        )
    rebuilt_replay = _replay_contract(
        rebuilt_input,
        knowledge,
        str(replay.get("injection_point", "audit")),
        str(replay.get("context_scope", "minimum")),
        deterministic,
    )
    rebuilt = llm_bridge.with_replay_contract(prepare_response["value"], rebuilt_replay)
    return rebuilt, deterministic, rebuilt_input, source_operation


def _rebuild_prepared_from_replay(
    prepared: dict[str, Any],
    api: EquipmentDesignApi,
) -> dict[str, Any]:
    claimed_prepared_hash = str(prepared.get("prepared_sha256", "")).strip().upper()
    submitted_without_hash = {
        key: value for key, value in prepared.items() if key != "prepared_sha256"
    }
    actual_submitted_hash = sha256_json(submitted_without_hash)
    if not claimed_prepared_hash or actual_submitted_hash != claimed_prepared_hash:
        raise AgentOperationError(
            "HYBRID_PREPARED_HASH_MISMATCH",
            "提交的 prepared 内容与 prepared_sha256 不一致。",
            {
                "expected": claimed_prepared_hash or None,
                "actual": actual_submitted_hash,
            },
        )
    _require_current_authority_revision(
        prepared.get("authority_revision"),
        "prepared",
    )
    rebuilt, _deterministic, _source_input, _source_operation = _build_prepared_from_replay_contract(
        prepared.get("replay_contract"),
        api,
    )
    if rebuilt.get("prepared_sha256") != prepared.get("prepared_sha256"):
        raise AgentOperationError(
            "HYBRID_PREPARED_REPLAY_MISMATCH",
            "重建的 prepared 与提交的 prepared 不一致；确定性输入、知识资产或上下文已变化。",
            {
                "expected": prepared.get("prepared_sha256"),
                "actual": rebuilt.get("prepared_sha256"),
            },
        )
    return rebuilt


def _validate_request(request: Any) -> tuple[str, str, dict[str, Any]]:
    if not isinstance(request, dict):
        raise AgentRequestError("REQUEST_NOT_OBJECT", "Agent 请求必须是 JSON 对象。")
    unknown_top_level = sorted(set(request) - {"schema", "request_id", "operation", "payload"})
    if unknown_top_level:
        raise AgentRequestError(
            "UNEXPECTED_REQUEST_FIELDS",
            "Agent 请求包含 schema 未允许的顶层字段。",
            {"fields": unknown_top_level},
        )
    schema = str(request.get("schema", "")).strip()
    if schema != "equipment-design-agent-request-v1":
        raise AgentRequestError("UNSUPPORTED_REQUEST_SCHEMA", "schema 必须是 equipment-design-agent-request-v1。", {"actual": schema})
    requested_operation = str(request.get("operation", "")).strip()
    if requested_operation not in OPERATIONS:
        raise AgentRequestError("UNSUPPORTED_OPERATION", f"不支持的 operation：{requested_operation}", {"allowed": list(OPERATIONS)})
    operation = OPERATION_ALIASES.get(requested_operation, requested_operation)
    if "payload" not in request:
        raise AgentRequestError("PAYLOAD_REQUIRED", "Agent 请求必须显式包含 payload 对象。")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise AgentRequestError("PAYLOAD_NOT_OBJECT", "payload 必须是 JSON 对象。")
    allowed_payload_keys = STRICT_OPERATION_PAYLOAD_KEYS.get(operation)
    if allowed_payload_keys is not None:
        unknown_payload = sorted(set(payload) - allowed_payload_keys)
        if unknown_payload:
            raise AgentRequestError(
                "UNEXPECTED_PAYLOAD_FIELDS",
                f"{operation} payload 包含未允许字段。",
                {"fields": unknown_payload, "allowed": sorted(allowed_payload_keys)},
            )
    request_id = str(request.get("request_id") or f"REQ-{uuid.uuid4().hex[:12]}")
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        raise AgentRequestError(
            "INVALID_REQUEST_ID",
            "request_id 只能包含字母、数字、下划线或连字符，长度 1-64。",
            {"actual": request_id},
        )
    return request_id, operation, payload


def _engine_info() -> dict[str, Any]:
    catalog = app_core.load_catalog()
    return {
        "agent_protocol_version": PROTOCOL_VERSION,
        "matcher_engine_version": getattr(app_core.matcher, "ENGINE_VERSION", "unknown"),
        "rule_version": catalog.get("rule_version"),
        "model_rule_version": catalog.get("model_rule_version"),
        "parameter_template_version": catalog.get("parameter_template_version"),
        "selection_count": len(catalog.get("selections", [])),
        "gui_required": False,
        "llm_required": False,
        "com_required": False,
        "operations": list(CANONICAL_OPERATIONS),
    }


def _response_machine_state(operation: str, result: Any, *, ok: bool, error_code: str | None = None) -> dict[str, Any]:
    if isinstance(result, dict) and isinstance(result.get("machine_state"), dict):
        state = dict(result["machine_state"])
        state.setdefault("operation", operation)
        state.setdefault("deterministic_authority", True)
        return state
    return {
        "state": "COMPLETED" if ok else "FAILED",
        "operation": operation,
        "deterministic_authority": True,
        "error_code": error_code,
    }


def _success(request_id: str, operation: str, request_hash: str, result: Any, artifacts: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": "equipment-design-agent-response-v1",
        "request_id": request_id,
        "request_sha256": request_hash,
        "operation": operation,
        "ok": True,
        "status": "PASS",
        "exit_code": 0,
        "machine_state": _response_machine_state(operation, result, ok=True),
        "engine": _engine_info(),
        "result": result,
        "artifacts": _artifact_manifest(artifacts),
        "issues": [],
        "errors": [],
        "provenance": _provenance(),
    }


def _failure(
    request_id: str,
    operation: str,
    request_hash: str,
    code: str,
    message: str,
    details: Any = None,
    exit_code: int = 2,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {
        "schema": "equipment-design-agent-response-v1",
        "request_id": request_id,
        "request_sha256": request_hash,
        "operation": operation,
        "ok": False,
        "status": "FAILED",
        "exit_code": exit_code,
        "machine_state": _response_machine_state(operation, None, ok=False, error_code=code),
        "engine": _engine_info(),
        "result": None,
        "artifacts": [],
        "issues": [error],
        "errors": [error],
        "provenance": _provenance(),
    }


def _hybrid_selection_completeness(
    value: dict[str, Any],
    calculation_application: dict[str, Any] | None,
) -> dict[str, Any]:
    design = value.get("result") if isinstance(value.get("result"), dict) else value
    recommendation = design.get("model_recommendation")
    recommendation = recommendation if isinstance(recommendation, dict) else {}
    package = design.get("design_parameter_package")
    package = package if isinstance(package, dict) else {}
    terminal = recommendation.get("terminal_selection")
    terminal = terminal if isinstance(terminal, dict) else {}
    leading = recommendation.get("leading_candidate")
    leading = leading if isinstance(leading, dict) else {}
    selection_vector = package.get("selection_feature_vector")
    selection_vector = selection_vector if isinstance(selection_vector, dict) else {}
    preliminary_missing = sorted({
        str(field) for field in selection_vector.get("missing_fields", [])
        if str(field).strip()
    })
    package_status = str(package.get("status") or "UNKNOWN")
    vector_status = str(selection_vector.get("status") or "UNKNOWN")
    candidate_axis = str(
        package.get("status_axes", {}).get("candidate_matching")
        if isinstance(package.get("status_axes"), dict)
        else "UNKNOWN"
    )
    hard_gate_failures = [
        {
            "check_id": str(item.get("check_id") or "unknown"),
            "status": str(item.get("status") or "UNKNOWN"),
        }
        for item in package.get("constraint_checks", [])
        if isinstance(item, dict) and item.get("status") == "FAIL"
    ]
    blocking_reasons: list[str] = []
    if package_status in {"BLOCKED", "BLOCKED_PHYSICAL_PHASE"}:
        blocking_reasons.append(f"parameter_package:{package_status}")
    if vector_status == "BLOCKED":
        blocking_reasons.append("selection_feature_vector:BLOCKED")
    if candidate_axis in {
        "BLOCKED_INCOMPATIBLE_PHASE",
        "BLOCKED_CALCULATION",
        "WAITING_SPECIAL_DUTY_ROUTE",
    }:
        blocking_reasons.append(f"candidate_matching:{candidate_axis}")
    blocking_reasons.extend(
        f"constraint:{item['check_id']}:{item['status']}"
        for item in hard_gate_failures
    )
    estimate_fields = sorted(
        (calculation_application or {}).get("applied_model_estimate_inputs", {})
    )
    terminal_complete = (
        terminal.get("status") in {
            "EXPLICIT_TERMINAL_TYPE_SELECTED",
            "CONDITIONED_TERMINAL_TYPE_SELECTED",
            "DEFAULTED_TERMINAL_TYPE_SELECTED",
        }
        and bool(str(terminal.get("recommended_type") or "").strip())
    )
    candidate_complete = bool(
        str(recommendation.get("recommended_type") or "").strip()
        and str(leading.get("designation") or "").strip()
    )
    complete = (
        terminal_complete
        and candidate_complete
        and not preliminary_missing
        and package_status == "READY_FOR_CANDIDATE_MATCHING"
        and vector_status == "READY"
        and candidate_axis == "READY"
        and not blocking_reasons
    )
    formal_gaps = sorted({
        *[
            str(item) for item in recommendation.get("formal_promotion_blockers", [])
            if str(item).strip()
        ],
        *[
            str(item) for item in leading.get("missing_gates", [])
            if str(item).strip()
        ],
    })
    return {
        "schema": "equipment-design-hybrid-selection-completeness-v1",
        "status": (
            "COMPLETE_PRELIMINARY_WITH_LLM_ESTIMATES"
            if complete and estimate_fields
            else "COMPLETE_PRELIMINARY"
            if complete
            else "INCOMPLETE_PRELIMINARY_SELECTION"
        ),
        "acceptance": "PASS" if complete else "FAIL",
        "terminal_form_complete": terminal_complete,
        "engineering_candidate_complete": candidate_complete,
        "preliminary_missing_fields": preliminary_missing,
        "parameter_package_status": package_status,
        "selection_feature_vector_status": vector_status,
        "candidate_matching_status": candidate_axis,
        "hard_gate_failures": hard_gate_failures,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "model_estimate_fields": estimate_fields,
        "formal_evidence_gaps": formal_gaps,
        "formal_promotion_allowed": False if estimate_fields else not bool(formal_gaps),
        "statement": (
            "初步设备型式和工程规格已闭合；模型估算均为 J/provisional，正式选型前必须替换并重算。"
            if complete and estimate_fields
            else "初步设备型式和工程规格已闭合，正式型号仍按同设备证据门判断。"
            if complete
            else "模型调用后初步选型仍未闭合，或存在物理/计算/工程约束硬门；候选文字不得覆盖硬门失败。"
        ),
    }


def _hybrid_result_envelope(
    *,
    state: str,
    deterministic_result: dict[str, Any],
    prepared: dict[str, Any] | None,
    knowledge_context: dict[str, Any] | None,
    source_operation: str,
    llm_requested: bool,
    knowledge_requested: bool,
    orchestration: dict[str, Any] | None = None,
    deterministic_recalculation: dict[str, Any] | None = None,
    calculation_assist_application: dict[str, Any] | None = None,
    terminal_selection_application: dict[str, Any] | None = None,
    errors: list[dict[str, Any]] | None = None,
    steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    failures = errors or []
    review_status = (
        "COMPLETED_STRICT" if orchestration is not None
        else ("FAILED_FALLBACK" if llm_requested and failures else "NOT_REQUESTED")
    )
    execution_timeline = (
        orchestration.get("execution_timeline")
        if isinstance(orchestration, dict) and isinstance(orchestration.get("execution_timeline"), dict)
        else llm_bridge.deterministic_only_timeline(deterministic_result)
    )
    if deterministic_recalculation is not None:
        execution_timeline = llm_bridge.materialize_recalculation_timeline(
            execution_timeline,
            deterministic_recalculation,
        )
    active_result = deterministic_recalculation or deterministic_result
    selection_completeness = _hybrid_selection_completeness(
        active_result,
        calculation_assist_application,
    )
    effective_state = state
    if orchestration is not None:
        if selection_completeness["acceptance"] == "PASS":
            effective_state = (
                "COMPLETED_HYBRID_SELECTION_COMPLETE_PROVISIONAL"
                if selection_completeness["model_estimate_fields"]
                else "COMPLETED_HYBRID_SELECTION_COMPLETE"
            )
        else:
            effective_state = "COMPLETED_HYBRID_SELECTION_INCOMPLETE"
    return {
        "schema": "equipment-design-hybrid-result-v2",
        "machine_state": {
            "state": effective_state,
            "deterministic_authority": True,
            "deterministic_result_preserved": True,
            "llm_requested": llm_requested,
            "knowledge_requested": knowledge_requested,
            "source_operation": source_operation,
            "steps": steps or [],
        },
        "deterministic_result": deterministic_result,
        "deterministic_recalculation": deterministic_recalculation,
        "calculation_assist_application": calculation_assist_application,
        "terminal_selection_application": terminal_selection_application,
        "selection_completeness": selection_completeness,
        "prepared": prepared,
        "knowledge_context": knowledge_context,
        "orchestration": orchestration,
        "execution_timeline": execution_timeline,
        "llm_review": {"status": review_status, "result": orchestration},
        "fallback": {
            "used": bool(failures),
            "preserved_result": "deterministic_result",
            "errors": failures,
        },
        "application_boundary": (
            "When enabled, AI owns the ordering and headings of intermediate output-operation blocks. "
            "The program's initial and recalculated results remain immutable authoritative anchors; AI "
            "cannot rewrite their values, units, blockers, candidate identities or model status."
        ),
    }


def _auto_apply_verified_calculation_inputs(
    source_operation: str,
    source_input: dict[str, Any],
    verified_inputs: dict[str, Any],
    api: EquipmentDesignApi,
) -> tuple[dict[str, Any] | None, list[str], dict[str, Any]]:
    """Apply program-verified missing inputs only; never overwrite a supplied field."""
    if not verified_inputs:
        return None, [], {
            "status": "NOT_NEEDED",
            "applied_inputs": {},
            "deferred_inputs": {},
            "overwritten_fields": [],
        }
    if source_operation not in {"manual_match", "auto_match"}:
        return None, [], {
            "status": "DEFERRED_SOURCE_NOT_SINGLE_DEVICE_PATCHABLE",
            "applied_inputs": {},
            "deferred_inputs": verified_inputs,
            "overwritten_fields": [],
        }
    replay_payload = json.loads(json.dumps(source_input.get("payload", {}), ensure_ascii=False))
    values = replay_payload.get("values")
    if not isinstance(values, dict):
        return None, [], {
            "status": "DEFERRED_VALUES_OBJECT_MISSING",
            "applied_inputs": {},
            "deferred_inputs": verified_inputs,
            "overwritten_fields": [],
        }
    applied: dict[str, Any] = {}
    deferred: dict[str, Any] = {}
    for field, value in verified_inputs.items():
        if field in values and values.get(field) not in (None, ""):
            deferred[field] = value
            continue
        values[field] = value
        applied[field] = value
    if not applied:
        return None, [], {
            "status": "NO_MISSING_FIELDS_APPLIED",
            "applied_inputs": {},
            "deferred_inputs": deferred,
            "overwritten_fields": [],
        }
    recalculation, artifacts = _execute(source_operation, replay_payload, api)
    if not isinstance(recalculation, dict):
        raise AgentOperationError(
            "CALCULATION_ASSIST_REPLAY_INVALID",
            "Verified calculation assistance did not return a deterministic result object.",
        )
    return recalculation, artifacts, {
        "status": "VERIFIED_INPUTS_APPLIED_AND_RECALCULATED",
        "applied_inputs": applied,
        "deferred_inputs": deferred,
        "overwritten_fields": [],
        "recalculation_sha256": sha256_json(recalculation),
    }


def _auto_apply_verified_hybrid_updates(
    source_operation: str,
    source_input: dict[str, Any],
    verified_inputs: dict[str, Any],
    verified_model_estimate_inputs: dict[str, Any],
    verified_model_estimate_lineage: dict[str, Any],
    verified_terminal_overrides: dict[str, str],
    api: EquipmentDesignApi,
) -> tuple[dict[str, Any] | None, list[str], dict[str, Any], dict[str, Any]]:
    """Replay calculation inputs and one scoped registered terminal rule in one pass."""

    if not verified_terminal_overrides and not verified_model_estimate_inputs:
        recalculation, artifacts, calculation_application = _auto_apply_verified_calculation_inputs(
            source_operation,
            source_input,
            verified_inputs,
            api,
        )
        return recalculation, artifacts, calculation_application, {
            "status": "NOT_NEEDED",
            "applied_rule_id": None,
            "deferred_overrides": {},
            "overwritten_fields": [],
        }
    if source_operation not in {"manual_match", "auto_match"}:
        recalculation, artifacts, calculation_application = _auto_apply_verified_calculation_inputs(
            source_operation,
            source_input,
            verified_inputs,
            api,
        )
        calculation_application["deferred_model_estimate_inputs"] = verified_model_estimate_inputs
        calculation_application["applied_model_estimate_inputs"] = {}
        return recalculation, artifacts, calculation_application, {
            "status": "DEFERRED_SOURCE_NOT_SINGLE_DEVICE_PATCHABLE",
            "applied_rule_id": None,
            "deferred_overrides": verified_terminal_overrides,
            "overwritten_fields": [],
        }
    deferred_terminal_overrides: dict[str, str] = {}
    if len(verified_terminal_overrides) > 1:
        deferred_terminal_overrides = dict(verified_terminal_overrides)
        verified_terminal_overrides = {}
    if deferred_terminal_overrides and not verified_model_estimate_inputs and not verified_inputs:
        recalculation, artifacts, calculation_application = _auto_apply_verified_calculation_inputs(
            source_operation,
            source_input,
            verified_inputs,
            api,
        )
        return recalculation, artifacts, calculation_application, {
            "status": "DEFERRED_MULTIPLE_SELECTION_CONTEXTS",
            "applied_rule_id": None,
            "deferred_overrides": deferred_terminal_overrides,
            "overwritten_fields": [],
        }

    replay_payload = json.loads(json.dumps(source_input.get("payload", {}), ensure_ascii=False))
    values = replay_payload.get("values")
    if not isinstance(values, dict):
        return None, [], {
            "status": "DEFERRED_VALUES_OBJECT_MISSING",
            "applied_inputs": {},
            "deferred_inputs": verified_inputs,
            "applied_model_estimate_inputs": {},
            "deferred_model_estimate_inputs": verified_model_estimate_inputs,
            "overwritten_fields": [],
        }, {
            "status": "DEFERRED_VALUES_OBJECT_MISSING",
            "applied_rule_id": None,
            "deferred_overrides": verified_terminal_overrides,
            "overwritten_fields": [],
        }

    applied_inputs: dict[str, Any] = {}
    deferred_inputs: dict[str, Any] = {}
    for field, value in verified_inputs.items():
        if field in values and values.get(field) not in (None, ""):
            deferred_inputs[field] = value
            continue
        values[field] = value
        applied_inputs[field] = value
    applied_model_estimate_inputs: dict[str, Any] = {}
    deferred_model_estimate_inputs: dict[str, Any] = {}
    applied_model_estimate_lineage: dict[str, Any] = {}
    for field, value in verified_model_estimate_inputs.items():
        if field in values and values.get(field) not in (None, ""):
            deferred_model_estimate_inputs[field] = value
            continue
        values[field] = value
        applied_model_estimate_inputs[field] = value
        if field in verified_model_estimate_lineage:
            applied_model_estimate_lineage[field] = verified_model_estimate_lineage[field]
    if not verified_terminal_overrides:
        terminal_application = {
            "status": (
                "DEFERRED_MULTIPLE_SELECTION_CONTEXTS"
                if deferred_terminal_overrides else "NOT_NEEDED"
            ),
            "applied_rule_id": None,
            "deferred_overrides": deferred_terminal_overrides,
            "overwritten_fields": [],
        }
    elif values.get("equipment_type") not in (None, "") or values.get("terminal_type_rule_override_id") not in (None, ""):
        terminal_application = {
            "status": "DEFERRED_EXISTING_TYPE_AUTHORITY",
            "applied_rule_id": None,
            "deferred_overrides": verified_terminal_overrides,
            "overwritten_fields": [],
        }
    else:
        _context_sha256, terminal_rule_id = next(iter(verified_terminal_overrides.items()))
        values["terminal_type_rule_override_id"] = terminal_rule_id
        terminal_application = {
            "status": "REGISTERED_CONDITION_RULE_APPLIED_AND_RECALCULATED",
            "applied_rule_id": terminal_rule_id,
            "selection_context_sha256": _context_sha256,
            "deferred_overrides": {},
            "overwritten_fields": [],
        }
    if (
        terminal_application["applied_rule_id"] is None
        and not applied_inputs
        and not applied_model_estimate_inputs
    ):
        return None, [], {
            "status": "NO_MISSING_FIELDS_APPLIED",
            "applied_inputs": {},
            "deferred_inputs": deferred_inputs,
            "applied_model_estimate_inputs": {},
            "deferred_model_estimate_inputs": deferred_model_estimate_inputs,
            "overwritten_fields": [],
        }, terminal_application

    if source_operation == "manual_match":
        selection_id = str(replay_payload.get("selection_id") or "").strip()
        if not selection_id:
            raise AgentOperationError(
                "HYBRID_ASSIST_REPLAY_INVALID",
                "manual_match provisional replay is missing selection_id.",
            )
        recalculation = app_core.manual_match(
            selection_id,
            values,
            model_estimate_lineage=applied_model_estimate_lineage,
        )
        artifacts: list[str] = []
    else:
        recalculation = app_core.auto_match(
            values,
            model_estimate_lineage=applied_model_estimate_lineage,
        )
        artifacts = []
    if not isinstance(recalculation, dict):
        raise AgentOperationError(
            "HYBRID_ASSIST_REPLAY_INVALID",
            "Verified hybrid assistance did not return a deterministic result object.",
        )
    recalculation_sha256 = sha256_json(recalculation)
    calculation_application = {
        "status": (
            "VERIFIED_INPUTS_APPLIED_AND_RECALCULATED"
            if applied_inputs and not applied_model_estimate_inputs
            else "PROVISIONAL_MODEL_INPUTS_APPLIED_AND_RECALCULATED"
            if applied_model_estimate_inputs
            else "NOT_NEEDED"
        ),
        "applied_inputs": applied_inputs,
        "deferred_inputs": deferred_inputs,
        "applied_model_estimate_inputs": applied_model_estimate_inputs,
        "deferred_model_estimate_inputs": deferred_model_estimate_inputs,
        "model_estimate_lineage": applied_model_estimate_lineage,
        "model_estimate_evidence_class": "J" if applied_model_estimate_inputs else None,
        "model_estimate_promotion_cap": "TYPE_SCREENING" if applied_model_estimate_inputs else None,
        "overwritten_fields": [],
        "recalculation_sha256": recalculation_sha256,
    }
    terminal_application["recalculation_sha256"] = recalculation_sha256
    return recalculation, artifacts, calculation_application, terminal_application


def _execute(operation: str, payload: dict[str, Any], api: EquipmentDesignApi) -> tuple[Any, list[str]]:
    if operation == "capabilities":
        bundle = app_core.require_runtime_bundle()
        return {
            "operations": list(CANONICAL_OPERATIONS),
            "operation_aliases": OPERATION_ALIASES,
            "com": app_core.com_capability(),
            "skill": app_core.skill_entry(),
            "request_schema_path": str(REQUEST_SCHEMA),
            "response_schema_path": str(RESPONSE_SCHEMA),
            "presentation_schema_path": str(PRESENTATION_SCHEMA),
            "llm_context_schema_path": str(LLM_CONTEXT_SCHEMA),
            "llm_step_schema_path": str(LLM_STEP_SCHEMA),
            "llm_prepared_schema_path": str(LLM_PREPARED_SCHEMA),
            "llm_orchestration_schema_path": str(LLM_ORCHESTRATION_SCHEMA),
            "hybrid_result_schema_path": str(HYBRID_RESULT_SCHEMA),
            "interleaved_timeline_schema_path": str(INTERLEAVED_TIMELINE_SCHEMA),
            "parameter_package_schema_path": str(PARAMETER_PACKAGE_SCHEMA),
            "customer_delivery_schema_paths": {
                "profile": str(CUSTOMER_PROFILE_SCHEMA),
                "bundle": str(CUSTOMER_DELIVERY_BUNDLE_SCHEMA),
                "overview": str(EQUIPMENT_OVERVIEW_SCHEMA),
                "datasheet": str(EQUIPMENT_FAMILY_DATASHEET_SCHEMA),
                "evidence_index": str(EQUIPMENT_EVIDENCE_INDEX_SCHEMA),
            },
            "pfd": {
                "operations": ["pfd_build", "pfd_override", "pfd_recalculate"],
                "operation_aliases": {
                    "aspen.pfd.build": "pfd_build",
                    "aspen.pfd.override": "pfd_override",
                    "aspen.pfd.recalculate": "pfd_recalculate",
                },
                "mapping_schema_path": str(PFD_MAPPING_SCHEMA),
                "input_schema": "aspen-equipment-export-v1 bundle_path",
                "layout": "deterministic-scc-longest-path-orthogonal-v1",
                "display_levels": ["compact", "standard", "detailed"],
                "default_display_level": "standard",
                "standard_canvas_fields": ["equipment_id", "source_module_type", "mapped_type", "selection_status"],
                "parameters_inline_on_canvas": False,
                "left_click_contract": "open_block_parameter_detail",
                "right_click_contract": "validated catalog selection override or AUTO restore",
                "parameter_recalculation_contract": (
                    "per-block user-input layer -> deterministic matcher replay -> changed block current; "
                    "incident streams and direct neighbours remain stale until separately replayed"
                ),
                "parameter_override_clear_action": "pfd_recalculate.clear=true",
                "source_bundle_mutation_allowed": False,
                "model_promotion_allowed": False,
                "llm_required": False,
                "hybrid_or_llm_source_operation_allowed": False,
            },
            "bundle_revision": bundle.get("bundle_revision"),
            "manifest_sha256": bundle.get("manifest_sha256"),
            "verification_status": bundle.get("verification_status"),
            "runtime_bundle": bundle,
            "schemas": _schema_catalog(),
            "schema_retrieval_operation": "schema_get",
            "knowledge_packages": app_core.knowledge_packages(),
            "llm_providers": llm_bridge.provider_catalog(),
            "hybrid": {
                "operations": ["hybrid_prepare", "hybrid_continue", "hybrid_run"],
                "external_agent_route": "hybrid_prepare -> external Agent -> hybrid_continue",
                "built_in_provider_route": "hybrid_prepare -> provider -> hybrid_continue (via hybrid_run)",
                "source_operations": ["auto_match", "manual_match", "manual_batch", "aspen_derive", "aspen_import"],
                "injection_points": sorted(llm_bridge.INJECTION_POINT_POLICIES),
                "context_scopes": ["minimum", "routed", "full_family", "full_bundle"],
                "optional_layers": ["knowledge_retrieval", "llm_calculation_assistance", "llm_orchestration"],
                "fallback": "preserve_deterministic_result",
                "primary_llm_role": "calculation_assistance_and_avoidable_stop_reduction",
                "calculation_recipe_catalog": llm_bridge.calculation_recipe_catalog(),
                "verified_recipe_values_computed_by": "deterministic_program",
                "verified_missing_inputs_auto_replayed_for": ["manual_match", "auto_match"],
                "bad_assist_scope": "single_item_nonblocking",
                "uncertain_model_inference": (
                    "missing_only_structured_estimate_program_validated_"
                    "preliminary_auto_apply"
                ),
                "model_estimate_required_controls": [
                    "registered_missing_preliminary_field",
                    "same_case_or_engineering_basis",
                    "explicit_assumptions",
                    "numeric_bounds_or_registered_enum",
                    "confidence",
                    "sensitivity_note",
                    "program_sanity_and_cross_field_replay",
                    "J_provisional_TYPE_SCREENING_cap",
                ],
                "existing_numeric_overwrite_allowed": False,
                "ai_controls_output_composition": True,
                "program_result_anchors": ["deterministic_result", "deterministic_recalculation"],
                "program_result_blocks_are_immutable": True,
                "interleaved_timeline_schema": "equipment-design-interleaved-timeline-v1",
                "llm_apply_requires_separate_explicit_approval": True,
                "candidate_model_free_text_allowed": False,
                "fixed_api_key_env": FIXED_LLM_API_KEY_ENV,
                "fixed_openai_compatible_base_url_env": FIXED_LLM_BASE_URL_ENV,
                "fixed_model_id_env": FIXED_LLM_MODEL_ID_ENV,
                "configured_default_model_id": os.environ.get(FIXED_LLM_MODEL_ID_ENV, "").strip() or None,
                "arbitrary_environment_variable_lookup_allowed": False,
                "agent_remote_base_url_override_allowed": False,
                "endpoint_binding": {
                    "openai": "https://api.openai.com/v1",
                    "openai_compatible": f"human-configured {FIXED_LLM_BASE_URL_ENV}",
                    "local_openai_compatible": "loopback only; request may choose loopback URL",
                },
            },
            "input_channels": ["json_file", "stdin", "jsonl_session"],
            "output_channels": ["json_file", "stdout", "jsonl_session"],
            "reporting": {
                "render_operation": "render_report",
                "formats": ["html", "markdown", "json"],
                "organized_answer_operation": "organize_answer",
                "organized_answer_schema": (
                    "equipment-agent-organized-answer-v1"
                ),
                "fixed_section_order": [
                    "结论",
                    "计算",
                    "候选与系统修改方案",
                    "强制警告",
                    "待补证据",
                    "下一步",
                ],
                "llm_may_organize_language_only": True,
                "llm_may_change_counts_models_or_open_gates": False,
            },
            "session_mode": {
                "cli_flag": "--session-jsonl",
                "aliases": ["--serve-stdio"],
                "framing": "one UTF-8 JSON request and one UTF-8 JSON response per line",
                "runtime_asset_verification": "once_per_process",
                "equipment_api_instance": "shared_within_session",
                "request_exit_code_field": "exit_code",
                "eof_action": "clean_shutdown",
            },
            "gui_required": False,
        }, []
    if operation == "schema_get":
        schema_id = str(payload.get("schema_id", "")).strip()
        if not schema_id:
            raise AgentRequestError("SCHEMA_ID_REQUIRED", "schema_get.payload.schema_id 不能为空。")
        return _schema_document(schema_id), []
    if operation == "catalog":
        return app_core.load_catalog(), []
    if operation == "auto_match":
        values = payload.get("values")
        records = payload.get("records")
        if isinstance(values, dict) and records is not None:
            raise AgentRequestError("AMBIGUOUS_INPUT", "auto_match 的 values 与 records 只能提供一个。")
        if isinstance(values, dict):
            return app_core.auto_match(values), []
        if isinstance(records, list) and records and all(isinstance(item, dict) for item in records):
            results = [app_core.auto_match(item) for item in records]
            return {"count": len(results), "items": results}, []
        raise AgentRequestError("AUTO_MATCH_INPUT_INVALID", "auto_match 需要 values 对象或非空 records 对象数组。")
    if operation == "manual_match":
        selection_id = str(payload.get("selection_id", "")).strip()
        values = payload.get("values")
        if not selection_id or not isinstance(values, dict):
            raise AgentRequestError("MANUAL_INPUT_INVALID", "manual_match 需要 selection_id 和 values 对象。")
        return app_core.manual_match(selection_id, values), []
    if operation == "manual_batch":
        rows = payload.get("items")
        if not isinstance(rows, list) or not rows:
            raise AgentRequestError("MANUAL_BATCH_INVALID", "manual_batch 需要非空 items 数组。")
        results: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("values"), dict):
                raise AgentRequestError("MANUAL_BATCH_ROW_INVALID", f"items[{index}] 缺少 selection_id/values。")
            selection_id = str(row.get("selection_id", "")).strip()
            if not selection_id:
                raise AgentRequestError("MANUAL_BATCH_ROW_INVALID", f"items[{index}] 缺少 selection_id。")
            results.append(app_core.manual_match(selection_id, row["values"]))
        return {"count": len(results), "items": results}, []
    if operation == "render_report":
        if not isinstance(payload.get("input"), dict):
            raise AgentRequestError(
                "REPORT_INPUT_REQUIRED",
                "render_report 必须提供 input.operation + input.payload，由当前确定性引擎复算后渲染。",
            )
        deterministic, source_artifacts, _source_operation, _source_input = _hybrid_deterministic_input(
            payload,
            api,
            allow_aspen_import=False,
        )
        presentation = result_presentation.build_presentation(deterministic)
        organized_answer = result_presentation.build_organized_answer(
            presentation
        )
        output_format = str(payload.get("format", "html")).strip().lower()
        if output_format == "md":
            output_format = "markdown"
        if output_format not in {"html", "json", "markdown"}:
            raise AgentRequestError(
                "REPORT_FORMAT_INVALID",
                "render_report format 只能是 html、markdown/md 或 json。",
            )
        output_value = str(payload.get("output_path", "")).strip()
        artifacts: list[str] = list(source_artifacts)
        output_path: Path | None = None
        if output_value:
            output_path = Path(output_value).expanduser().resolve()
            if output_format == "html":
                atomic_write_text(
                    output_path,
                    result_presentation.render_html(presentation),
                )
            elif output_format == "markdown":
                atomic_write_text(
                    output_path,
                    result_presentation.render_organized_markdown(
                        organized_answer
                    ),
                )
            else:
                atomic_write_json(
                    output_path,
                    {
                        "presentation": presentation,
                        "organized_answer": organized_answer,
                    },
                    pretty=True,
                )
            artifacts.append(str(output_path))
        report_manifest = {
            "schema": "equipment-design-report-manifest-v1",
            "format": output_format,
            "output_path": (
                str(output_path) if output_path is not None else None
            ),
            "output_file_sha256": (
                sha256_file(output_path)
                if output_path is not None
                else None
            ),
            "source_deterministic_result_sha256": sha256_json(
                deterministic
            ),
            "presentation_sha256": sha256_json(presentation),
            "organized_answer_sha256": organized_answer.get(
                "organized_answer_sha256"
            ),
            "program_generated": True,
            "llm_used": False,
        }
        report_manifest["manifest_sha256"] = sha256_json(
            report_manifest
        )
        return {
            "presentation": presentation,
            "organized_answer": organized_answer,
            "format": output_format,
            "output_path": (
                str(output_path) if output_path is not None else None
            ),
            "report_manifest": report_manifest,
        }, artifacts
    if operation == "organize_answer":
        if not isinstance(payload.get("input"), dict):
            raise AgentRequestError(
                "ORGANIZED_ANSWER_INPUT_REQUIRED",
                "organize_answer 必须提供 input.operation + input.payload，由当前确定性引擎复算后组织答案。",
            )
        (
            deterministic,
            source_artifacts,
            _source_operation,
            _source_input,
        ) = _hybrid_deterministic_input(
            payload,
            api,
            allow_aspen_import=False,
        )
        organized_answer = result_presentation.build_organized_answer(
            deterministic
        )
        output_format = str(
            payload.get("format", "markdown")
        ).strip().lower()
        if output_format == "md":
            output_format = "markdown"
        if output_format not in {"markdown", "json"}:
            raise AgentRequestError(
                "ORGANIZED_ANSWER_FORMAT_INVALID",
                "organize_answer format 只能是 markdown/md 或 json。",
            )
        output_value = str(
            payload.get("output_path", "")
        ).strip()
        artifacts = list(source_artifacts)
        output_path: Path | None = None
        if output_value:
            output_path = Path(output_value).expanduser().resolve()
            if output_format == "markdown":
                atomic_write_text(
                    output_path,
                    result_presentation.render_organized_markdown(
                        organized_answer
                    ),
                )
            else:
                atomic_write_json(
                    output_path,
                    organized_answer,
                    pretty=True,
                )
            artifacts.append(str(output_path))
        return {
            "organized_answer": organized_answer,
            "markdown": (
                result_presentation.render_organized_markdown(
                    organized_answer
                )
                if output_format == "markdown"
                else None
            ),
            "format": output_format,
            "output_path": (
                str(output_path) if output_path is not None else None
            ),
            "output_file_sha256": (
                sha256_file(output_path)
                if output_path is not None
                else None
            ),
        }, artifacts
    if operation == "customer_export":
        if not isinstance(payload.get("input"), dict):
            raise AgentRequestError(
                "CUSTOMER_EXPORT_INPUT_REQUIRED",
                "customer_export 必须提供 input.operation + input.payload，由当前确定性引擎复算后导出。",
            )
        deterministic, source_artifacts, _source_operation, _source_input = _hybrid_deterministic_input(
            payload,
            api,
            allow_aspen_import=False,
        )
        delivery = customer_delivery.build_customer_delivery(deterministic)
        output_value = str(payload.get("output_path", "")).strip()
        artifacts: list[str] = list(source_artifacts)
        output_path: Path | None = None
        if output_value:
            output_path = Path(output_value).expanduser().resolve()
            atomic_write_json(output_path, delivery, pretty=True)
            artifacts.append(str(output_path))
        return {
            "customer_delivery": delivery,
            "output_path": str(output_path) if output_path else None,
        }, artifacts
    if operation == "knowledge_search":
        query = str(payload.get("query", "")).strip()
        if not query:
            raise AgentRequestError("KNOWLEDGE_QUERY_EMPTY", "knowledge_search 需要非空 query。")
        package_ids = payload.get("package_ids")
        if package_ids is not None and (not isinstance(package_ids, list) or not all(isinstance(item, str) for item in package_ids)):
            raise AgentRequestError("KNOWLEDGE_PACKAGES_INVALID", "package_ids 必须是字符串数组。")
        try:
            return app_core.knowledge_search(query, limit=int(payload.get("limit", 8)), package_ids=package_ids), []
        except ValueError as exc:
            raise AgentRequestError("KNOWLEDGE_PACKAGES_INVALID", str(exc)) from exc
    if operation == "aspen_derive":
        path_value = str(payload.get("export_path") or payload.get("input_path") or "").strip()
        if not path_value:
            raise AgentRequestError("ASPEN_EXPORT_PATH_REQUIRED", "aspen_derive 需要 export_path。")
        source_path = Path(path_value).expanduser().resolve()
        if not source_path.is_file():
            raise AgentRequestError("INPUT_FILE_NOT_FOUND", f"Aspen 导出文件不存在：{source_path}")
        expected_hash = str(payload.get("export_sha256", "")).strip().upper()
        actual_hash = sha256_file(source_path)
        if expected_hash and expected_hash != actual_hash:
            raise AgentOperationError(
                "ASPEN_EXPORT_HASH_MISMATCH",
                "Aspen 导出文件哈希不一致。",
                {"expected": expected_hash, "actual": actual_hash, "path": str(source_path)},
                exit_code=6,
            )
        bundle = load_json_file(source_path)
        if not isinstance(bundle, dict):
            raise AgentRequestError("INPUT_NOT_OBJECT", "Aspen 导出文件顶层必须是 JSON 对象。")
        import aspen_equipment_derivation

        derived = aspen_equipment_derivation.derive_bundle(bundle, source_path)
        output_value = str(payload.get("output_path", "")).strip()
        artifacts: list[str] = []
        if output_value:
            output_path = Path(output_value).expanduser().resolve()
            atomic_write_json(output_path, derived, pretty=True)
            artifacts.append(str(output_path))
        if bool(payload.get("require_clean")) and derived.get("formal_use_gate") != "ELIGIBLE_AS_PROCESS_BASIS":
            raise AgentOperationError(
                "ASPEN_CLEAN_GATE_NOT_MET",
                "Aspen 导出推导完成，但正式流程基础门未闭合。",
                derived,
                exit_code=4,
            )
        return derived, artifacts
    if operation == "aspen_import":
        import_payload = dict(payload)
        import_payload.setdefault("run", False)
        response = api.import_aspen(import_payload)
        artifacts = [str(response["session_dir"])] if response.get("session_dir") else []
        if not response.get("ok"):
            error_text = str(response.get("error", "Aspen 导入失败。"))
            dependency = any(word in error_text.casefold() for word in ("com", "license", "许可证", "dispatch"))
            raise AgentOperationError(
                "ASPEN_IMPORT_FAILED",
                error_text,
                response,
                exit_code=5 if dependency else 3,
            )
        return response.get("value"), artifacts
    if operation == "pfd_build":
        source_path, bundle, source_hash = _pfd_bundle_from_payload(payload)
        overrides = _pfd_overrides(payload)
        output_path = _pfd_output_path(payload, source_path)
        try:
            _derived, canonical_blocks, canonical_streams, normalization_issues = _pfd_derivation_context(bundle, source_path)
            mapping = aspen_pfd.build_pfd_mapping(
                bundle,
                overrides,
                canonical_parameters_by_block=canonical_blocks,
                canonical_parameters_by_stream=canonical_streams,
                parameter_normalization_issues=normalization_issues,
            )
        except aspen_pfd.AspenPFDMappingError as exc:
            raise AgentRequestError(exc.code, exc.message, exc.details) from exc
        return _pfd_operation_result(
            action="BUILD_PFD_MAPPING",
            source_path=source_path,
            source_hash=source_hash,
            mapping=mapping,
            output_path=output_path,
        )
    if operation == "pfd_override":
        source_path, bundle, source_hash = _pfd_bundle_from_payload(payload)
        overrides = _pfd_overrides(payload)
        block_id = str(payload.get("block_id", "")).strip()
        if not block_id:
            raise AgentRequestError("PFD_OVERRIDE_BLOCK_REQUIRED", "pfd_override 需要 block_id。")
        if "selection_id" not in payload or not isinstance(payload.get("selection_id"), str):
            raise AgentRequestError(
                "PFD_OVERRIDE_SELECTION_REQUIRED",
                "pfd_override 需要 selection_id；恢复自动使用 AUTO。",
            )
        selection_text = str(payload["selection_id"]).strip()
        if not selection_text:
            raise AgentRequestError(
                "PFD_OVERRIDE_SELECTION_REQUIRED",
                "selection_id 不能为空；恢复自动使用 AUTO。",
            )
        output_path = _pfd_output_path(payload, source_path)
        try:
            _derived, canonical_blocks, canonical_streams, normalization_issues = _pfd_derivation_context(bundle, source_path)
            updated = aspen_pfd.update_type_override(
                bundle,
                overrides,
                block_id,
                None if selection_text.upper() in {"AUTO", "AUTOMATIC", "RESTORE_AUTO"} else selection_text,
                canonical_parameters_by_block=canonical_blocks,
                canonical_parameters_by_stream=canonical_streams,
                parameter_normalization_issues=normalization_issues,
            )
        except aspen_pfd.AspenPFDMappingError as exc:
            raise AgentRequestError(exc.code, exc.message, exc.details) from exc
        return _pfd_operation_result(
            action=str(updated.get("action", "APPLY_USER_TYPE_OVERRIDE")),
            source_path=source_path,
            source_hash=source_hash,
            mapping=updated["mapping"],
            output_path=output_path,
        )
    if operation == "pfd_recalculate":
        source_path, bundle, source_hash = _pfd_bundle_from_payload(payload)
        type_overrides = _pfd_overrides(payload)
        parameter_state = _pfd_parameter_state(payload, bundle)
        block_id = str(payload.get("block_id", "")).strip()
        if not block_id:
            raise AgentRequestError("PFD_PARAMETER_BLOCK_REQUIRED", "pfd_recalculate 需要 block_id。")
        clear = payload.get("clear", False)
        if not isinstance(clear, bool):
            raise AgentRequestError("PFD_PARAMETER_CLEAR_INVALID", "clear 必须是布尔值。")
        values = payload.get("values", {})
        if not isinstance(values, Mapping):
            raise AgentRequestError("INVALID_PARAMETER_OVERRIDE_VALUES", "values 必须是 field -> scalar 对象。")
        output_path = _pfd_output_path(payload, source_path)
        try:
            derived, canonical_blocks, canonical_streams, normalization_issues = _pfd_derivation_context(bundle, source_path)
            updated = aspen_pfd.update_parameter_override(
                bundle,
                type_overrides,
                parameter_state,
                block_id,
                values,
                clear=clear,
                canonical_parameters_by_block=canonical_blocks,
                canonical_parameters_by_stream=canonical_streams,
                parameter_normalization_issues=normalization_issues,
            )
        except aspen_pfd.AspenPFDMappingError as exc:
            raise AgentRequestError(exc.code, exc.message, exc.details) from exc

        mapping = updated["mapping"]
        block_row = next(
            (
                row for row in mapping.get("blocks", [])
                if isinstance(row, Mapping) and str(row.get("block_id")) == block_id
            ),
            {},
        )
        effective = block_row.get("effective_mapping") if isinstance(block_row.get("effective_mapping"), Mapping) else {}
        selection_id = str(effective.get("selection_id") or "").strip() or None

        equipment_rows = derived.get("equipment") if isinstance(derived.get("equipment"), list) else []
        equipment = next(
            (
                row for row in equipment_rows
                if isinstance(row, Mapping)
                and str(row.get("aspen_block_id") or row.get("equipment_tag")) == block_id
            ),
            {},
        )
        base_input = (
            dict(equipment.get("canonical_match_input"))
            if isinstance(equipment.get("canonical_match_input"), Mapping)
            else {}
        )
        effective_values = updated.get("effective_values") if isinstance(updated.get("effective_values"), Mapping) else {}
        if selection_id:
            catalog_selection = next(
                (
                    item for item in app_core.load_catalog().get("selections", [])
                    if isinstance(item, Mapping) and item.get("selection_id") == selection_id
                ),
                {},
            )
            allowed_fields = {
                str(field.get("name"))
                for field in catalog_selection.get("fields", [])
                if isinstance(field, Mapping) and field.get("name")
            }
            unknown_fields = sorted(set(effective_values) - allowed_fields)
            if unknown_fields:
                raise AgentRequestError(
                    "PFD_PARAMETER_FIELDS_NOT_IN_SELECTION",
                    "补录字段不属于当前设备类型；请更改类型或清空旧补录后重试。",
                    {"block_id": block_id, "selection_id": selection_id, "fields": unknown_fields},
                )
        try:
            merged_input = aspen_pfd.merge_canonical_input_with_parameter_overrides(
                block_id,
                base_input,
                effective_values,
            )
        except aspen_pfd.AspenPFDMappingError as exc:
            raise AgentRequestError(exc.code, exc.message, exc.details) from exc

        deterministic: Mapping[str, Any] | None = None
        if selection_id and base_input:
            response = api.manual_match(selection_id, merged_input)
            if not response.get("ok") or not isinstance(response.get("value"), Mapping):
                raise AgentOperationError(
                    "PFD_DETERMINISTIC_RECALCULATION_FAILED",
                    str(response.get("error", f"{block_id} 确定性重算失败。")),
                    {"block_id": block_id, "selection_id": selection_id},
                    exit_code=3,
                )
            deterministic = dict(response["value"])
            updated = dict(updated)
            updated["mapping"] = aspen_pfd.mark_block_recalculated(mapping, block_id)
            updated["change_impact"] = updated["mapping"].get("change_impact", {})

        return _pfd_recalculation_operation_result(
            source_path=source_path,
            source_hash=source_hash,
            output_path=output_path,
            updated=updated,
            selection_id=selection_id,
            base_input=base_input,
            merged_input=merged_input,
            deterministic_recalculation=deterministic,
        )
    if operation == "hybrid_prepare":
        deterministic, artifacts, source_operation, source_input = _hybrid_deterministic_input(
            payload,
            api,
            allow_aspen_import=False,
        )
        knowledge, injection_point, context_scope = _hybrid_options(payload)
        response = api.hybrid_prepare(
            deterministic,
            knowledge,
            injection_point,
            context_scope,
        )
        if not response.get("ok"):
            raise AgentOperationError("HYBRID_PREPARE_FAILED", str(response.get("error", "混合上下文准备失败。")))
        replay = _replay_contract(
            source_input,
            knowledge,
            injection_point,
            context_scope,
            deterministic,
        )
        value = llm_bridge.with_replay_contract(response["value"], replay)
        return value, artifacts
    if operation == "hybrid_continue":
        prepared = _object_from_payload(payload, "prepared", "prepared_path")
        step_output = _object_from_payload(payload, "step_output", "step_output_path")
        rebuilt_prepared = _rebuild_prepared_from_replay(prepared, api)
        response = api.hybrid_continue(rebuilt_prepared, step_output)
        if not response.get("ok"):
            raise AgentOperationError("HYBRID_CONTINUE_FAILED", str(response.get("error", "外部 Agent 回包校验失败。")))
        return response["value"], []
    if operation == "hybrid_run":
        deterministic, artifacts, source_operation, source_input = _hybrid_deterministic_input(payload, api)
        knowledge, injection_point, context_scope = _hybrid_options(payload)
        llm = payload.get("llm", {})
        if not isinstance(llm, dict):
            raise AgentRequestError("HYBRID_LLM_INVALID", "hybrid llm 必须是对象。")
        llm_enabled = bool(llm.get("enabled", False))
        raw_config = llm.get("config", {})
        if not isinstance(raw_config, dict):
            raise AgentRequestError("LLM_CONFIG_INVALID", "llm.config 必须是对象。")
        if "api_key" in raw_config:
            raise AgentRequestError(
                "API_KEY_LITERAL_FORBIDDEN",
                "请求 JSON 不得保存 API Key；请使用固定的人类配置环境变量。",
            )
        config: dict[str, Any] = {"enabled": False}
        config_failure: dict[str, Any] | None = None
        if llm_enabled:
            try:
                config = _agent_provider_config(raw_config)
                config["enabled"] = True
            except AgentRequestError as exc:
                if exc.code in {
                    "API_KEY_LITERAL_FORBIDDEN",
                    "API_KEY_ENV_NOT_ALLOWLISTED",
                    "LLM_BASE_URL_LITERAL_FORBIDDEN",
                }:
                    raise
                config_failure = {"code": exc.code, "message": str(exc), "details": exc.details}
        prepared_response = api.hybrid_prepare(
            deterministic,
            knowledge,
            injection_point,
            context_scope,
        )
        if not prepared_response.get("ok"):
            raise AgentOperationError("HYBRID_PREPARE_FAILED", str(prepared_response.get("error", "混合上下文准备失败。")))
        replay = _replay_contract(
            source_input,
            knowledge,
            injection_point,
            context_scope,
            deterministic,
        )
        prepared = llm_bridge.with_replay_contract(prepared_response["value"], replay)
        knowledge_context = prepared_response.get("knowledge_context")
        knowledge_requested = bool(knowledge.get("enabled", False) or knowledge.get("result") is not None)
        base_steps = [
            {"id": "deterministic_result", "status": "COMPLETED", "authoritative": True},
            {"id": "hybrid_prepare", "status": "COMPLETED", "authoritative": False},
        ]
        if not llm_enabled:
            return _hybrid_result_envelope(
                state="COMPLETED_DETERMINISTIC_ONLY",
                deterministic_result=deterministic,
                prepared=prepared,
                knowledge_context=knowledge_context,
                source_operation=source_operation,
                llm_requested=False,
                knowledge_requested=knowledge_requested,
                steps=base_steps + [{"id": "llm_review", "status": "NOT_REQUESTED", "authoritative": False}],
            ), artifacts
        if config_failure is not None:
            return _hybrid_result_envelope(
                state="FALLBACK_DETERMINISTIC",
                deterministic_result=deterministic,
                prepared=prepared,
                knowledge_context=knowledge_context,
                source_operation=source_operation,
                llm_requested=True,
                knowledge_requested=knowledge_requested,
                errors=[config_failure],
                steps=base_steps + [{"id": "provider_config", "status": "FAILED_FALLBACK", "authoritative": False}],
            ), artifacts
        response = api.hybrid_run(config, prepared)
        if not response.get("ok"):
            return _hybrid_result_envelope(
                state="FALLBACK_DETERMINISTIC",
                deterministic_result=deterministic,
                prepared=prepared,
                knowledge_context=knowledge_context,
                source_operation=source_operation,
                llm_requested=True,
                knowledge_requested=knowledge_requested,
                errors=[{"code": "LLM_ORCHESTRATION_FAILED", "message": str(response.get("error", "混合编排失败。"))}],
                steps=base_steps + [{"id": "provider_or_validation", "status": "FAILED_FALLBACK", "authoritative": False}],
            ), artifacts
        orchestration = response["value"]
        verified_inputs = orchestration.get("verified_calculation_inputs", {})
        if not isinstance(verified_inputs, dict):
            verified_inputs = {}
        verified_model_estimate_inputs = orchestration.get("verified_model_estimate_inputs", {})
        if not isinstance(verified_model_estimate_inputs, dict):
            verified_model_estimate_inputs = {}
        verified_model_estimate_lineage = orchestration.get("verified_model_estimate_lineage", {})
        if not isinstance(verified_model_estimate_lineage, dict):
            verified_model_estimate_lineage = {}
        verified_terminal_overrides = orchestration.get("verified_terminal_selection_overrides", {})
        if not isinstance(verified_terminal_overrides, dict):
            verified_terminal_overrides = {}
        recalculation, recalculation_artifacts, assist_application, terminal_selection_application = (
            _auto_apply_verified_hybrid_updates(
                source_operation,
                source_input,
                verified_inputs,
                verified_model_estimate_inputs,
                verified_model_estimate_lineage,
                verified_terminal_overrides,
                api,
            )
        )
        artifacts.extend(recalculation_artifacts)
        return _hybrid_result_envelope(
            state=(
                "COMPLETED_HYBRID_RECALCULATED"
                if recalculation is not None
                else "COMPLETED_HYBRID"
            ),
            deterministic_result=deterministic,
            prepared=prepared,
            knowledge_context=knowledge_context,
            source_operation=source_operation,
            llm_requested=True,
            knowledge_requested=knowledge_requested,
            orchestration=orchestration,
            deterministic_recalculation=recalculation,
            calculation_assist_application=assist_application,
            terminal_selection_application=terminal_selection_application,
            steps=base_steps + [
                {"id": "provider", "status": "COMPLETED", "authoritative": False},
                {"id": "hybrid_continue", "status": "COMPLETED", "authoritative": False},
                {
                    "id": "verified_calculation_replay",
                    "status": "COMPLETED" if recalculation is not None else assist_application["status"],
                    "authoritative": True,
                },
            ],
        ), artifacts
    if operation == "llm_review":
        if payload.get("policy", {}).get("llm_allowed") is False:
            raise AgentRequestError("LLM_DISABLED_BY_POLICY", "当前请求明确禁用 LLM。")
        deterministic, artifacts, _source_operation, source_input = _hybrid_deterministic_input(
            payload,
            api,
            allow_aspen_import=False,
        )
        config = _agent_provider_config(payload.get("config", {}))
        knowledge, injection_point, context_scope = _hybrid_options(payload)
        prepared_response = api.hybrid_prepare(
            deterministic,
            knowledge,
            injection_point,
            context_scope,
        )
        if not prepared_response.get("ok"):
            raise AgentOperationError(
                "HYBRID_PREPARE_FAILED",
                str(prepared_response.get("error", "LLM 审核上下文准备失败。")),
            )
        replay = _replay_contract(
            source_input,
            knowledge,
            injection_point,
            context_scope,
            deterministic,
        )
        prepared = llm_bridge.with_replay_contract(prepared_response["value"], replay)
        response = api.hybrid_run(config, prepared)
        if not response.get("ok"):
            raise AgentOperationError("LLM_REVIEW_FAILED", str(response.get("error", "LLM 审核失败。")))
        return response["value"], artifacts
    if operation == "llm_apply":
        approval = payload.get("approval")
        if not isinstance(approval, dict) or approval.get("approved") is not True:
            raise AgentRequestError("EXPLICIT_APPROVAL_REQUIRED", "llm_apply 必须包含 approval.approved=true。")
        approved_ids = approval.get("approved_change_ids")
        if not isinstance(approved_ids, list) or not all(isinstance(item, str) for item in approved_ids):
            raise AgentRequestError("APPROVED_CHANGE_IDS_REQUIRED", "approval.approved_change_ids 必须是字符串数组。")
        approved_by = str(approval.get("approved_by", "")).strip()
        if not approved_by:
            raise AgentRequestError("APPROVER_REQUIRED", "approval.approved_by 不能为空。")
        proposal = _object_from_payload(payload, "proposal", "proposal_path")
        if proposal.get("schema") == "equipment-design-hybrid-result-v2" and isinstance(proposal.get("orchestration"), dict):
            proposal = proposal["orchestration"]
        if proposal.get("schema") != llm_bridge.ORCHESTRATION_SCHEMA:
            raise AgentRequestError(
                "STRICT_ORCHESTRATION_REQUIRED",
                "llm_apply 只接受 hybrid_continue/hybrid_run 生成的严格 orchestration；裸 legacy proposal 已禁用。",
            )
        _require_current_authority_revision(
            proposal.get("authority_revision"),
            "orchestration",
        )
        approval_context = str(approval.get("context_sha256", "")).strip().upper()
        expected_context = str(proposal.get("context_sha256", "")).strip().upper()
        if not approval_context or approval_context != expected_context:
            raise AgentRequestError(
                "APPROVAL_CONTEXT_HASH_MISMATCH",
                "编排结果批准必须携带与 proposal 一致的 approval.context_sha256。",
                {"expected": expected_context, "actual": approval_context or None},
            )
        approval_orchestration = str(approval.get("orchestration_sha256", "")).strip().upper()
        expected_orchestration = str(proposal.get("orchestration_sha256", "")).strip().upper()
        if not approval_orchestration or approval_orchestration != expected_orchestration:
            raise AgentRequestError(
                "APPROVAL_ORCHESTRATION_HASH_MISMATCH",
                "批准记录必须绑定严格 orchestration_sha256。",
                {"expected": expected_orchestration or None, "actual": approval_orchestration or None},
            )
        rebuilt_prepared, original_result, source_input, source_operation = _build_prepared_from_replay_contract(
            proposal.get("replay_contract"),
            api,
        )
        if rebuilt_prepared.get("prepared_sha256") != proposal.get("prepared_sha256"):
            raise AgentOperationError(
                "LLM_APPLY_PREPARED_REPLAY_MISMATCH",
                "应用前重放的 prepared 与审核时 prepared 不一致。",
                {
                    "expected": proposal.get("prepared_sha256"),
                    "actual": rebuilt_prepared.get("prepared_sha256"),
                },
            )
        revalidated = llm_bridge.hybrid_continue(rebuilt_prepared, proposal.get("step_output"))
        if revalidated.get("orchestration_sha256") != expected_orchestration:
            raise AgentOperationError(
                "LLM_ORCHESTRATION_TAMPERED",
                "严格 step output 重校验结果与提交的 orchestration 哈希不一致。",
                {
                    "expected": expected_orchestration,
                    "actual": revalidated.get("orchestration_sha256"),
                },
            )
        proposal = revalidated
        candidate_reference = proposal.get("candidate_reference")
        has_candidate_reference = (
            isinstance(candidate_reference, dict)
            and candidate_reference.get("status") == "candidate_reference"
        )
        verified_calculation_inputs = proposal.get("verified_calculation_inputs", {})
        if not isinstance(verified_calculation_inputs, dict):
            verified_calculation_inputs = {}
        if not approved_ids and not has_candidate_reference and not verified_calculation_inputs:
            raise AgentRequestError(
                "APPROVED_CHANGE_IDS_REQUIRED",
                "没有受控候选引用时，approval.approved_change_ids 必须是非空字符串数组。",
            )
        validated = proposal["validated_proposal"]
        accepted_by_id = {item["change_id"]: item for item in validated.get("accepted_changes", [])}
        unknown_ids = sorted(set(approved_ids) - set(accepted_by_id))
        if unknown_ids:
            raise AgentRequestError("UNKNOWN_APPROVED_CHANGE_ID", "批准记录包含不存在或已被拒绝的 change ID。", {"unknown_ids": unknown_ids})
        approved_set = set(approved_ids)
        approved_validation = dict(validated)
        approved_validation["accepted_changes"] = [
            item for item in validated.get("accepted_changes", []) if item["change_id"] in approved_set
        ]
        source_payload = source_input.get("payload")
        if not isinstance(source_payload, dict):
            raise AgentOperationError("LLM_REPLAY_SOURCE_INVALID", "replay source payload 无效。")
        replay_payload = json.loads(json.dumps(source_payload, ensure_ascii=False))
        current: dict[str, Any]
        if source_operation == "manual_match":
            current = replay_payload.get("values")
            if not isinstance(current, dict):
                raise AgentOperationError("LLM_REPLAY_SOURCE_INVALID", "manual_match replay 缺少 values。")
            draft = llm_bridge.apply_proposal(current, approved_validation)
            for field, value in verified_calculation_inputs.items():
                if field not in draft or draft.get(field) in (None, ""):
                    draft[field] = value
            replay_payload["values"] = draft
        elif source_operation == "auto_match" and isinstance(replay_payload.get("values"), dict):
            current = replay_payload["values"]
            draft = llm_bridge.apply_proposal(current, approved_validation)
            for field, value in verified_calculation_inputs.items():
                if field not in draft or draft.get(field) in (None, ""):
                    draft[field] = value
            replay_payload["values"] = draft
        else:
            if approved_validation.get("accepted_changes") or verified_calculation_inputs:
                raise AgentRequestError(
                    "LLM_SOURCE_NOT_PATCHABLE",
                    f"{source_operation} 不能自动注入描述字段；请保留审核记录或重建可重放单设备输入。",
                )
            current = {}
            draft = {}
        changed_hard_fields = [
            field for field in llm_bridge.HARD_PARAMETER_FIELDS
            if field in current and draft.get(field) != current.get(field)
        ]
        if changed_hard_fields:
            raise AgentOperationError(
                "LLM_HARD_PARAMETER_MUTATION",
                "LLM 草案改变了硬参数，已拒绝。",
                {"fields": sorted(changed_hard_fields)},
            )
        recalculation, recalculation_artifacts = _execute(source_operation, replay_payload, api)
        candidate_validation: dict[str, Any] | None = None
        if isinstance(candidate_reference, dict) and candidate_reference.get("status") == "candidate_reference":
            registry = {
                item["candidate_id"]: item
                for item in llm_bridge.candidate_registry(recalculation)
            }
            candidate_id = str(candidate_reference.get("selected_candidate_id", "")).strip()
            actual_record = registry.get(candidate_id)
            actual = None if actual_record is None else {
                key: actual_record.get(key)
                for key in (
                    "candidate_id", "designation",
                    "selection_feature_vector_sha256", "selection_context_sha256",
                )
            }
            expected = {
                "candidate_id": candidate_id,
                "designation": candidate_reference.get("selected_designation"),
                "selection_feature_vector_sha256": candidate_reference.get("selection_feature_vector_sha256"),
                "selection_context_sha256": candidate_reference.get("selection_context_sha256"),
            }
            if actual != expected:
                raise AgentOperationError(
                    "CANDIDATE_CONTEXT_CHANGED",
                    "确定性复算后的候选身份或 feature/context hash 已变化；候选引用不再有效。",
                    {"expected": expected, "actual": actual},
                )
            candidate_validation = {"status": "PASS_EXACT_DETERMINISTIC_REFERENCE", **expected}
        execution_timeline = llm_bridge.materialize_recalculation_timeline(
            proposal["execution_timeline"],
            recalculation,
        )
        return {
            "validation": validated,
            "approval": {
                "approved": True,
                "approved_change_ids": sorted(approved_set),
                "approved_by": approved_by,
                "context_sha256": proposal.get("context_sha256"),
                "orchestration_sha256": proposal.get("orchestration_sha256"),
            },
            "applied_draft": draft,
            "replayed_source_operation": source_operation,
            "original_deterministic_result": original_result,
            "ai_operations": [
                step for step in execution_timeline.get("steps", [])
                if isinstance(step, dict) and step.get("actor") == "ai"
            ],
            "deterministic_recalculation": recalculation,
            "execution_timeline": execution_timeline,
            "candidate_reference_validation": candidate_validation,
        }, recalculation_artifacts
    if operation == "selftest":
        bundle = app_core.require_runtime_bundle()
        rules = app_core.matcher.load_json(app_core.matcher.RULES_PATH)
        graph = app_core.matcher.load_graph()
        rule_check = app_core.matcher.validate_rules(rules, graph)
        partial = app_core.auto_match({"flow_m3_h": 20})
        pump = app_core.manual_match("block:PUMP", {
            "pressure_basis": "absolute",
            "phase": "liquid",
            "flow_m3_h": 20,
            "inlet_pressure_mpa": 0.2,
            "outlet_pressure_mpa": 0.6,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        })
        invalid_phase = app_core.manual_match("block:PUMP", {
            "phase": "banana",
            "flow_m3_h": 20,
        })
        large_pump = app_core.manual_match("block:PUMP", {
            "equipment_tag": "P-SELFTEST-LARGE",
            "phase": "liquid",
            "flow_m3_h": 4000,
            "density_kg_m3": 1000,
            "head_m": 60,
        })
        organized_large_pump = (
            result_presentation.build_organized_answer(
                large_pump
            )
        )
        pfd_mapping = aspen_pfd.build_pfd_mapping({
            "schema": "aspen-equipment-export-v1",
            "case": {
                "case_id": "SELFTEST-PFD",
                "pressure_basis": "absolute",
                "run_status": {
                    "terminal_errors": 0,
                    "severe_errors": 0,
                    "errors": 0,
                    "warnings": 0,
                },
            },
            "streams": [
                {"stream_id": "S-IN", "phase": "liquid", "pressure_bar": 1.0},
                {"stream_id": "S-OUT", "phase": "liquid", "pressure_bar": 4.0},
            ],
            "blocks": [{
                "block_id": "P-SELFTEST",
                "block_type": "PUMP",
                "inlet_streams": ["S-IN"],
                "outlet_streams": ["S-OUT"],
                "HEAD_CAL": 30.0,
            }],
        })
        pfd_summary = aspen_pfd.summarize_pfd_mapping(pfd_mapping)
        no_llm_hybrid, _ = _execute("hybrid_run", {
            "input": {
                "operation": "manual_match",
                "payload": {
                    "selection_id": "block:PUMP",
                    "values": {
                        "pressure_basis": "absolute",
                        "phase": "liquid",
                        "flow_m3_h": 20,
                        "inlet_pressure_mpa": 0.2,
                        "outlet_pressure_mpa": 0.6,
                        "density_kg_m3": 900,
                        "efficiency_percent": 75,
                    },
                },
            },
            "knowledge": {"enabled": False},
            "injection_point": "audit",
            "context_scope": "minimum",
            "llm": {"enabled": False},
        }, api)
        schema_ids = {item["schema_id"] for item in _schema_catalog()}
        family_type_results = [
            app_core.auto_match({"equipment_family": item["id"]})["result"]
            for item in rules.get("families", [])
        ]
        family_fixture = load_json_file(APP_DIR / "fixtures" / "all_family_minimum_meaningful_inputs.json")
        family_acceptance_rows = []
        for case in family_fixture.get("cases", []):
            result = app_core.auto_match({
                "equipment_family": case["family_id"],
                **case.get("values", {}),
            })["result"]
            calculation_ids = [item.get("calculation_id") for item in result.get("calculations", [])]
            recommendation = result.get("model_recommendation", {})
            leading = recommendation.get("leading_candidate") or {}
            selection_execution_status = recommendation.get(
                "selection_execution", {}
            ).get("status")
            candidate_generation_executed = selection_execution_status in {
                "EXECUTED",
                "EXECUTED_TYPE_SCREENING_ONLY",
            }
            family_acceptance_rows.append({
                "family_id": case["family_id"],
                "calculation_ids": calculation_ids,
                "expected_calculation_ids": case.get("expected_calculation_ids", []),
                "parameter_package_status": result.get("design_parameter_package", {}).get("status"),
                "selection_execution_status": selection_execution_status,
                "minimum_candidate_missing_fields": recommendation.get("minimum_candidate_missing_fields", []),
                "candidate_kind": leading.get("candidate_kind"),
                "expected_candidate_kind": case.get("expected_candidate_kind"),
                "candidate_designation": leading.get("designation"),
                "recommended_type": leading.get("recommended_type"),
                "expected_recommended_type": case.get("expected_recommended_type"),
                "type_name_quality": leading.get("type_name_quality"),
                "generated_candidate_model": result.get("model_decision", {}).get("generated_candidate_model"),
                "pass": (
                    calculation_ids == case.get("expected_calculation_ids", [])
                    and result.get("design_parameter_package", {}).get("status") == "READY_FOR_CANDIDATE_MATCHING"
                    and candidate_generation_executed
                    and not recommendation.get("minimum_candidate_missing_fields", [])
                    and leading.get("candidate_kind") == case.get("expected_candidate_kind")
                    and leading.get("recommended_type") == case.get("expected_recommended_type")
                    and leading.get("candidate_kind") != "generic_type_placeholder"
                    and leading.get("type_name_quality", {}).get("is_concrete") is True
                    and bool(leading.get("designation"))
                ),
            })
        customer_bundle = pump["result"].get("customer_delivery", {})
        customer_overview = customer_bundle.get("equipment_overview_table", {})
        customer_datasheet = customer_bundle.get("equipment_family_datasheet", {})
        customer_evidence = customer_bundle.get("equipment_evidence_index", {})
        customer_rows = customer_overview.get("rows", [])
        customer_equipment = customer_datasheet.get("equipment", [])
        customer_fields = customer_equipment[0].get("fields", []) if customer_equipment else []
        customer_field_ids = {
            item.get("field_id") for item in customer_fields if isinstance(item, dict)
        }
        checks = [
            {
                "id": "runtime_asset_manifest",
                "pass": bundle.get("verified") is True,
                "detail": {
                    "verification_status": bundle.get("verification_status"),
                    "bundle_revision": bundle.get("bundle_revision"),
                    "manifest_sha256": bundle.get("manifest_sha256"),
                    "issues": bundle.get("issues", []),
                },
            },
            {"id": "rules_and_graph", "pass": rule_check.get("status") == "PASS", "detail": rule_check},
            {
                "id": "partial_input_candidate_generation",
                "pass": bool(partial.get("progress", {}).get("candidate_count")),
                "detail": partial.get("progress", {}).get("state"),
            },
            {
                "id": "pump_formula_chain",
                "pass": len(pump["result"].get("calculations", [])) == 3,
                "detail": [item.get("calculation_id") for item in pump["result"].get("calculations", [])],
            },
            {
                "id": "all_family_catalog_and_concrete_type_coverage",
                "pass": len(family_type_results) == 17 and all(
                    item.get("model_recommendation", {}).get("candidate_count", 0) >= 1
                    and item.get("model_decision", {}).get("generated_candidate_designation")
                    and item.get("model_recommendation", {}).get("leading_candidate", {}).get("candidate_kind")
                    != "generic_type_placeholder"
                    and item.get("model_recommendation", {}).get("leading_candidate", {}).get(
                        "type_name_quality", {}
                    ).get("is_concrete") is True
                    for item in family_type_results
                ),
                "detail": {
                    "claim_boundary": "family-only input proves a concrete deterministic engineering type is always available; it does not prove calculation readiness or a formal vendor model",
                    "family_count": len(family_type_results),
                    "covered": sum(
                        1 for item in family_type_results
                        if item.get("model_recommendation", {}).get("candidate_count", 0) >= 1
                    ),
                },
            },
            {
                "id": "all_family_parameter_package_coverage",
                "pass": len(family_type_results) == 17 and all(
                    item.get("design_parameter_package", {}).get("schema") == "equipment-design-parameter-package-v1"
                    and item.get("design_parameter_package", {}).get("groups")
                    for item in family_type_results
                ),
                "detail": {
                    "family_count": len(family_type_results),
                    "covered": sum(
                        1 for item in family_type_results
                        if item.get("design_parameter_package", {}).get("groups")
                    ),
                },
            },
            {
                "id": "all_family_minimum_meaningful_calculate_then_select",
                "pass": (
                    len(family_acceptance_rows) == family_fixture.get("expected_family_count") == 17
                    and sum(len(item["calculation_ids"]) for item in family_acceptance_rows)
                    == family_fixture.get("expected_total_calculation_count")
                    and all(item["pass"] for item in family_acceptance_rows)
                ),
                "detail": {
                    "fixture_schema": family_fixture.get("schema"),
                    "family_count": len(family_acceptance_rows),
                    "calculation_count": sum(len(item["calculation_ids"]) for item in family_acceptance_rows),
                    "standard_reference_family_count": sum(
                        1 for item in family_acceptance_rows if item["candidate_kind"] == "standard_marking"
                    ),
                    "engineered_designation_family_count": sum(
                        1 for item in family_acceptance_rows if item["candidate_kind"] == "engineered_designation"
                    ),
                    "component_marking_family_count": sum(
                        1 for item in family_acceptance_rows if item["candidate_kind"] == "component_marking"
                    ),
                    "non_concrete_type_family_count": sum(
                        1 for item in family_acceptance_rows
                        if item.get("type_name_quality", {}).get("is_concrete") is not True
                    ),
                    "rows": family_acceptance_rows,
                    "claim_boundary": "The pump uses a bundled GB/T reference-point catalog. Other families return concrete deterministic engineering types or component specifications, while standard/vendor/formal-model promotion remains blocked until same-equipment evidence is supplied.",
                },
            },
            {
                "id": "calculate_before_select_contract",
                "pass": (
                    {"head_m", "hydraulic_power_kw", "shaft_power_kw"}
                    <= set(pump["result"].get("derived_parameters", {}))
                    and pump["result"].get("model_recommendation", {}).get("selection_execution", {}).get("context_sha256")
                    == pump["result"].get("design_parameter_package", {}).get("selection_context", {}).get("sha256")
                ),
                "detail": pump["result"].get("model_recommendation", {}).get("selection_execution"),
            },
            {
                "id": "structured_formula_chains",
                "pass": all(
                    item.get("target_field") and item.get("formula_chain", {}).get("dependencies") is not None
                    for item in pump["result"].get("calculations", [])
                ),
                "detail": [item.get("target_field") for item in pump["result"].get("calculations", [])],
            },
            {
                "id": "pump_standard_marking_candidate",
                "pass": pump["result"].get("model_recommendation", {}).get("leading_candidate", {}).get("standard_marking") == "65-40-200",
                "detail": pump["result"].get("model_decision", {}).get("generated_candidate_model"),
            },
            {
                "id": "algorithmic_modification_and_organized_answer",
                "pass": (
                    large_pump["result"].get(
                        "engineering_adjustment_plan", {}
                    ).get("configuration", {}).get(
                        "parallel_train_count_estimate"
                    )
                    == 2
                    and "轴流泵系统"
                    in str(
                        large_pump["result"].get(
                            "engineering_adjustment_plan", {}
                        ).get("configuration", {}).get(
                            "candidate_model_or_designation"
                        )
                    )
                    and organized_large_pump.get("schema")
                    == "equipment-agent-organized-answer-v1"
                    and organized_large_pump.get(
                        "section_order"
                    )
                    == [
                        "结论",
                        "计算",
                        "候选与系统修改方案",
                        "强制警告",
                        "待补证据",
                        "下一步",
                    ]
                ),
                "detail": {
                    "plan": large_pump["result"].get(
                        "engineering_adjustment_plan"
                    ),
                    "organized_answer_sha256": (
                        organized_large_pump.get(
                            "organized_answer_sha256"
                        )
                    ),
                },
            },
            {
                "id": "zero_llm_core",
                "pass": pump["result"].get("llm_used") is False and partial["result"].get("llm_used") is False,
                "detail": "deterministic matcher only",
            },
            {
                "id": "no_llm_hybrid_v2",
                "pass": (
                    no_llm_hybrid.get("schema") == "equipment-design-hybrid-result-v2"
                    and no_llm_hybrid.get("machine_state", {}).get("state") == "COMPLETED_DETERMINISTIC_ONLY"
                    and no_llm_hybrid.get("machine_state", {}).get("deterministic_result_preserved") is True
                    and no_llm_hybrid.get("deterministic_result", {}).get("result", {}).get("llm_used") is False
                ),
                "detail": no_llm_hybrid.get("machine_state"),
            },
            {
                "id": "strict_schema_catalog",
                "pass": {
                    "equipment-design-llm-prepared-v1",
                    "equipment-design-app-llm-orchestration-v1",
                    "equipment-design-hybrid-result-v2",
                    "equipment-design-parameter-package-v1",
                    "equipment-customer-output-profiles-v1",
                    "equipment-customer-delivery-bundle-v1",
                    "equipment-overview-table-v1",
                    "equipment-family-datasheet-v1",
                    "equipment-evidence-index-v1",
                    "equipment-design-pfd-mapping-v1",
                    "equipment-agent-organized-answer-v1",
                } <= schema_ids,
                "detail": sorted(schema_ids),
            },
            {
                "id": "deterministic_pfd_mapping",
                "pass": (
                    pfd_mapping.get("schema") == "equipment-design-pfd-mapping-v1"
                    and pfd_summary.get("equipment_node_count") == 1
                    and pfd_summary.get("edge_count") == 2
                    and pfd_summary.get("topology_gate", {}).get("status") == "PASS"
                    and pfd_summary.get("model_promotion_allowed") is False
                ),
                "detail": pfd_summary,
            },
            {
                "id": "authoritative_customer_delivery",
                "pass": (
                    customer_bundle.get("schema") == "equipment-customer-delivery-bundle-v1"
                    and customer_bundle.get("deterministic") is True
                    and customer_bundle.get("llm_used") is False
                    and customer_overview.get("schema") == "equipment-overview-table-v1"
                    and customer_overview.get("row_count") == 1
                    and bool(customer_rows)
                    and bool(customer_rows[0].get("model_or_specification"))
                    and bool(customer_rows[0].get("model_or_specification_status"))
                    and isinstance(customer_rows[0].get("customer_table_missing_fields"), list)
                    and isinstance(customer_rows[0].get("algorithm_evidence_missing_fields"), list)
                    and isinstance(customer_rows[0].get("missing_information"), list)
                    and customer_datasheet.get("schema") == "equipment-family-datasheet-v1"
                    and customer_datasheet.get("equipment_count") == 1
                    and {"model_designation", "model_status", "pending_evidence", "head_m"}
                    <= customer_field_ids
                    and customer_evidence.get("schema") == "equipment-evidence-index-v1"
                    and int(customer_evidence.get("record_count", 0)) >= 1
                ),
                "detail": {
                    "overview_rows": customer_overview.get("row_count"),
                    "datasheet_fields": len(customer_fields),
                    "evidence_records": customer_evidence.get("record_count"),
                },
            },
            {
                "id": "invalid_phase_blocked",
                "pass": (
                    invalid_phase.get("result", {}).get("status") == "BLOCKED_INVALID_PARAMETERS"
                    and any(
                        item.get("code") == "INVALID_PHASE"
                        for item in invalid_phase.get("result", {}).get("parameter_errors", [])
                    )
                ),
                "detail": invalid_phase.get("result", {}).get("parameter_errors"),
            },
        ]
        status = "PASS" if all(item["pass"] for item in checks) else "FAILED"
        result = {
            "status": status,
            "checks": checks,
            "check_count": len(checks),
            "bundle_revision": bundle.get("bundle_revision"),
            "manifest_sha256": bundle.get("manifest_sha256"),
            "verification_status": bundle.get("verification_status"),
        }
        if status != "PASS":
            raise AgentOperationError("SELFTEST_FAILED", "无界面自检未通过。", result, exit_code=3)
        return result, []
    raise AgentRequestError("UNSUPPORTED_OPERATION", operation)


def execute_operation(
    operation: str,
    payload: dict[str, Any],
    api: EquipmentDesignApi,
) -> tuple[Any, list[str]]:
    """Public in-process bridge used by the GUI.

    Keeping this as a thin wrapper around ``_execute`` guarantees that GUI
    hybrid/apply actions use the same replay, authority-revision, approval and
    candidate validators as file/stdin Agent requests.
    """
    canonical_operation = OPERATION_ALIASES.get(operation, operation)
    if canonical_operation not in CANONICAL_OPERATIONS:
        raise AgentRequestError("UNKNOWN_OPERATION", f"不支持的操作：{operation}。")
    if not isinstance(payload, dict):
        raise AgentRequestError("PAYLOAD_NOT_OBJECT", "payload 必须是对象。")
    extra = sorted(set(payload) - STRICT_OPERATION_PAYLOAD_KEYS.get(canonical_operation, set(payload)))
    if extra:
        raise AgentRequestError(
            "UNEXPECTED_PAYLOAD_FIELDS",
            f"{canonical_operation} 包含未允许字段：{', '.join(extra)}。",
            {"fields": extra},
        )
    return _execute(canonical_operation, payload, api)


def execute_request(request: Any, api: EquipmentDesignApi | None = None) -> tuple[dict[str, Any], int]:
    request_hash = sha256_json(request)
    request_id = str(request.get("request_id", "UNKNOWN")) if isinstance(request, dict) else "UNKNOWN"
    operation = str(request.get("operation", "UNKNOWN")) if isinstance(request, dict) else "UNKNOWN"
    try:
        try:
            app_core.require_runtime_bundle()
        except app_core.runtime_bundle.RuntimeBundleError as exc:
            raise AgentOperationError(
                "RUNTIME_BUNDLE_VERIFICATION_FAILED",
                str(exc),
                app_core.runtime_bundle_verification(),
                exit_code=9,
            ) from exc
        request_id, operation, payload = _validate_request(request)
        result, artifacts = _execute(operation, payload, api or EquipmentDesignApi())
        return _success(request_id, operation, request_hash, result, artifacts), 0
    except AgentRequestError as exc:
        return _failure(request_id, operation, request_hash, exc.code, str(exc), exc.details, 2), 2
    except AgentOperationError as exc:
        return _failure(request_id, operation, request_hash, exc.code, str(exc), exc.details, exc.exit_code), exc.exit_code
    except Exception as exc:
        return _failure(request_id, operation, request_hash, "UNHANDLED_OPERATION_ERROR", str(exc), exit_code=8), 8


def _configure_utf8_stdio() -> None:
    """Keep the stdin/stdout JSON protocol independent of the Windows code page."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def _read_request(path_text: str) -> Any:
    if path_text == "-":
        return json.load(sys.stdin)
    return load_json_file(Path(path_text).expanduser().resolve())


def _write_json(value: Any, path_text: str, pretty: bool) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, sort_keys=True) + "\n"
    if path_text == "-":
        sys.stdout.write(text)
        return
    path = Path(path_text).expanduser().resolve()
    atomic_write_json(path, value, pretty=pretty)


def _run_jsonl_session() -> int:
    """Serve sequential Agent requests without reloading the packaged runtime.

    Each non-blank input line is one complete request object and produces one
    compact response line.  Per-request failures stay in the normal response
    ``exit_code`` field; they do not terminate the session or contaminate the
    next equipment request.  EOF performs a clean shutdown.
    """
    api = EquipmentDesignApi()
    for line_number, raw_line in enumerate(sys.stdin, start=1):
        if line_number == 1 and raw_line.startswith("\ufeff"):
            raw_line = raw_line[1:]
        if not raw_line.strip():
            continue
        try:
            request = json.loads(raw_line)
        except Exception as exc:
            placeholder = {
                "schema": "equipment-design-agent-request-v1",
                "operation": "UNKNOWN",
                "payload": {},
            }
            response = _failure(
                "UNKNOWN",
                "UNKNOWN",
                sha256_json(placeholder),
                "REQUEST_READ_FAILED",
                f"JSONL 第 {line_number} 行无法解析：{exc}",
                {"line_number": line_number},
                2,
            )
        else:
            response, _ = execute_request(request, api)
        sys.stdout.write(
            json.dumps(
                response,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_stdio()
    args_list = list(sys.argv[1:] if argv is None else argv)
    if "--allow-com" in args_list:
        os.environ["EQUIPMENT_BACKEND_ALLOW_COM"] = "1"
    if "--aspen-worker" in args_list:
        index = args_list.index("--aspen-worker")
        import aspen_com_import

        return aspen_com_import.main(args_list[index + 1 :])
    parser = argparse.ArgumentParser(description="Agent-first JSON interface for deterministic equipment design. GUI is not required.")
    parser.add_argument("--request", default="-", help="Request JSON path or - for stdin.")
    parser.add_argument("--output", default="-", help="Response JSON path or - for stdout.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print response JSON.")
    parser.add_argument("--allow-com", action="store_true", help="Explicitly authorize the optional isolated Aspen COM path for this process.")
    parser.add_argument(
        "--session-jsonl",
        "--serve-stdio",
        dest="session_jsonl",
        action="store_true",
        help="Keep one Agent process resident and exchange one request/response JSON object per line.",
    )
    parser.add_argument("--bkp", "--aspen-file", dest="aspen_file", help="Direct Aspen .bkp/.apw/.inp input; no request JSON is needed.")
    parser.add_argument("--pressure-basis", choices=("absolute", "gauge"), help="Required with --bkp.")
    parser.add_argument("--atmospheric-pressure-mpa", type=float, help="Required for gauge pressure; never defaulted.")
    parser.add_argument("--output-dir", help="New artifact directory for a direct Aspen run.")
    parser.add_argument("--timeout", dest="aspen_timeout_s", type=int, default=900, help="Direct Aspen worker timeout in seconds.")
    run_group = parser.add_mutually_exclusive_group()
    run_group.add_argument("--run", dest="run_aspen", action="store_true", help="Run the staged Aspen copy before extraction (direct mode default).")
    run_group.add_argument("--no-run", dest="run_aspen", action="store_false", help="Read existing results without running Aspen.")
    parser.set_defaults(run_aspen=True)
    parser.add_argument("--print-request-schema", action="store_true")
    parser.add_argument("--print-response-schema", action="store_true")
    args = parser.parse_args(args_list)
    if args.session_jsonl:
        incompatible = [
            flag
            for flag in (
                "--request", "--output", "--pretty", "--bkp", "--aspen-file",
                "--print-request-schema", "--print-response-schema",
            )
            if flag in args_list or any(item.startswith(f"{flag}=") for item in args_list)
        ]
        if incompatible:
            parser.error(f"--session-jsonl cannot be combined with: {', '.join(incompatible)}")
        return _run_jsonl_session()
    if args.print_request_schema or args.print_response_schema:
        schema_path = REQUEST_SCHEMA if args.print_request_schema else RESPONSE_SCHEMA
        _write_json(load_json_file(schema_path), args.output, True)
        return 0
    if args.aspen_file:
        if "--request" in args_list or any(item.startswith("--request=") for item in args_list):
            parser.error("--bkp/--aspen-file cannot be combined with --request")
        if not args.pressure_basis:
            parser.error("--pressure-basis absolute|gauge is required with --bkp")
        if args.pressure_basis == "gauge" and args.atmospheric_pressure_mpa is None:
            parser.error("--atmospheric-pressure-mpa is required when --pressure-basis gauge")
        payload: dict[str, Any] = {
            "source_path": str(Path(args.aspen_file).expanduser().resolve()),
            "pressure_basis": args.pressure_basis,
            "run": bool(args.run_aspen),
            "timeout_s": max(10, min(int(args.aspen_timeout_s), 7200)),
        }
        if args.output_dir:
            payload["output_dir"] = str(Path(args.output_dir).expanduser().resolve())
        if args.atmospheric_pressure_mpa is not None:
            payload["atmospheric_pressure_mpa"] = args.atmospheric_pressure_mpa
        request = {
            "schema": "equipment-design-agent-request-v1",
            "request_id": f"ASPEN-DIRECT-{uuid.uuid4().hex[:12]}",
            "operation": "aspen_import",
            "payload": payload,
        }
        response, exit_code = execute_request(request)
        _write_json(response, args.output, args.pretty)
        return exit_code
    try:
        request = _read_request(args.request)
    except Exception as exc:
        request = {"schema": "equipment-design-agent-request-v1", "operation": "UNKNOWN", "payload": {}}
        response = _failure("UNKNOWN", "UNKNOWN", sha256_json(request), "REQUEST_READ_FAILED", str(exc))
        _write_json(response, args.output, True)
        return 2
    response, exit_code = execute_request(request)
    _write_json(response, args.output, args.pretty)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
