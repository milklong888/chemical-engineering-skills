"""Read-only integration runner; real cases/plans must remain outside this package.

Manifest schema: {"cases": [{"source": "...", "export4": "...", "plan": "...",
                           "readback": "..."}]}. Paths resolve from the manifest
directory. Readback is optional. Generated INP exists only in memory. The receipt
contains hashes/counts, never private file paths or process coordinates.
"""
import argparse
import json
from pathlib import Path

if __package__:
    from .pfs_layout import Document, LayoutError, apply_layout, require, sha, verify_layout
else:
    from pfs_layout import Document, LayoutError, apply_layout, require, sha, verify_layout


def run_case(source, export4, plan, readback=None):
    output = apply_layout(source, export4, plan)
    document = Document(output)
    result = {"source_sha256": sha(source), "export4_sha256": sha(export4),
              "generated_in_memory_sha256": sha(output), "block_count": len(document.blocks),
              "stream_count": len(document.streams), "apply_and_reparse": True,
              "native_export_readback_compared": readback is not None,
              "simulation_acceptance": "NOT_CLAIMED"}
    if readback is not None:
        result["readback"] = verify_layout(output, readback, export4)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    require(set(manifest) == {'cases'} and manifest['cases'], 'Expected nonempty cases manifest')
    results = []
    for case in manifest['cases']:
        require(set(case) in ({'source', 'export4', 'plan'}, {'source', 'export4', 'plan', 'readback'}), 'Unexpected private manifest fields')
        def read(key):
            return (args.manifest.parent / case[key]).read_bytes()
        results.append(run_case(read('source'), read('export4'), json.loads(read('plan').decode('utf-8-sig')),
                                read('readback') if 'readback' in case else None))
    print(json.dumps({'case_count': len(results), 'cases': results, 'scope': 'offline; no Aspen session started'}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (LayoutError, OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('Rejected: ' + str(error))
