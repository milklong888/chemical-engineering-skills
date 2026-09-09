#!/usr/bin/env python3
"""Audit basic PDF container integrity without attempting content promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import re
from pathlib import Path


TOKENS = (b"%PDF-", b"%%EOF", b"startxref", b"/Type/Page", b"/Type /Page")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def count_token(data: mmap.mmap, token: bytes) -> int:
    count = 0
    offset = 0
    while True:
        offset = data.find(token, offset)
        if offset < 0:
            return count
        count += 1
        offset += len(token)


def is_nonzero_byte(value: object) -> bool:
    return value not in (0, b"\x00")


def audit_pdf(path: Path) -> dict:
    size = path.stat().st_size
    if size == 0:
        return {
            "schema": "pdf-container-integrity-audit-v1",
            "path": str(path),
            "size_bytes": 0,
            "sha256": sha256_file(path),
            "status": "EMPTY_FILE",
            "content_recovery_state": "SOURCE_UNREADABLE_BLOCKED",
        }
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            first_nonzero = next(
                (i for i, value in enumerate(data) if is_nonzero_byte(value)), -1
            )
            last_nonzero_from_end = next(
                (
                    i
                    for i, value in enumerate(reversed(data))
                    if is_nonzero_byte(value)
                ),
                -1,
            )
            last_nonzero = (
                size - last_nonzero_from_end - 1 if last_nonzero_from_end >= 0 else -1
            )
            zero_tail = size - last_nonzero - 1 if last_nonzero >= 0 else size
            token_counts = {
                token.decode("ascii", errors="replace"): count_token(data, token)
                for token in TOKENS
            }
            token_last_offsets = {
                token.decode("ascii", errors="replace"): data.rfind(token)
                for token in TOKENS
            }
            indirect_object_count = sum(
                1
                for _ in re.finditer(
                    rb"(?m)^\s*\d+\s+\d+\s+obj\b",
                    data[: last_nonzero + 1] if last_nonzero >= 0 else data,
                )
            )

    has_header = token_counts["%PDF-"] >= 1 and first_nonzero == 0
    has_eof = token_counts["%%EOF"] >= 1
    has_startxref = token_counts["startxref"] >= 1
    suspicious_padding = zero_tail >= 1024 * 1024
    if has_header and has_eof and has_startxref and not suspicious_padding:
        status = "BASIC_CONTAINER_MARKERS_PRESENT"
        recovery = "PARSER_VALIDATION_REQUIRED"
    elif has_header and not has_eof and not has_startxref and suspicious_padding:
        status = "TRUNCATED_ZERO_PADDED"
        recovery = "SOURCE_UNREADABLE_BLOCKED_REACQUIRE_REQUIRED"
    else:
        status = "MALFORMED_OR_INCOMPLETE"
        recovery = "SOURCE_UNREADABLE_BLOCKED_REPAIR_OR_REACQUIRE_REQUIRED"

    return {
        "schema": "pdf-container-integrity-audit-v1",
        "path": str(path),
        "size_bytes": size,
        "sha256": sha256_file(path),
        "first_nonzero_offset": first_nonzero,
        "last_nonzero_offset": last_nonzero,
        "zero_tail_bytes": zero_tail,
        "zero_tail_fraction": zero_tail / size,
        "token_counts": token_counts,
        "token_last_offsets": token_last_offsets,
        "indirect_object_marker_count": indirect_object_count,
        "status": status,
        "content_recovery_state": recovery,
        "promotion_authority": "NONE_CONTAINER_AUDIT_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, nargs="?")
    parser.add_argument(
        "--pdf-env",
        help="Read a Unicode-safe PDF path from this environment variable.",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.pdf_env:
        env_value = os.environ.get(args.pdf_env, "")
        if not env_value:
            parser.error(f"environment variable is empty or missing: {args.pdf_env}")
        path = Path(env_value).resolve()
    elif args.pdf:
        path = args.pdf.resolve()
    else:
        parser.error("provide PDF path or --pdf-env")
    payload = audit_pdf(path)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "BASIC_CONTAINER_MARKERS_PRESENT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
