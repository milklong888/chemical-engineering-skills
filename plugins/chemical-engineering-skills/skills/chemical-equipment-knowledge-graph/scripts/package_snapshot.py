"""Package the current graph snapshot without touching its source files."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import tempfile
from time import monotonic
import unicodedata
import zipfile


GRAPH = '知识图谱'
ROOT_FILES = ('AGENTS.md', 'LOCAL_KNOWLEDGE_GRAPH_LINKS.md')
MANIFEST = 'SNAPSHOT_MANIFEST.json'
BASE = f'{GRAPH}/knowledge.sqlite'
INCREMENT = f'{GRAPH}/increment.sqlite'
OCR = f'{GRAPH}/ocr.sqlite'
ALPHA = f'{GRAPH}/fortran_ocr_review/alpha_ocr.sqlite'
BASE_MANIFEST = f'{GRAPH}/snapshot_manifest.json'
AUDIT = f'{GRAPH}/continuation_audit/receipt.json'
TRANSCRIPTION = f'{GRAPH}/design_role_review/source_transcription_receipt.json'
POLICY = f'{GRAPH}/design_role_review/policy.json'
REQUIRED = {BASE, INCREMENT, OCR, ALPHA, BASE_MANIFEST, AUDIT, *ROOT_FILES}
VIDEO_EXTENSIONS = {'.avi', '.m4v', '.mkv', '.mov', '.mp4', '.mpeg', '.mpg', '.rmvb', '.webm', '.wmv', '.flv'}
BLOCK_SIZE = 1024 * 1024
DEVICE_NAME = re.compile(r'(?i)(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


def canonical_json(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_keys(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f'重复 JSON 键 {key!r}')
        result[key] = value
    return result


def parse_json(data):
    return json.loads(data, object_pairs_hook=unique_keys)


def digest_stream(reader, writer=None):
    total = 0
    digest = hashlib.sha256()
    for chunk in iter(lambda: reader.read(BLOCK_SIZE), b''):
        digest.update(chunk)
        total += len(chunk)
        if writer is not None:
            writer.write(chunk)
    return total, digest.hexdigest()


def digest_file(path):
    with path.open('rb') as source:
        return digest_stream(source)


def path_key(name):
    if not name or name != PurePosixPath(name).as_posix() or name.startswith('/'):
        raise ValueError(f'不安全的 ZIP 路径 {name!r}')
    parts = name.split('/')
    for part in parts:
        if (part in ('', '.', '..') or part.endswith((' ', '.')) or DEVICE_NAME.fullmatch(part)
                or any(c in '\\:<>"|?*' or ord(c) < 32 for c in part)):
            raise ValueError(f'不安全的 ZIP 路径 {name!r}')
    return unicodedata.normalize('NFC', name).casefold()


def unique_paths(names):
    keys = set()
    for name in names:
        key = path_key(name)
        if key in keys:
            raise ValueError(f'重复的 ZIP 路径 {name!r}')
        keys.add(key)
    for key in keys:
        parts = key.split('/')
        if any('/'.join(parts[:i]) in keys for i in range(1, len(parts))):
            raise ValueError(f'ZIP 路径的父目录与文件冲突 {key!r}')


def exclusion(relative):
    name = relative.name.casefold()
    if name == '__pycache__' or name.endswith(('.pyc', '.pyo')):
        return 'Python 字节码缓存'
    if re.search(r'\.(?:sqlite3?|db)-(?:wal|shm|journal)\Z', name):
        return 'SQLite 临时旁车文件'
    if name == 'stop_ocr':
        return '实时 OCR 停止标志'
    if len(relative.parts) == 2 and (name == 'ocr_progress.json' or (name.startswith('ocr_') and name.endswith('.log'))):
        return '实时 OCR 进度或运行日志；用在线备份数据库统计'
    if name.startswith('source_watermther60') and name.endswith('.exe'):
        return '范围外的配套教程程序'
    if relative.suffix.casefold() in VIDEO_EXTENSIONS:
        return '范围外的教程视频'
    return None


def collect(workspace):
    files = {name: workspace / name for name in ROOT_FILES}
    excluded = {}

    def raise_walk_error(error):
        raise error

    graph_dir = workspace / GRAPH
    if graph_dir.resolve() != graph_dir or not graph_dir.is_dir():
        raise ValueError(f'知识图谱目录应为工作区内的实体目录 {graph_dir}')
    for directory, subdirs, names in os.walk(graph_dir, onerror=raise_walk_error):
        parent = Path(directory)
        for name in sorted([*subdirs, *names]):
            path = parent / name
            relative = path.relative_to(workspace)
            member = relative.as_posix()
            reason = exclusion(relative)
            if reason:
                excluded[member] = reason
                if name in subdirs:
                    subdirs.remove(name)
                continue
            if path.resolve() != path or path.is_symlink():
                raise ValueError(f'快照包含符号链接或重解析点 {path}')
            if name not in subdirs:
                files[member] = path
    unique_paths([*files, MANIFEST])
    for name, path in files.items():
        if path.resolve() != path or not path.is_file():
            raise ValueError(f'缺少实体文件 {name}')
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError(f'快照缺少必要文件 {sorted(missing)}')
    return files, excluded


def file_stamp(path):
    info = path.stat()
    return info.st_size, info.st_mtime_ns, info.st_ino, info.st_dev


def no_live_sidecar(path):
    # A WAL header occupies 32 bytes and contains no frames.
    for suffix, permitted in (('-wal', 32), ('-journal', 0)):
        sidecar = path.with_name(path.name + suffix)
        try:
            size = sidecar.stat().st_size
        except FileNotFoundError:
            continue
        if size > permitted:
            raise ValueError(f'{sidecar} 有 {size} 字节。待数据库写入者完成持久化后重试。')


def sqlite_uri(path, immutable=False):
    return path.as_uri() + ('?mode=ro&immutable=1' if immutable else '?mode=ro')


def stable_sqlites(files):
    result = {}
    for name, path in files.items():
        if name == OCR or path.suffix.casefold() not in ('.db', '.sqlite', '.sqlite3'):
            continue
        with path.open('rb') as source:
            is_sqlite = source.read(16) == b'SQLite format 3\x00'
        if not is_sqlite:
            if name in (BASE, INCREMENT, ALPHA):
                raise ValueError(f'非 SQLite 文件 {path}')
            continue
        no_live_sidecar(path)
        before = digest_file(path)
        with closing(sqlite3.connect(sqlite_uri(path, immutable=True), uri=True)) as database:
            if database.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError(f'SQLite 快速完整性检查失败 {path}')
        no_live_sidecar(path)
        result[name] = before
    return result


def binding_info(files_or_rows, json_member):
    """Return consistent database bindings independently of how bytes are read."""
    base_hash = files_or_rows[BASE]['sha256']
    inc_hash = files_or_rows[INCREMENT]['sha256']
    base_pointer = json_member(BASE_MANIFEST)
    if base_pointer['files']['knowledge.sqlite'] != base_hash:
        raise ValueError('knowledge.sqlite 与 snapshot_manifest.json 的 SHA-256 不匹配')
    old_receipt = json_member(AUDIT)
    rounds = [item.get('passed') for item in old_receipt.get('rounds', [])]
    old_matches = old_receipt.get('increment_sha256') == inc_hash
    transcription = json_member(TRANSCRIPTION) if TRANSCRIPTION in files_or_rows else {}
    transcription_matches = transcription.get('increment_sha256') == inc_hash
    if transcription_matches and transcription.get('mode') != 'source_transcription':
        raise ValueError('当前增量收录回执的模式无效')
    if transcription_matches and transcription.get('policy_sha256'):
        if POLICY not in files_or_rows or files_or_rows[POLICY]['sha256'] != transcription['policy_sha256']:
            raise ValueError('原文收录回执与当前 policy.json 的 SHA-256 不匹配')
    if not (transcription_matches or (old_matches and len(rounds) == 3 and all(v is True for v in rounds))):
        raise ValueError('increment.sqlite 未匹配当前收录回执或已通过三轮审核的同版本回执')
    binding = {
        'knowledge': {'sha256': base_hash, 'snapshot_manifest': BASE_MANIFEST},
        'increment': {'sha256': inc_hash, 'current_receipt': TRANSCRIPTION if transcription_matches else AUDIT},
        'historical_audit': {'path': AUDIT, 'increment_sha256': old_receipt.get('increment_sha256'),
                             'matches_packaged_increment': old_matches, 'rounds_passed': rounds},
    }
    if transcription:
        binding['source_transcription'] = {'path': TRANSCRIPTION, 'increment_sha256': transcription.get('increment_sha256'),
                                           'matches_packaged_increment': transcription_matches}
    return binding


def backup_ocr(path, destination, graph_file, timeout):
    started = datetime.now(timezone.utc).isoformat()
    deadline = monotonic() + timeout

    def progress(status, remaining, total):
        if monotonic() > deadline and status != sqlite3.SQLITE_DONE:
            raise TimeoutError(f'OCR 在线备份超过 {timeout} 秒，还余 {remaining}/{total} 页')

    with (closing(sqlite3.connect(sqlite_uri(path), uri=True, timeout=10)) as live,
          closing(sqlite3.connect(destination, uri=True)) as backup):
        live.backup(backup, pages=512, progress=progress, sleep=0.1)
        if backup.execute('PRAGMA journal_mode=DELETE').fetchone()[0].lower() != 'delete':
            raise ValueError('OCR 快照无法切换至独立数据库模式')
        if backup.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('OCR 在线备份的 SQLite 快速完整性检查失败')
        backup.execute('ATTACH DATABASE ? AS graph', (sqlite_uri(graph_file, immutable=True),))
        counts = dict(backup.execute('SELECT status, count(*) FROM results GROUP BY status'))
        empty, = backup.execute("SELECT count(*) FROM results WHERE status='ocr_candidate' AND boxes_json='[]'").fetchone()
        synced, = backup.execute("SELECT count(*) FROM graph.evidence WHERE id LIKE 'ocr:%'").fetchone()
        matched, = backup.execute('''SELECT count(*) FROM results JOIN graph.evidence
                                    ON evidence.id='ocr:' || results.unit_id WHERE results.status='ocr_candidate' ''').fetchone()
    candidate_count = counts.get('ocr_candidate', 0)
    return {'member': OCR, 'method': 'SQLite online backup', 'started_at_utc': started,
            'finished_at_utc': datetime.now(timezone.utc).isoformat(), 'result_status_counts': counts,
            'result_rows': sum(counts.values()), 'candidate_rows': candidate_count, 'empty_candidate_rows': empty,
            'increment_ocr_evidence_rows': synced, 'candidate_rows_present_in_increment': matched,
            'candidate_rows_not_in_increment': candidate_count - matched,
            'increment_ocr_rows_without_matching_snapshot_candidate': synced - matched,
            'status_boundary': 'OCR 识别候选。增量条数为入库证据计数，旧审核仅对应记录版本。'}


def write_member(archive, member, source, origin, method):
    stamp = file_stamp(source)
    with source.open('rb') as reader, archive.open(member, 'w', force_zip64=True) as writer:
        size, sha = digest_stream(reader, writer)
    if stamp != file_stamp(source) or size != stamp[0]:
        raise ValueError(f'打包中途文件改变，保留原发布包并重试 {source}')
    return {'path': member, 'source_relative_path': origin, 'method': method, 'size': size, 'sha256': sha}


def verify_archive(path):
    """Validate ZIP structure, file bytes and packed receipt bindings without extracting."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        unique_paths(entry.orig_filename for entry in entries)
        listing = {}
        for entry in entries:
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if (entry.orig_filename != entry.filename or entry.is_dir() or mode not in (0, stat.S_IFREG)
                    or entry.flag_bits & 1):
                raise ValueError(f'不支持的 ZIP 条目 {entry.orig_filename!r}')
            name = entry.filename
            if name not in {*ROOT_FILES, MANIFEST} and not name.startswith(f'{GRAPH}/'):
                raise ValueError(f'意外的根目录条目 {name}')
            if exclusion(PurePosixPath(name)):
                raise ValueError(f'ZIP 含排除项 {name}')
            listing[name] = entry
        missing = (REQUIRED | {MANIFEST}) - listing.keys()
        if missing:
            raise ValueError(f'ZIP 缺少必要成员 {sorted(missing)}')

        manifest = parse_json(archive.read(MANIFEST))
        version = manifest.pop('package_version_sha256')
        if manifest['schema_version'] != 1 or version != hashlib.sha256(canonical_json(manifest)).hexdigest():
            raise ValueError('快照清单的版本哈希无效')
        manifest['package_version_sha256'] = version
        rows = manifest['files']
        unique_paths(row['path'] for row in rows)
        by_name = {row['path']: row for row in rows}
        if listing.keys() - {MANIFEST} != by_name.keys():
            raise ValueError('ZIP 目录与快照清单成员不同')
        for row in rows:
            name = row['path']
            entry = listing[name]
            if (row['source_relative_path'] != name or type(row['size']) is not int
                    or entry.file_size != row['size'] or not SHA256.fullmatch(row['sha256'])):
                raise ValueError(f'快照清单的文件信息无效 {name}')
            with archive.open(entry) as stream:
                if digest_stream(stream) != (row['size'], row['sha256']):
                    raise ValueError(f'ZIP 成员的 SHA-256 或长度不匹配 {name}')

        expected_bindings = binding_info(by_name, lambda name: parse_json(archive.read(name)))
        if manifest['database_bindings'] != expected_bindings:
            raise ValueError('快照清单与 ZIP 内数据库回执的绑定不一致')
        if manifest['ocr_snapshot']['sha256'] != by_name[OCR]['sha256']:
            raise ValueError('OCR 快照哈希与 ZIP 成员不一致')
    return manifest


def pack(workspace, output, timeout):
    workspace = workspace.resolve(strict=True)
    output = output.absolute()
    output = output.parent.resolve(strict=True) / output.name
    if output.suffix.casefold() != '.zip':
        raise ValueError('输出文件须使用 .zip 结尾')
    if output.is_relative_to(workspace / GRAPH) or output.is_symlink():
        raise ValueError('输出须位于知识图谱源目录之外，且须使用实体文件路径')
    files, excluded = collect(workspace)
    static_before = stable_sqlites(files)
    binding_before = binding_info(
        {BASE: {'sha256': static_before[BASE][1]}, INCREMENT: {'sha256': static_before[INCREMENT][1]},
         **{name: {'sha256': digest_file(files[name])[1]} for name in (TRANSCRIPTION, POLICY) if name in files}},
        lambda name: parse_json(files[name].read_bytes()),
    )

    with tempfile.TemporaryDirectory(prefix='.knowledge-graph-pack-', dir=output.parent) as temp:
        staging = Path(temp)
        copy_db = staging / 'ocr.sqlite'
        temporary_zip = staging / 'snapshot.zip'
        ocr = backup_ocr(files[OCR], copy_db, files[INCREMENT], timeout)
        no_live_sidecar(copy_db)
        snapshot_stamp = file_stamp(copy_db)

        with zipfile.ZipFile(temporary_zip, 'w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=4, allowZip64=True) as archive:
            rows = []
            for member, source in sorted(files.items()):
                if member in static_before:
                    no_live_sidecar(source)
                packed = copy_db if member == OCR else source
                method = ('sqlite_online_backup' if member == OCR else
                          'verified_sqlite_byte_copy' if member in static_before else 'byte_copy')
                rows.append(write_member(archive, member, packed, member, method))
            by_name = {row['path']: row for row in rows}
            for member, before in static_before.items():
                source = files[member]
                no_live_sidecar(source)
                written = by_name[member]
                if before != (written['size'], written['sha256']) or before != digest_file(source):
                    raise ValueError(f'SQLite 复制前后字节不一致 {member}')
                no_live_sidecar(source)

            binding = binding_info(by_name, lambda name: parse_json(files[name].read_bytes()))
            if binding != binding_before or snapshot_stamp != file_stamp(copy_db):
                raise ValueError('打包中途数据库绑定或备份变动')
            ocr['sha256'] = by_name[OCR]['sha256']
            ocr['size'] = by_name[OCR]['size']
            manifest = {
                'schema_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'workspace_root_at_capture': str(workspace), 'graph_member_root': GRAPH,
                'database_bindings': binding, 'ocr_snapshot': ocr, 'files': rows,
                'exclusions': {'paths': excluded, 'root_trees': {
                    '教材手册': '原始资料树；图谱来源档案仍保留其原路径',
                    '设备设计': '原始资料树；图谱来源档案仍保留其原路径',
                }, 'python_cache_directories': '按目录排除，未逐个枚举其后代',
                    'live_ocr_progress': '实时文件排除；历史交接中的观察值保留原记录'},
                'package_version_hash_definition': '清单去除 package_version_sha256 后的排序键紧凑 UTF-8 JSON 的 SHA-256',
            }
            manifest['package_version_sha256'] = hashlib.sha256(canonical_json(manifest)).hexdigest()
            archive.writestr(MANIFEST, canonical_json(manifest))

        verified = verify_archive(temporary_zip)
        os.replace(temporary_zip, output)
    return verified


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pack_args = commands.add_parser('pack', help='创建并校验图谱快照 ZIP')
    pack_args.add_argument('--workspace', type=Path, default=Path.cwd(), help='含知识图谱的工作目录')
    pack_args.add_argument('--output', type=Path, required=True, help='ZIP 目标路径，父目录须存在')
    pack_args.add_argument('--ocr-backup-timeout', type=int, default=180, help='SQLite OCR 在线备份时限（秒）')
    verify_args = commands.add_parser('verify', help='校验 ZIP 文件结构、哈希和回执绑定')
    verify_args.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'pack':
            if args.ocr_backup_timeout < 1:
                parser.error('--ocr-backup-timeout 须为正整数')
            archive = args.output
            manifest = pack(args.workspace, archive, args.ocr_backup_timeout)
        else:
            archive = args.archive
            manifest = verify_archive(archive)
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error, zipfile.BadZipFile) as error:
        parser.exit(1, f'{args.command}: {error}\n')
    print(json.dumps({'archive': str(archive.resolve()), 'file_count': len(manifest['files']),
                      'package_version_sha256': manifest['package_version_sha256'],
                      'ocr_snapshot': manifest['ocr_snapshot']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
