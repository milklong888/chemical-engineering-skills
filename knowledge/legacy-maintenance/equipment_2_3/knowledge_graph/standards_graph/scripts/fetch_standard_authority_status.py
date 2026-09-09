#!/usr/bin/env python3
"""Resolve supplied standard identities against the official SAMR platform.

This is an offline build/audit utility. Production equipment queries must not
call the network or the original standards.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path


SEARCH_URL = "https://std.samr.gov.cn/search/stdPage?q={}"
ENTRY_PATTERN = re.compile(
    r'<a[^>]*\bpid="(?P<pid>[^"]+)"[^>]*>\s*'
    r'<span\s+class="en-code">(?P<code>.*?)</span>.*?</a>.*?'
    r'<span\s+class="s-status[^"]*">(?P<status>.*?)</span>',
    re.I | re.S,
)
INFO_PATTERN = re.compile(
    r'<dt\s+class="basicInfo-item name">(?P<name>.*?)</dt>\s*'
    r'<dd\s+class="basicInfo-item value"[^>]*>(?P<value>.*?)</dd>',
    re.I | re.S,
)
UPCOMING_REPLACEMENT_PATTERN = re.compile(
    r'即将被以下标准替代.*?'
    r'<a\s+href="(?P<url>[^"]+)"[^>]*>.*?'
    r'(?P<code>(?:GB|GB/T)\s*[0-9]+(?:\.[0-9]+)?-[0-9]{4})\s*'
    r'</a>',
    re.I | re.S,
)


def norm_code(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    value = value.upper().replace("～", "~")
    return re.sub(r"\s+", "", value)


def parse_entries(content: str) -> list[dict]:
    entries = []
    for match in ENTRY_PATTERN.finditer(content):
        code = html.unescape(re.sub(r"<[^>]+>", "", match.group("code"))).strip()
        status = html.unescape(re.sub(r"<[^>]+>", "", match.group("status"))).strip()
        pid = match.group("pid").strip()
        entries.append(
            {
                "code": code,
                "normalized_code": norm_code(code),
                "status_text": status,
                "pid": pid,
                "detail_url": f"https://std.samr.gov.cn/gb/search/gbDetailed?id={pid}",
            }
        )
    return entries


def authority_state(status_text: str) -> str:
    if "现行" in status_text:
        return "CURRENT"
    if "废止" in status_text:
        return "WITHDRAWN"
    if "即将" in status_text:
        return "UPCOMING"
    return "UNRESOLVED"


def plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", value))).strip()


def parse_detail(content: str) -> dict:
    """Parse official lifecycle fields from a SAMR national-standard page."""
    info = {
        plain_text(match.group("name")): plain_text(match.group("value"))
        for match in INFO_PATTERN.finditer(content)
    }
    replacement = UPCOMING_REPLACEMENT_PATTERN.search(content)
    replacement_relation = ""
    if replacement:
        nearby = content[replacement.end() : replacement.end() + 800]
        relation_match = re.search(r"（[^）]+代替[^）]*）", plain_text(nearby))
        replacement_relation = relation_match.group(0) if relation_match else ""
    return {
        "publication_date": info.get("发布日期", ""),
        "implementation_date": info.get("实施日期", ""),
        "review_date": info.get("上次复审日期", ""),
        "review_conclusion": info.get("上次复审结论", ""),
        "replaced_by_code": plain_text(replacement.group("code")) if replacement else "",
        "replaced_by_detail_url": html.unescape(replacement.group("url")) if replacement else "",
        "replacement_relation": replacement_relation,
    }


def lifecycle_state(authority: str, replacement_code: str, replacement_date: str, as_of: date) -> str:
    if authority != "CURRENT":
        return authority
    if not replacement_code:
        return "CURRENT"
    try:
        effective = date.fromisoformat(replacement_date)
    except ValueError:
        return "CURRENT_REPLACEMENT_DATE_UNRESOLVED"
    if as_of < effective:
        return "CURRENT_PENDING_REPLACEMENT"
    return "WITHDRAWN_BY_EFFECTIVE_REPLACEMENT"


def fetch_text(url: str, cache_path: Path, timeout: int) -> str:
    if cache_path.is_file():
        return cache_path.read_text(encoding="utf-8")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EquipmentDesignDataAudit/1.0 (+offline standards inventory)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    content = raw.decode("utf-8", errors="replace")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(content, encoding="utf-8")
    return content


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def collapse_official_resolution_rows(
    rows: list[dict], evidence_path: Path, as_of: date
) -> dict[str, dict]:
    """Collapse independently verified official evidence to one source-level row."""
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("source_id") or ""), []).append(row)
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest().upper()
    collapsed: dict[str, dict] = {}
    for source_id, members in grouped.items():
        if not source_id:
            continue
        source_hashes = {str(row.get("sha256") or "").upper() for row in members}
        resolution_complete = all(row.get("resolution") == "VERIFIED" for row in members)
        status_values = [str(row.get("authority_status") or "") for row in members]
        all_withdrawn = bool(status_values) and all(
            ("被替代" in value and "即将" not in value) or "废止" in value
            for value in status_values
        )
        all_current = bool(status_values) and all("现行" in value for value in status_values)
        if not resolution_complete:
            state = "UNRESOLVED"
            lifecycle = "UNRESOLVED"
            verification = "OFFICIAL_MANUAL_RESOLUTION_UNRESOLVED"
        elif all_withdrawn:
            state = "WITHDRAWN"
            lifecycle = "WITHDRAWN_REPLACED"
            verification = "OFFICIAL_MANUAL_RESOLUTION_VERIFIED"
        elif all_current:
            state = "CURRENT"
            future_dates = sorted(
                {
                    row.get("future_replacement_date", "")
                    for row in members
                    if row.get("future_replacement_date", "")
                }
            )
            future = future_dates[0] if len(future_dates) == 1 else ""
            lifecycle = lifecycle_state(
                state,
                "future replacement" if future else "",
                future,
                as_of,
            )
            verification = "OFFICIAL_MANUAL_RESOLUTION_VERIFIED"
        else:
            state = "UNRESOLVED"
            lifecycle = "UNRESOLVED_MIXED_MEMBER_STATUS"
            verification = "OFFICIAL_MANUAL_RESOLUTION_MIXED_STATUS"

        def unique(field: str) -> list[str]:
            return sorted(
                {
                    str(row.get(field) or "").strip()
                    for row in members
                    if str(row.get(field) or "").strip()
                }
            )

        collapsed[source_id] = {
            "source_id": source_id,
            "source_sha256": next(iter(source_hashes)) if len(source_hashes) == 1 else "",
            "standard_id": " | ".join(unique("official_standard_no")),
            "authority_state": state,
            "status_text": " | ".join(unique("authority_status")),
            "matched_code": " | ".join(unique("official_standard_no")),
            "official_search_url": "",
            "official_detail_url": " | ".join(unique("official_url")),
            "match_count": len(members),
            "verification_status": verification,
            "publication_date": " | ".join(unique("publication_date")),
            "implementation_date": " | ".join(unique("implementation_date")),
            "review_date": "",
            "review_conclusion": "",
            "replaced_by_code": "",
            "replacement_relation": " | ".join(unique("replacement_relation")),
            "replacement_implementation_date": " | ".join(
                unique("future_replacement_date")
            ),
            "lifecycle_state": lifecycle,
            "resolution_evidence_path": str(evidence_path),
            "resolution_evidence_sha256": evidence_sha256,
            "resolution_member_count": len(members),
        }
    return collapsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--official-resolution-csv", type=Path)
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    cache_dir = out_dir / "authority_cache"
    rows = []
    official_resolution_overrides: dict[str, dict] = {}
    if args.official_resolution_csv:
        official_resolution_path = args.official_resolution_csv.resolve()
        official_resolution_overrides = collapse_official_resolution_rows(
            read_csv(official_resolution_path), official_resolution_path, args.as_of
        )
    allowed_kinds = {"standard", "construction_standard", "obsolete_standard"}
    for source in read_csv(args.source_inventory.resolve()):
        if source.get("source_kind") not in allowed_kinds:
            continue
        standard_id = str(source.get("standard_id") or "").strip()
        manual_resolution = official_resolution_overrides.get(source.get("source_id", ""))
        if manual_resolution:
            if manual_resolution.get("source_sha256") != str(source.get("sha256") or "").upper():
                raise ValueError(
                    f"{source.get('source_id')}: official resolution source hash mismatch"
                )
            rows.append(manual_resolution)
            continue
        if source.get("authority_status") == "OBSOLETE_FORBIDDEN":
            rows.append(
                {
                    "source_id": source.get("source_id", ""),
                    "source_sha256": source.get("sha256", ""),
                    "standard_id": standard_id,
                    "authority_state": "WITHDRAWN",
                    "status_text": "文件名明确标注废止；仍需确认替代标准",
                    "matched_code": standard_id,
                    "official_search_url": "",
                    "official_detail_url": "",
                    "match_count": 0,
                    "verification_status": "FILE_DECLARED_OBSOLETE_QUARANTINED",
                }
            )
            continue
        if not standard_id or "~" in standard_id:
            rows.append(
                {
                    "source_id": source.get("source_id", ""),
                    "source_sha256": source.get("sha256", ""),
                    "standard_id": standard_id,
                    "authority_state": "UNRESOLVED",
                    "status_text": "",
                    "matched_code": "",
                    "official_search_url": "",
                    "official_detail_url": "",
                    "match_count": 0,
                    "verification_status": "IDENTITY_REQUIRES_COMPONENT_OR_MANUAL_RESOLUTION",
                }
            )
            continue
        url = SEARCH_URL.format(urllib.parse.quote(standard_id, safe=""))
        cache_name = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".html"
        try:
            content = fetch_text(url, cache_dir / cache_name, args.timeout)
            entries = parse_entries(content)
            target = norm_code(standard_id)
            exact = [entry for entry in entries if entry["normalized_code"] == target]
            authoritative_exact = [
                entry
                for entry in exact
                if authority_state(entry["status_text"]) in {"CURRENT", "WITHDRAWN", "UPCOMING"}
            ]
            if len(authoritative_exact) == 1:
                match = authoritative_exact[0]
                verification = "OFFICIAL_EXACT_MATCH"
                state = authority_state(match["status_text"])
            else:
                match = {}
                verification = (
                    "OFFICIAL_NO_EXACT_MATCH"
                    if not exact
                    else "OFFICIAL_AMBIGUOUS_MATCH"
                )
                state = "UNRESOLVED"
            detail = {}
            replacement_detail = {}
            if match.get("detail_url"):
                detail_url = match["detail_url"]
                detail_cache = cache_dir / (hashlib.sha256(detail_url.encode("utf-8")).hexdigest() + ".html")
                detail = parse_detail(fetch_text(detail_url, detail_cache, args.timeout))
                replacement_url = detail.get("replaced_by_detail_url", "")
                if replacement_url:
                    replacement_cache = cache_dir / (
                        hashlib.sha256(replacement_url.encode("utf-8")).hexdigest() + ".html"
                    )
                    replacement_detail = parse_detail(
                        fetch_text(replacement_url, replacement_cache, args.timeout)
                    )
            replacement_date = replacement_detail.get("implementation_date", "")
            rows.append(
                {
                    "source_id": source.get("source_id", ""),
                    "source_sha256": source.get("sha256", ""),
                    "standard_id": standard_id,
                    "authority_state": state,
                    "status_text": match.get("status_text", ""),
                    "matched_code": match.get("code", ""),
                    "official_search_url": url,
                    "official_detail_url": match.get("detail_url", ""),
                    "match_count": len(authoritative_exact),
                    "verification_status": verification,
                    "publication_date": detail.get("publication_date", ""),
                    "implementation_date": detail.get("implementation_date", ""),
                    "review_date": detail.get("review_date", ""),
                    "review_conclusion": detail.get("review_conclusion", ""),
                    "replaced_by_code": detail.get("replaced_by_code", ""),
                    "replacement_relation": detail.get("replacement_relation", ""),
                    "replacement_implementation_date": replacement_date,
                    "lifecycle_state": lifecycle_state(
                        state,
                        detail.get("replaced_by_code", ""),
                        replacement_date,
                        args.as_of,
                    ),
                }
            )
        except Exception as exc:  # network failures remain explicit, never guessed
            rows.append(
                {
                    "source_id": source.get("source_id", ""),
                    "source_sha256": source.get("sha256", ""),
                    "standard_id": standard_id,
                    "authority_state": "UNRESOLVED",
                    "status_text": "",
                    "matched_code": "",
                    "official_search_url": url,
                    "official_detail_url": "",
                    "match_count": 0,
                    "verification_status": f"NETWORK_ERROR:{type(exc).__name__}",
                }
            )
        time.sleep(max(0.0, args.delay))
    fields = [
        "source_id",
        "source_sha256",
        "standard_id",
        "authority_state",
        "status_text",
        "matched_code",
        "official_search_url",
        "official_detail_url",
        "match_count",
        "verification_status",
        "publication_date",
        "implementation_date",
        "review_date",
        "review_conclusion",
        "replaced_by_code",
        "replacement_relation",
        "replacement_implementation_date",
        "lifecycle_state",
        "resolution_evidence_path",
        "resolution_evidence_sha256",
        "resolution_member_count",
    ]
    write_csv(out_dir / "standard_authority_status.csv", rows, fields)
    summary = {
        "schema": "equipment-standard-authority-status-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(rows),
        "state_counts": {
            state: sum(row["authority_state"] == state for row in rows)
            for state in sorted({row["authority_state"] for row in rows})
        },
        "verification_counts": {
            state: sum(row["verification_status"] == state for row in rows)
            for state in sorted({row["verification_status"] for row in rows})
        },
        "unresolved_count": sum(row["authority_state"] == "UNRESOLVED" for row in rows),
        "lifecycle_counts": {
            state: sum(row.get("lifecycle_state", "") == state for row in rows)
            for state in sorted({row.get("lifecycle_state", "") for row in rows if row.get("lifecycle_state", "")})
        },
    }
    (out_dir / "standard_authority_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
