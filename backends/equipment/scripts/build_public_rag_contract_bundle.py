from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import database_authority


BUNDLE_SCHEMA = "equipment-rag-public-contract-bundle-v1"
RAG_CONSUMER_ID = "standards_knowledge_search"
PUBLIC_FILES = (
    "README.md",
    "app/app_core.py",
    "app/database_authority.py",
    "app/schemas/equipment_database_authority_registry.schema.json",
    "data/database_authority_registry.json",
    "data/database_contracts/standards_knowledge_public_schema.sql",
    "data/database_contracts/executable_standard_data_public_schema.sql",
    "docs/DATABASE_STRUCTURE.md",
    "docs/RETRIEVAL_AND_GAPS.md",
    "scripts/audit_database_authority.py",
    "scripts/build_public_rag_contract_bundle.py",
)
FORBIDDEN_PAYLOAD_SUFFIXES = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".pdf",
    ".bkp",
    ".apw",
    ".inp",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
}
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


class PublicRagBundleError(RuntimeError):
    pass


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_source_path(root: Path, relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise PublicRagBundleError(f"unsafe public bundle path: {relative_path}")
    if relative.suffix.casefold() in FORBIDDEN_PAYLOAD_SUFFIXES:
        raise PublicRagBundleError(
            f"database, source-document or image payload is forbidden: {relative_path}"
        )
    source = root.joinpath(*relative.parts)
    if not source.is_file():
        raise PublicRagBundleError(f"public bundle source is missing: {relative_path}")
    return source


def _zip_write_bytes(
    archive: zipfile.ZipFile,
    archive_name: str,
    payload: bytes,
) -> None:
    info = zipfile.ZipInfo(archive_name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload)


def _bundle_readme(rag_database: dict[str, Any]) -> str:
    return (
        "# RAG 知识图谱公开合同包\n\n"
        "本包只包含可公开审查的源码、机器注册表、SQL 表结构、检索机理和"
        "验证工具，不包含 SQLite 数据载荷、教材/标准正文、页面图像或 Aspen "
        "工程。\n\n"
        f"- RAG 数据库 ID：`{rag_database['database_id']}`\n"
        f"- 登记状态：`{rag_database['status']}`\n"
        f"- 逻辑范围：`{rag_database['scope_status']}`\n"
        f"- 载荷相对路径：`{rag_database['relative_path']}`\n"
        f"- 预期大小：`{rag_database['expected_size_bytes']}` 字节\n"
        f"- 预期 SHA-256：`{rag_database['expected_sha256']}`\n\n"
        "先读 `docs/DATABASE_STRUCTURE.md`，再读 "
        "`docs/RETRIEVAL_AND_GAPS.md`。完整运行资产安装后，可执行 "
        "`python scripts/audit_database_authority.py` 验证真实数据库。\n"
    )


def build_public_rag_bundle(
    root: Path = PACKAGE_ROOT,
    output: Path | None = None,
) -> dict[str, Any]:
    package_root = root.resolve()
    registry = database_authority.load_registry(package_root)
    declaration = database_authority.declared_database_for_consumer(
        RAG_CONSUMER_ID,
        package_root,
    )
    rag_database = dict(declaration["database"])
    if rag_database.get("status") != "ACTIVE":
        raise PublicRagBundleError("RAG authority is not ACTIVE")

    output_path = (
        output
        or package_root
        / "outputs"
        / f"equipment-rag-public-contract-{registry['revision']}.zip"
    )
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    file_records: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for relative_path in sorted(PUBLIC_FILES):
        source = _safe_source_path(package_root, relative_path)
        payload = source.read_bytes()
        payloads[relative_path] = payload
        file_records.append(
            {
                "relative_path": relative_path,
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )

    manifest = {
        "schema": BUNDLE_SCHEMA,
        "revision": registry["revision"],
        "scope": "PUBLIC_RAG_CONTRACT_ONLY_NO_DATABASE_OR_COPYRIGHTED_TEXT",
        "rag_consumer": declaration["binding"],
        "rag_authority": {
            "database_id": rag_database["database_id"],
            "status": rag_database["status"],
            "scope_status": rag_database["scope_status"],
            "relative_path": rag_database["relative_path"],
            "expected_size_bytes": rag_database["expected_size_bytes"],
            "expected_sha256": rag_database["expected_sha256"],
            "table_contracts": rag_database["table_contracts"],
        },
        "excluded_payload_types": sorted(FORBIDDEN_PAYLOAD_SUFFIXES),
        "files": file_records,
    }
    manifest_payload = json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    readme_payload = _bundle_readme(rag_database).encode("utf-8")

    with zipfile.ZipFile(output_path, "w") as archive:
        _zip_write_bytes(archive, "PUBLIC_RAG_BUNDLE_README.md", readme_payload)
        _zip_write_bytes(archive, "public_rag_bundle_manifest.json", manifest_payload)
        for relative_path in sorted(payloads):
            _zip_write_bytes(archive, relative_path, payloads[relative_path])

    return {
        "schema": BUNDLE_SCHEMA,
        "status": "PASS",
        "output_path": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "sha256": sha256_file(output_path),
        "source_file_count": len(file_records),
        "archive_entry_count": len(file_records) + 2,
        "rag_database_id": rag_database["database_id"],
        "rag_database_payload_included": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a small public RAG knowledge-graph contract archive."
    )
    parser.add_argument("--root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_public_rag_bundle(args.root, args.output)
    except (database_authority.DatabaseAuthorityError, PublicRagBundleError) as exc:
        result = {
            "schema": BUNDLE_SCHEMA,
            "status": "FAIL",
            "error": str(exc),
        }
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=None if args.compact else 2,
            )
        )
        return 1
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
