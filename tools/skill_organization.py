#!/usr/bin/env python3
"""Read-only, partial file-dependency inventory; never a Skill execution router."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict, deque
import hashlib
from itertools import islice, product
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

# Direct CLI use must not populate the source checkout with helper bytecode.
sys.dont_write_bytecode = True
if __package__:
    from .verify_release import ReleaseError, SKILLS_PREFIX, relative_path, reject_links, safe_target
else:
    from verify_release import ReleaseError, SKILLS_PREFIX, relative_path, reject_links, safe_target

EXCLUDED = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
            "node_modules", ".venv", ".env", "credentials", "source_pages", "raw_l0"}
MAX_FILES = 20000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
FILE_END = re.compile(r"\.(?:md|py|json|jsonl|ya?ml|toml|csv|txt|schema|bkp|inp|apwz?|edr|fx3|cn2)$", re.I)
BLIND_SPOTS = [
    "Static references are review candidates, not proof of reading, execution or engineering impact.",
    "Directory membership identifies related Skills; canonical factual ownership is not inferred.",
    "Markdown parsing covers simple inline/reference links and single-backtick file paths, not full CommonMark/HTML.",
    "Python resolution covers repository/source-directory imports and simple file-anchored paths; runtime sys.path, CWD, dynamic imports and generated paths may differ.",
    "Rebound or globally mutable path names and dependent aliases remain unresolved; bounded lexical candidates are not control-flow or future-value predictions.",
    "JSON/YAML data semantics, shell commands, COM objects, package installation mirrors, and implicit host loading are not traced.",
    "Excluded trees and non-Markdown/Python payloads are not parsed; unresolved edges require review.",
    "This is a filesystem snapshot, not an atomic checkout lock; recheck identities before applying changes.",
]


def _root(value: str | Path) -> Path:
    path = Path(value).absolute()
    reject_links(path)
    if not path.is_dir():
        raise ReleaseError("Repository root must be an existing directory")
    return path.resolve()


def _relative(value: str) -> str:
    value = relative_path(value)
    if any(part.casefold() in EXCLUDED for part in PurePosixPath(value).parts):
        raise ReleaseError("Path is in an excluded tree")
    return value


def _files(root: Path) -> list[str]:
    found: list[str] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        # Reject links even when their names belong to excluded trees.
        for name in sorted(dirs + files):
            child = Path(directory) / name
            info = child.lstat()
            if (stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
                raise ReleaseError("Symlink/junction/reparse point not accepted: " + str(child))
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise ReleaseError("Nonregular filesystem entry not accepted: " + str(child))
        dirs[:] = sorted(name for name in dirs if name.casefold() not in EXCLUDED)
        for name in sorted(files):
            rel = (Path(directory) / name).relative_to(root).as_posix()
            if any(part.casefold() in EXCLUDED for part in PurePosixPath(rel).parts):
                continue
            _relative(rel)
            found.append(rel)
            if len(found) > MAX_FILES:
                raise ReleaseError("File inventory limit exceeded")
    return sorted(found)


def _membership(path: str, ids: set[str]) -> str | None:
    if path.startswith(SKILLS_PREFIX):
        name = path[len(SKILLS_PREFIX):].split("/", 1)[0]
        if name in ids:
            return name
    return None


class Scanner:
    def __init__(self, root: Path, files: list[str]):
        self.root, self.files = root, set(files)
        self.directories = {str(parent) for path in files for parent in PurePosixPath(path).parents}
        self.edges: list[dict] = []
        self.issues: list[dict] = []

    def edge(self, source: str, line: int, kind: str, reference: str,
             target: str | None = None, reason: str | None = None,
             candidates: list[str] | None = None) -> None:
        if target is not None:
            try:
                target = _relative(target)
            except (ReleaseError, OSError):
                target, reason = None, "unsafe_reference_rejected"
        status = "resolved" if target in self.files else "missing" if target else "unresolved"
        if target in self.directories:
            status, reason = "directory_not_expanded", "directory_reference_not_expanded"
        self.edges.append({"source": source, "line": line, "type": kind,
                           "reference": reference[:300], "target": target,
                           "status": status, "reason": reason,
                           "candidate_targets": sorted(set(candidates or []))})

    def local_reference(self, source: str, line: int, kind: str, value: str) -> None:
        try:
            url = urlsplit(value)
            if re.match(r"^[A-Za-z]:", value):
                raise ReleaseError("Absolute filesystem reference")
            if url.scheme or url.netloc:
                # External links are outside this file dependency inventory.
                return
            if not url.path:
                return
            path = unquote(url.path)
            if path.startswith("/") or "\\" in path or ":" in path or "\x00" in path:
                raise ReleaseError("Nonportable reference")
            combined = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
            target = _relative(combined)
            self.edge(source, line, kind, value, target)
        except (ValueError, OSError):
            self.edge(source, line, kind, value, reason="unsafe_reference_rejected")

    def markdown(self, source: str, text: str) -> None:
        in_fence = False
        for line, content in enumerate(text.splitlines(), 1):
            if re.match(r"^\s*(```|~~~)", content):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            destinations: list[tuple[str, str]] = []
            for match in re.finditer(r"!?\[[^\]\n]*\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+['\"][^\n]*?['\"])?\s*\)", content):
                destinations.append(("markdown_link", match.group(1).strip("<>")))
            definition = re.match(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", content)
            if definition:
                destinations.append(("markdown_reference_definition", definition.group(1).strip("<>")))
            for match in re.finditer(r"(?<!`)`([^`\n]+)`(?!`)", content):
                value = match.group(1)
                if FILE_END.search(value) and not re.search(r"\s", value):
                    destinations.append(("markdown_code_path", value))
            for kind, value in destinations:
                if kind != "markdown_code_path":
                    self.local_reference(source, line, kind, value)
                    continue
                # Unlike real links, prose code paths may use repository-root
                # conventions. Keep ambiguity explicit rather than invent CWD.
                candidates = []
                for base in (posixpath.dirname(source), ""):
                    try:
                        if "\\" in value or ":" in value or value.startswith("/"):
                            raise ReleaseError("Unsafe code path")
                        candidates.append(_relative(posixpath.normpath(posixpath.join(base, value))))
                    except ReleaseError:
                        continue
                existing = sorted(set(candidates) & self.files)
                self.edge(source, line, kind, value,
                          target=existing[0] if len(existing) == 1 else None,
                          reason="static_code_path_candidate" if len(existing) == 1 else
                          "ambiguous_code_path" if existing else
                          "unanchored_code_path_missing" if candidates else "unsafe_reference_rejected",
                          candidates=candidates)

    def import_edge(self, source: str, node: ast.AST, module: str,
                    level: int = 0, names: list[str] | None = None) -> None:
        reference = "." * level + module
        if not level and module.split(".")[0] in sys.stdlib_module_names:
            return
        parent = PurePosixPath(source).parent
        if level:
            for _ in range(level - 1):
                if parent == PurePosixPath("."):
                    self.edge(source, node.lineno, "python_import", reference,
                              reason="relative_import_outside_root")
                    return
                parent = parent.parent
            bases = [parent / module.replace(".", "/")]
        else:
            bases = list(dict.fromkeys([parent / module.replace(".", "/"),
                                       PurePosixPath(module.replace(".", "/"))]))
        groups = []
        all_candidates = []
        for base in bases:
            paths = []
            if str(base) != ".":
                paths += [str(base) + ".py", str(base / "__init__.py")]
            paths += [str(base / name) + ".py" for name in names or [] if name != "*"]
            paths += [str(base / name / "__init__.py") for name in names or [] if name != "*"]
            safe = []
            for path in paths:
                try:
                    safe.append(_relative(path))
                except ReleaseError:
                    continue
            all_candidates.extend(safe)
            existing = sorted(set(safe) & self.files)
            if existing:
                groups.append(existing)
        distinct = {tuple(group) for group in groups}
        if len(distinct) == 1:
            for target in next(iter(distinct)):
                self.edge(source, node.lineno, "python_import", reference, target,
                          reason="static_local_candidate_not_runtime_resolution")
                for parent in PurePosixPath(target).parents:
                    initializer = str(parent / "__init__.py")
                    if parent != PurePosixPath(".") and initializer != target and initializer in self.files:
                        self.edge(source, node.lineno, "python_package_init", reference, initializer,
                                  reason="possible_package_initialization")
        else:
            self.edge(source, node.lineno, "python_import", reference,
                      reason="ambiguous_local_import" if distinct else "external_or_unresolved_import",
                      candidates=all_candidates)
        # An existing package initializer does not prove that every imported
        # member is present. It might be an exported attribute, or a missing
        # submodule: retain the file candidates without guessing which.
        for name in names or []:
            if name == "*":
                continue
            members = []
            for base in bases:
                for path in (str(base / name) + ".py", str(base / name / "__init__.py")):
                    try:
                        members.append(_relative(path))
                    except ReleaseError:
                        continue
            if not set(members) & self.files:
                self.edge(source, node.lineno, "python_import_member", reference + " import " + name,
                          reason="exported_attribute_or_missing_submodule_unresolved", candidates=members)

    def python(self, source: str, text: str) -> None:
        try:
            tree = ast.parse(text, filename=source)
        except (SyntaxError, ValueError, RecursionError) as exc:
            self.issues.append({"source": source, "code": "python_parse_failed", "detail": type(exc).__name__})
            return
        # Only a small syntactic subset is interpreted, never eval/import/run.
        known: dict[str, PurePosixPath] = {"__file__": PurePosixPath(source)}
        uncertain_paths: dict[str, set[PurePosixPath]] = defaultdict(set)

        def module_nodes(node: ast.AST):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                return
            yield node
            for child in ast.iter_child_nodes(node):
                yield from module_nodes(child)

        counts = Counter(node.id for node in module_nodes(tree)
                         if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)))
        rebound = {name for name, count in counts.items() if count > 1}
        rebound.update(name for node in ast.walk(tree) if isinstance(node, ast.Global) for name in node.names)
        if counts.get("__file__"):
            known.pop("__file__", None)

        def path_value(node: ast.AST, blocked: set[str], values=None) -> PurePosixPath | None:
            values = known if values is None else values
            if isinstance(node, ast.Name):
                return values.get(node.id) if node.id not in blocked else None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "Path" and len(node.args) == 1:
                    return path_value(node.args[0], blocked, values)
                if isinstance(node.func, ast.Attribute) and node.func.attr in {"resolve", "absolute"} and not node.args:
                    return path_value(node.func.value, blocked, values)
                if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
                    base = path_value(node.func.value, blocked, values)
                    if base is not None and all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in node.args):
                        return base.joinpath(*(arg.value for arg in node.args))
            if isinstance(node, ast.Attribute) and node.attr == "parent":
                base = path_value(node.value, blocked, values)
                return base.parent if base is not None and base != PurePosixPath(".") else None
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
                base = path_value(node.value.value, blocked, values)
                index = node.slice.value if isinstance(node.slice, ast.Constant) else None
                if base is not None and type(index) is int and 0 <= index < len(base.parents):
                    return base.parents[index]
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                base = path_value(node.left, blocked, values)
                if base is not None and isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
                    return base / node.right.value
            return None

        def path_candidates(node: ast.AST, blocked: set[str]) -> list[str]:
            names = sorted({part.id for part in ast.walk(node) if isinstance(part, ast.Name)
                            and part.id not in blocked and uncertain_paths.get(part.id)})
            if not names:
                return []
            choices = [sorted(uncertain_paths[name]) for name in names]
            found = set()
            for index, combination in enumerate(islice(product(*choices), 33)):
                if index == 32:
                    self.issues.append({"source": source, "code": "path_candidate_limit", "line": node.lineno})
                    break
                value = path_value(node, blocked, {**known, **dict(zip(names, combination))})
                if value is not None:
                    try:
                        found.add(_relative(posixpath.normpath(value.as_posix())))
                    except ReleaseError:
                        continue
            return sorted(found)

        for statement in tree.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        value = path_value(statement.value, set())
                        candidates = path_candidates(statement.value, set()) if value is None else []
                        if target.id in rebound or candidates:
                            known.pop(target.id, None)
                            uncertain_paths[target.id].update(PurePosixPath(path) for path in candidates)
                            if value is not None:
                                uncertain_paths[target.id].add(value)
                            if candidates and any(FILE_END.search(path) for path in candidates):
                                self.edge(source, statement.lineno, "python_path_definition",
                                          ast.unparse(statement.value), reason="rebound_path_or_dependent_alias",
                                          candidates=candidates)
                        elif value is not None:
                            known[target.id] = value
                            if FILE_END.search(value.as_posix()) and value.as_posix() != source:
                                self.edge(source, statement.lineno, "python_path_definition",
                                          ast.unparse(statement.value), posixpath.normpath(value.as_posix()),
                                          reason="static_path_definition_not_execution")
                        else:
                            known.pop(target.id, None)

        def visit(node: ast.AST, blocked: set[str]) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                local = {child.id for child in ast.walk(node) if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del))}
                local.update(child.arg for child in ast.walk(node) if isinstance(child, ast.arg))
                blocked = blocked | local
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.import_edge(source, node, alias.name)
            elif isinstance(node, ast.ImportFrom):
                self.import_edge(source, node, node.module or "", node.level, [alias.name for alias in node.names])
            if isinstance(node, ast.Call):
                func = node.func
                name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
                expression = None
                if name == "open" and isinstance(func, ast.Attribute):
                    expression = func.value
                elif name in {"Path", "open", "run_path"} and node.args:
                    expression = node.args[0]
                elif name == "spec_from_file_location" and len(node.args) >= 2:
                    expression = node.args[1]
                elif name in {"read_text", "read_bytes"} and isinstance(func, ast.Attribute):
                    expression = func.value
                if expression is not None:
                    value = path_value(expression, blocked)
                    raw = ast.unparse(expression)
                    if value is not None:
                        target = posixpath.normpath(value.as_posix())
                        if target != source and target not in {".", ""}:
                            self.edge(source, node.lineno, "python_file_reference", raw, target,
                                      reason="static_file_anchored_expression")
                    elif not (isinstance(expression, ast.Name) and expression.id == "__file__"):
                        candidates = path_candidates(expression, blocked)
                        self.edge(source, node.lineno, "python_file_reference", raw,
                                  reason="rebound_path_or_dependent_alias" if candidates else "dynamic_path_or_runtime_cwd_required",
                                  candidates=candidates)
                if name in {"import_module", "__import__"}:
                    self.edge(source, node.lineno, "python_dynamic_import", name,
                              reason="dynamic_import_not_resolved")
            for child in ast.iter_child_nodes(node):
                visit(child, blocked)
        visit(tree, set())


def inventory(root: str | Path) -> dict:
    root = _root(root)
    if not safe_target(root, SKILLS_PREFIX.rstrip("/")).is_dir():
        raise ReleaseError("Existing product skills directory is required")
    files = _files(root)
    entries = [path for path in files if path.startswith(SKILLS_PREFIX)
               and path.count("/") == SKILLS_PREFIX.count("/") + 1
               and path.endswith("/SKILL.md")]
    if not entries:
        raise ReleaseError("No Skill entries found in the product's existing skills directory")
    scanner = Scanner(root, files)
    nodes = []
    texts = {}
    total = 0
    for path in files:
        if PurePosixPath(path).suffix.lower() not in {".md", ".py"}:
            continue
        target = safe_target(root, path)
        size = target.stat().st_size
        if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
            scanner.issues.append({"source": path, "code": "text_size_limit_not_parsed"})
            continue
        with target.open("rb") as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ReleaseError("Source grew beyond the text limit during read")
        total += len(data)
        digest = hashlib.sha256(data).hexdigest()
        nodes.append({"path": path, "sha256": digest, "bytes": len(data)})
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            scanner.issues.append({"source": path, "code": "text_decode_failed"})
            continue
        if path in entries:
            texts[path] = text
        if path.lower().endswith(".md"):
            scanner.markdown(path, text)
        else:
            try:
                scanner.python(path, text)
            except RecursionError:
                scanner.issues.append({"source": path, "code": "python_analysis_recursion_limit"})
    skills = []
    for path in entries:
        skill_id = PurePosixPath(path).parent.name
        match = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", texts.get(path, ""), re.M)
        declared = match.group(1) if match else None
        if declared != skill_id:
            scanner.issues.append({"source": path, "code": "skill_name_missing_or_mismatched"})
        skills.append({"skill_id": skill_id, "entry": path, "declared_name": declared})
    edges = sorted({json.dumps(edge, sort_keys=True, ensure_ascii=False): edge for edge in scanner.edges}.values(),
                   key=lambda edge: (edge["source"], edge["line"], edge["type"], edge["target"] or "", edge["reference"]))
    ids = {skill["skill_id"] for skill in skills}
    for node in nodes:
        node["skill_membership"] = _membership(node["path"], ids)
    return {"schema": "skill-organization-inventory-v1", "read_only": True,
            "semantic_routing_proven": False, "execution_proven": False,
            "complete_dependency_graph": False, "skills": skills, "skill_count": len(skills),
            "files": nodes, "edges": edges,
            "unresolved_edges": [edge for edge in edges if edge["status"] != "resolved"],
            "issues": scanner.issues, "blind_spots": BLIND_SPOTS,
            "coverage": {"enumerated_files": len(files), "fingerprinted_text_files": len(nodes),
                         "parsed_text_bytes": total, "expected_product_skill_count": 19,
                         "skill_count_matches_product": len(skills) == 19},
            "canonical_rule_owner_map": SKILLS_PREFIX + "chemical-engineering-expert/references/CANONICAL_RULE_OWNERSHIP.md"}


def impact(root: str | Path, changed: list[str]) -> dict:
    root = _root(root)
    if not changed:
        raise ReleaseError("At least one changed file is required")
    changed = sorted({_relative(path) for path in changed})
    for path in changed:
        target = safe_target(root, path)
        if target.is_dir():
            raise ReleaseError("Changed paths must name files, not directories")
    result = inventory(root)
    consumers: dict[str, list[dict]] = defaultdict(list)
    for edge in result["edges"]:
        # Missing but explicit references also matter for deleted/new files.
        if edge["target"] is not None:
            consumers[edge["target"]].append(edge)
    reached = set(changed)
    queue = deque(changed)
    witnesses = {}
    while queue:
        target = queue.popleft()
        for edge in consumers[target]:
            source = edge["source"]
            if source not in reached:
                reached.add(source)
                witnesses[source] = edge
                queue.append(source)
    ids = {skill["skill_id"] for skill in result["skills"]}
    related = sorted({member for path in reached if (member := _membership(path, ids))})
    result.update({"schema": "skill-organization-impact-v1", "changed": changed,
                   "changed_missing": [path for path in changed if not safe_target(root, path).exists()],
                   "affected_files": sorted(reached), "related_skills": related,
                   "direct_consumers": [edge for path in changed for edge in consumers[path]],
                   "propagation_witnesses": [witnesses[path] for path in sorted(witnesses)],
                   "unresolved_edges_in_reached_files": [edge for edge in result["unresolved_edges"] if edge["source"] in reached],
                   "possible_consumers_from_unresolved_edges": [edge for edge in result["unresolved_edges"]
                                                               if set(edge["candidate_targets"]) & reached],
                   "impact_meaning": "Observed reverse file references and directory membership only; review candidates, not automatic change or acceptance."})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory", "impact"])
    parser.add_argument("--root", type=Path, default=Path(__file__).absolute().parents[1])
    parser.add_argument("--changed", action="append", default=[], help="Portable repository-relative file; repeat for multiple changes")
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory" and args.changed:
            raise ReleaseError("--changed is only valid for impact")
        result = inventory(args.root) if args.command == "inventory" else impact(args.root, args.changed)
    except (ReleaseError, OSError) as exc:
        print(json.dumps({"schema": "skill-organization-error-v1", "error": str(exc), "read_only": True}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
