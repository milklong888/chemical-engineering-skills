from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import database_authority


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the public database authority registry and, unless "
            "--inventory-only is used, hash/check every active database."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PACKAGE_ROOT,
        help="Package root containing data/ and knowledge_graph/.",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="Validate and print registry state without opening large SQLite files.",
    )
    parser.add_argument("--compact", action="store_true")
    arguments = parser.parse_args()
    try:
        result = (
            database_authority.registry_inventory(arguments.root)
            if arguments.inventory_only
            else database_authority.audit_active_databases(arguments.root)
        )
    except database_authority.DatabaseAuthorityError as exc:
        result = {
            "schema": database_authority.AUDIT_SCHEMA,
            "status": "FAIL",
            "error": str(exc),
        }
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                indent=None if arguments.compact else 2,
            )
        )
        return 1
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=None if arguments.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
