"""Verify actual preserved content; never fetch or rebuild absent source pages."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path = ROOT) -> dict:
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    problems, paths = [], set()
    if manifest.get("schema") != "chemical-offline-knowledge-manifest-v1":
        problems.append("manifest schema")
    for item in manifest.get("files", []):
        relative = item["path"]
        path = (root / relative).resolve()
        if relative in paths or ".." in Path(relative).parts or Path(relative).is_absolute() or not path.is_relative_to(root):
            problems.append("unsafe/duplicate path: " + relative)
            continue
        paths.add(relative)
        try:
            raw = path.read_bytes()
            if len(raw) != item["bytes"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
                problems.append("hash/size mismatch: " + relative)
            if path.suffix in {".md", ".json", ".jsonl", ".py", ".csv"}:
                raw.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            problems.append(relative + ": " + str(exc))
    from query_knowledge import load_records
    try:
        _, records = load_records(root)
        counts = {name: sum(r["corpus"] == name for r in records) for name in ("chemical_principles", "sun_lanyi", "aspen_v10")}
        declared = manifest.get("corpus_record_counts")
        if not isinstance(declared, dict) or counts != declared:
            problems.append("corpus identity count mismatch")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(str(exc)); counts = {}
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
            and p != root/'manifest.json' and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    problems.extend('unmanifested file: '+p for p in sorted(actual-paths))
    return {"status": "pass" if not problems else "fail", "verified_files": len(paths),
            "corpus_record_counts": counts, "problems": problems, "raw_source_pages_verified": False,
            "aspen_engineering_acceptance_verified": False, "network_used": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = verify(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
