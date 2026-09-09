"""Explicit, hash-bound user case data for the preserved legacy audit code.

Generic equipment formulas never need a case profile. No source-machine case
values are bundled, inferred or loaded from the current working directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaseProfile:
    values: dict[str, Any]
    profile_path: Path
    profile_sha256: str
    source_root: Path
    output_root: Path

    def source_path(self, relative: str) -> Path:
        path = (self.source_root / relative).resolve()
        if not path.is_relative_to(self.source_root) or not path.is_file():
            raise ValueError(f"case_source_unavailable_or_outside_root: {relative}")
        return path


_CURRENT: CaseProfile | None = None


def configure_case_profile(profile_path: Path | None, expected_sha256: str | None,
                           source_root: Path | None, output_root: Path | None) -> CaseProfile:
    global _CURRENT
    if not all((profile_path, expected_sha256, source_root, output_root)):
        raise ValueError("Explicit --case-profile, --case-profile-sha256, --source-root and --output-root are required")
    profile_path = Path(profile_path).resolve(strict=True)
    source_root = Path(source_root).resolve(strict=True)
    output_root = Path(output_root).resolve()
    if not source_root.is_dir() or not profile_path.is_file():
        raise ValueError("Case source root/profile is unavailable")
    if output_root.is_relative_to(source_root) or source_root.is_relative_to(output_root):
        raise ValueError("Case output must be disjoint from the source root")
    if output_root.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Case outputs cannot overwrite the installed backend")
    content = profile_path.read_bytes()
    actual = hashlib.sha256(content).hexdigest().upper()
    if actual != str(expected_sha256).upper():
        raise ValueError("Case profile SHA-256 mismatch")
    data = json.loads(content)
    if (data.get("schema") != "equipment-legacy-case-profile-v1"
            or not isinstance(data.get("globals"), dict)
            or not isinstance(data.get("literals"), dict)):
        raise ValueError("Unsupported case profile schema")
    _CURRENT = CaseProfile(data, profile_path, actual, source_root, output_root)
    return _CURRENT


def require_case_profile() -> CaseProfile:
    if _CURRENT is None:
        raise ValueError("dependency_unavailable: no explicit hash-bound legacy case profile")
    return _CURRENT


def _guard(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        require_case_profile()
        return function(*args, **kwargs)
    return guarded


require_case_profile.guard = _guard


def case_value(key: str):
    values = require_case_profile().values["literals"]
    if key not in values:
        raise ValueError(f"case_literal_missing: {key}")
    return values[key]


class CaseGlobal:
    def __init__(self, key: str):
        self.key = key

    def _value(self):
        values = require_case_profile().values["globals"]
        if self.key not in values:
            raise ValueError(f"case_global_missing: {self.key}")
        return values[self.key]

    def __iter__(self):
        return iter(self._value())

    def __len__(self):
        return len(self._value())

    def __getitem__(self, key):
        return self._value()[key]

    def __getattr__(self, key):
        return getattr(self._value(), key)

    def __bool__(self):
        return bool(self._value())
