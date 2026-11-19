"""Project preference for adding the equipment knowledge graph to general searches."""
import json
import os
from pathlib import Path
import tempfile


def project_setting(root, enabled=None):
    if enabled is not None and type(enabled) is not bool:
        raise ValueError("equipment_graph must be true or false")
    if root is None:
        return enabled is True
    path = Path(root) / ".aspen-equipment-graph.json"
    if enabled is None:
        try:
            saved = json.loads(path.read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            return False
        if not isinstance(saved, dict) or type(saved.get("enabled")) is not bool:
            raise ValueError("Invalid equipment graph setting in the project directory")
        return saved["enabled"]
    # Replace the entire preference atomically; only an explicit choice writes.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".equipment-graph-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({"enabled": enabled}, handle)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return enabled
