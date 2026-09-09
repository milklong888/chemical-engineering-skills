#!/usr/bin/env python3
"""Install a hash-frozen, local-only MCP runtime into a new CPython 3.14 venv.

No Aspen launch, global configuration change, implicit download or overwrite.
An incomplete environment is preserved with a failure receipt, never reused.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / 'vendor' / 'aspen-mcp-toolkit' / 'offline-runtime.lock.json'
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
VERSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.+!-]*\Z')
HASH = re.compile(r'[0-9a-fA-F]{64}\Z')


class OfflineInstallError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def normalize_name(value: str) -> str:
    return re.sub(r'[-_.]+', '-', value).lower()


def safe_environment() -> dict[str, str]:
    # Deliberately omit account, token, proxy, provider and Python-path variables.
    keys = ('SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE', 'COMSPEC', 'PATH', 'PATHEXT',
            'TEMP', 'TMP', 'PROCESSOR_ARCHITECTURE')
    result = {key: os.environ[key] for key in keys if key in os.environ}
    result.update({'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8',
                   'PIP_CONFIG_FILE': os.devnull, 'PIP_NO_INDEX': '1',
                   'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
    return result


def inspect_python(executable: Path) -> dict[str, Any]:
    code = ('import json,platform,struct,sysconfig;'
            'print(json.dumps({"implementation":platform.python_implementation(),'
            '"version":platform.python_version(),"bits":struct.calcsize("P")*8,'
            '"platform":sysconfig.get_platform()}))')
    result = subprocess.run([str(executable), '-I', '-B', '-c', code],
                            capture_output=True, text=True, encoding='utf-8',
                            timeout=20, env=safe_environment(), check=False)
    if result.returncode:
        raise OfflineInstallError('Python probe failed: ' + result.stderr[:500])
    try:
        info = json.loads(result.stdout)
    except ValueError as exc:
        raise OfflineInstallError('Python probe did not return JSON') from exc
    validate_python_info(info)
    return info


def validate_python_info(info: dict[str, Any]) -> None:
    if not (info.get('implementation') == 'CPython'
            and str(info.get('version', '')).split('.')[:2] == ['3', '14']
            and info.get('bits') == 64
            and str(info.get('platform', '')).replace('-', '_') == 'win_amd64'):
        raise OfflineInstallError('Required runtime: CPython 3.14, Windows AMD64, 64 bit')


def validate_lock(lock_path: Path, wheelhouse: Path, *,
                  expected_schema: str = 'aspen-mcp-offline-runtime-v1',
                  required_distributions: set[str] | None = None) -> tuple[dict[str, Any], str]:
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    if lock.get('schema') != expected_schema:
        raise OfflineInstallError('Unknown offline lock schema')
    target = lock.get('target', {})
    if (target.get('implementation'), target.get('python_major_minor'),
        target.get('platform'), target.get('bits')) != ('CPython', '3.14', 'win_amd64', 64):
        raise OfflineInstallError('Unsupported lock target')
    wheels = lock.get('wheels')
    if not isinstance(wheels, list) or not wheels or lock.get('wheel_count') != len(wheels):
        raise OfflineInstallError('Missing or inconsistent wheel inventory')
    names: set[str] = set()
    files: set[str] = set()
    requirements: list[str] = []
    for row in wheels:
        name, version = row.get('name', ''), row.get('version', '')
        filename, checksum = row.get('filename', ''), row.get('sha256', '')
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise OfflineInstallError('Invalid distribution name')
        if not isinstance(version, str) or not VERSION.fullmatch(version):
            raise OfflineInstallError('Invalid exact version')
        if (not isinstance(filename, str) or Path(filename).name != filename
                or '/' in filename or '\\' in filename or ':' in filename
                or not filename.endswith('.whl')):
            raise OfflineInstallError('Wheel filename must be a local basename')
        if not isinstance(checksum, str) or not HASH.fullmatch(checksum):
            raise OfflineInstallError('Invalid wheel hash')
        canonical = normalize_name(name)
        if canonical in names or filename.lower() in files:
            raise OfflineInstallError('Duplicate distribution or wheel filename')
        names.add(canonical)
        files.add(filename.lower())
        path = wheelhouse / filename
        if path.is_symlink() or not path.is_file() or path.resolve().parent != wheelhouse.resolve():
            raise OfflineInstallError('Missing or unsafe wheel: ' + filename)
        if type(row.get('bytes')) is not int or path.stat().st_size != row['bytes']:
            raise OfflineInstallError('Wheel size mismatch: ' + filename)
        if sha256(path) != checksum.lower():
            raise OfflineInstallError('Wheel hash mismatch: ' + filename)
        requirements.append(f'{name}=={version} --hash=sha256:{checksum.lower()}')
    required = {'fastmcp', 'fastmcp-slim', 'mcp', 'pywin32'} if required_distributions is None else required_distributions
    if not required.issubset(names):
        raise OfflineInstallError('Required MCP/Windows distributions missing from lock')
    actual = {p.name.lower() for p in wheelhouse.iterdir() if p.is_file() and p.suffix == '.whl'}
    if actual != files:
        raise OfflineInstallError('Wheelhouse has unlisted or missing wheels')
    return lock, '\n'.join(sorted(requirements, key=str.lower)) + '\n'


def validate_extension(base_path: Path, base: dict[str, Any], path: Path,
                       wheelhouse: Path) -> tuple[dict[str, Any], str]:
    extension, requirements = validate_lock(path, wheelhouse,
        expected_schema='aspen-mcp-offline-extension-v1', required_distributions=set())
    if extension.get('base_lock_sha256') != sha256(base_path):
        raise OfflineInstallError('Extension is not bound to this exact base lock')
    original_names = {normalize_name(row['name']) for row in base['wheels']}
    if original_names & {normalize_name(row['name']) for row in extension['wheels']}:
        raise OfflineInstallError('Extension cannot replace any base distribution')
    return extension, requirements


def validate_new_target(target: Path, wheelhouse: Path, lock_path: Path) -> None:
    if os.path.lexists(target):
        raise OfflineInstallError('Target already exists; choose a new venv directory')
    for source in (wheelhouse.resolve(), lock_path.resolve().parent):
        if target == source or target in source.parents or source in target.parents:
            raise OfflineInstallError('Target overlaps immutable source or wheelhouse')


def write_receipt(target: Path, receipt: dict[str, Any]) -> None:
    (target / 'offline-install-receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def execute_stage(command: list[str], target: Path, name: str, timeout: float) -> dict[str, Any]:
    out = target / (name + '.stdout.txt')
    err = target / (name + '.stderr.txt')
    with out.open('w', encoding='utf-8') as stdout, err.open('w', encoding='utf-8') as stderr:
        # Commands are Python/venv/pip only. No untrusted project scripts are executed.
        result = subprocess.run(command, cwd=target, stdout=stdout, stderr=stderr,
                                timeout=timeout, env=safe_environment(), check=False)
    return {'stage': name, 'returncode': result.returncode,
            'stdout': out.name, 'stderr': err.name,
            'stdout_sha256': sha256(out), 'stderr_sha256': sha256(err)}


def install(*, python: Path, target: Path, wheelhouse: Path, lock_path: Path,
            dry_run: bool = False, extension_lock: Path | None = None,
            extension_wheelhouse: Path | None = None) -> dict[str, Any]:
    if os.path.lexists(target):
        raise OfflineInstallError('Target already exists, including dangling links')
    target, wheelhouse, lock_path = target.resolve(), wheelhouse.resolve(), lock_path.resolve()
    validate_new_target(target, wheelhouse, lock_path)
    runtime = inspect_python(python.resolve())
    lock, requirements = validate_lock(lock_path, wheelhouse)
    extension = None
    if (extension_lock is None) != (extension_wheelhouse is None):
        raise OfflineInstallError('Supply both extension lock and extension wheelhouse')
    if extension_lock is not None:
        extension_lock, extension_wheelhouse = extension_lock.resolve(), extension_wheelhouse.resolve()
        validate_new_target(target, extension_wheelhouse, extension_lock)
        extension, more_requirements = validate_extension(lock_path, lock, extension_lock, extension_wheelhouse)
        requirements += more_requirements
    receipt: dict[str, Any] = {
        'schema': 'aspen-mcp-offline-install-receipt-v1',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'target': str(target), 'runtime': runtime, 'lock_sha256': sha256(lock_path),
        'wheel_count': len(lock['wheels']), 'network_install_allowed': False,
        'aspen_started': False, 'protocol_verified': False,
        'simulation_clean': False, 'stages': [], 'status': 'validated_dry_run'}
    receipt['extensions'] = [] if extension is None else [{
        'extension_id': extension.get('extension_id'), 'lock_sha256': sha256(extension_lock),
        'wheel_count': len(extension['wheels']), 'base_lock_sha256': extension['base_lock_sha256']}]
    if dry_run:
        return receipt
    # Atomic exclusive claim; do not reuse even an empty caller-owned directory.
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(exist_ok=False)
    receipt['status'] = 'installing'
    write_receipt(target, receipt)
    requirement_path = target / 'offline-frozen-requirements.txt'
    requirement_path.write_text(requirements, encoding='utf-8')
    (target / 'offline-runtime.lock.json').write_bytes(lock_path.read_bytes())
    extra_links: list[str] = []
    if extension is not None:
        (target / 'offline-extension.lock.json').write_bytes(extension_lock.read_bytes())
        extra_links = ['--find-links', str(extension_wheelhouse)]
    try:
        version_probe = (
            'import importlib.metadata as m,json,sys;'
            'from pathlib import Path;'
            'rows=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["wheels"];'
            'rows += json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["wheels"] if sys.argv[2]!="-" else [];'
            'actual=[{"name":r["name"],"expected":r["version"],"installed":m.version(r["name"])} for r in rows];'
            'print(json.dumps(actual));'
            'sys.exit(0 if all(r["expected"]==r["installed"] for r in actual) else 1)')
        stages = [
            ('venv', [str(python.resolve()), '-I', '-B', '-m', 'venv', str(target)], 180),
            ('pip_install', [str(target / 'Scripts' / 'python.exe'), '-I', '-B', '-m', 'pip',
                             '--disable-pip-version-check', 'install', '--no-index',
                             '--no-input', '--only-binary=:all:', '--find-links', str(wheelhouse),
                             *extra_links, '--require-hashes', '-r', str(requirement_path)], 300),
            ('pip_check', [str(target / 'Scripts' / 'python.exe'), '-I', '-B', '-m', 'pip',
                           '--disable-pip-version-check', 'check'], 60),
            ('version_check', [str(target / 'Scripts' / 'python.exe'), '-I', '-B', '-c', version_probe,
                               str(target / 'offline-runtime.lock.json'),
                               str(target / 'offline-extension.lock.json') if extension is not None else '-'], 30),
        ]
        for name, command, timeout in stages:
            stage = execute_stage(command, target, name, timeout)
            receipt['stages'].append(stage)
            write_receipt(target, receipt)
            if stage['returncode'] != 0:
                raise OfflineInstallError(f'{name} failed; inspect preserved logs')
        receipt['status'] = 'installed_offline'
    except Exception as exc:
        receipt['status'] = 'failed_preserved'
        receipt['error'] = str(exc)
        write_receipt(target, receipt)
        raise
    write_receipt(target, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheelhouse', type=Path, required=True)
    parser.add_argument('--lock', type=Path, default=DEFAULT_LOCK)
    parser.add_argument('--target', type=Path, required=True, help='New nonexistent venv directory')
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--extension-lock', type=Path, help='Optional separately hash-bound extension lock')
    parser.add_argument('--extension-wheelhouse', type=Path, help='Local wheels for that extension')
    args = parser.parse_args()
    try:
        result = install(python=args.python, target=args.target, wheelhouse=args.wheelhouse,
                         lock_path=args.lock, dry_run=args.dry_run,
                         extension_lock=args.extension_lock, extension_wheelhouse=args.extension_wheelhouse)
    except Exception as exc:
        print(json.dumps({'status': 'blocked_or_failed', 'error': str(exc),
                          'aspen_started': False}, ensure_ascii=True))
        return 2
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
