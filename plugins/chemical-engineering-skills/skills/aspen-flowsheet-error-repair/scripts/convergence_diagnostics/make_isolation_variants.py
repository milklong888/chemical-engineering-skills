#!/usr/bin/env python3
"""Make caller-defined literal variants offline, not a diagnosis or solver.

Each safe name is a filename stem; the source suffix is retained. All groups
are preflighted independently from the same source bytes. Unsupported local
splicing in a stateful encoding is rejected, never silently normalized.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    if isinstance(value, dict):
        for child in value.values():
            finite_json(child)
    elif isinstance(value, list):
        for child in value:
            finite_json(child)


def safe_name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise ValueError("name must be a safe ASCII filename stem")
    stem = value.split(".", 1)[0].upper()
    if value.endswith(".") or stem in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9]", stem):
        raise ValueError("reserved Windows name or trailing dot: " + value)
    return value


def decode_exact(raw, encoding):
    value = raw.decode(encoding, errors="strict")
    if value.encode(encoding, errors="strict") != raw:
        raise ValueError("source bytes do not strictly round-trip in selected encoding")
    return value


def replace_bytes(raw, find, replacement, encoding, expected):
    """Splice original non-target byte slices; validate the entire round-trip."""
    text = decode_exact(raw, encoding)
    actual = text.count(find)
    if actual != expected:
        raise ValueError("literal occurrence count: expected %d, got %d" % (expected, actual))
    pieces, cursor, position = [], 0, 0
    while actual and (start := text.find(find, position)) >= 0:
        end = start + len(find)
        before = text[:start].encode(encoding, errors="strict")
        through = text[:end].encode(encoding, errors="strict")
        changed = (text[:start] + replacement).encode(encoding, errors="strict")
        if not raw.startswith(before) or not raw.startswith(through) or not changed.startswith(before):
            raise ValueError("selected encoding cannot preserve non-target bytes at this edit")
        pieces.extend((raw[cursor:len(before)], changed[len(before):]))
        cursor, position = len(through), end
    pieces.append(raw[cursor:])
    result = b"".join(pieces)
    if decode_exact(result, encoding) != text.replace(find, replacement):
        raise ValueError("byte splice does not match the requested literal edit")
    return result, actual


def reference(path, raw):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def prepare(source, plan, encoding):
    if not isinstance(plan, dict) or not isinstance(plan.get("variants"), list) or not plan["variants"]:
        raise ValueError("plan requires a nonempty variants list")
    suffix = source.suffix
    if suffix and not re.fullmatch(r"\.[A-Za-z0-9]+", suffix):
        raise ValueError("source suffix must be a safe simple extension")
    original = source.read_bytes()
    decode_exact(original, encoding)
    prepared, seen = [], set()
    for variant in plan["variants"]:
        if not isinstance(variant, dict):
            raise ValueError("each variant must be an object")
        name = safe_name(variant.get("name"))
        filename = name + suffix
        if name.casefold() in seen or filename.casefold() == "manifest.json":
            raise ValueError("duplicate variant name or manifest filename collision")
        seen.add(name.casefold())
        edits = variant.get("edits")
        if not isinstance(edits, list):
            raise ValueError("each variant requires an edits list")
        raw, changes = original, []  # Reset to identical source bytes for every group.
        for edit in edits:
            if not isinstance(edit, dict):
                raise ValueError("each edit must be an object")
            find, replacement, count = edit.get("find"), edit.get("replace"), edit.get("expected_count")
            if not isinstance(find, str) or not find or not isinstance(replacement, str):
                raise ValueError("nonempty find and string replace required")
            if type(count) is not int or count < 0:
                raise ValueError("explicit nonnegative integer expected_count required; bool is not a count")
            raw, actual = replace_bytes(raw, find, replacement, encoding, count)
            changes.append({"find": find, "replace": replacement,
                            "expected_count": count, "actual_count": actual})
        prepared.append((filename, raw, {"name": name, "file": filename,
                         "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                         "edits": changes,
                         "caller_group_definition": {k: v for k, v in variant.items() if k != "edits"}}))
    return original, prepared


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--encoding", default="utf-8")
    args = parser.parse_args(argv)
    try:
        target = args.output_dir.resolve()
        if os.path.lexists(args.output_dir) or target == args.source.resolve() or args.source.resolve().is_relative_to(target):
            raise ValueError("output directory must be new and must not cover the source")
        safe_name(args.output_dir.name)
        if not target.parent.is_dir():
            raise ValueError("output parent directory must already exist")
        plan_raw = args.plan.read_bytes()
        plan = json.loads(plan_raw.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=invalid_constant)
        finite_json(plan)
        original, prepared = prepare(args.source, plan, args.encoding)
        if args.source.read_bytes() != original or args.plan.read_bytes() != plan_raw:
            raise ValueError("source or plan changed during preflight")
        manifest = {"schema": "literal-isolation-variants/1", "encoding": args.encoding,
                    "source": reference(args.source, original), "plan": reference(args.plan, plan_raw),
                    "caller_plan_metadata": {k: v for k, v in plan.items() if k != "variants"},
                    "variants": [row for _, _, row in prepared],
                    "scope": "Offline literal edits only; no native parser, solver, warning diagnosis or engineering acceptance."}
        manifest_raw = (json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
        target.mkdir()  # Exclusive creation occurs only after every group passed preflight.
        for filename, raw, _ in prepared:
            with (target / filename).open("xb") as handle:
                handle.write(raw)
        with (target / "manifest.json").open("xb") as handle:
            handle.write(manifest_raw)
    except (OSError, ValueError, LookupError) as exc:
        print("variant error: " + str(exc), file=sys.stderr)
        return 2
    print(str(target / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
