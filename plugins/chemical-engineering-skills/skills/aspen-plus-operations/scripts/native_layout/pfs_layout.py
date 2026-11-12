"""Offline, fail-closed editing of Aspen Export(18) comment graphics.

Run ``python pfs_layout.py --help``. This tool never opens Aspen, changes a
physical card, or certifies a simulation. All coordinates use x-right/y-up.
The input's complete configuration and icon definitions are preserved.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import sys

NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"
MATRICES = {
    0: ((1, 0), (0, 1)), 1: ((-1, 0), (0, 1)),
    2: ((1, 0), (0, -1)), 3: ((0, -1), (1, 0)),
    4: ((0, 1), (-1, 0)), 5: ((-1, 0), (0, -1)),
    6: ((0, -1), (-1, 0)), 7: ((0, 1), (1, 0)),
}
DIRECTIONS = {"l": (-1, 0), "r": (1, 0), "u": (0, 1), "d": (0, -1)}
EPS = 1e-5


class LayoutError(ValueError):
    """Unsupported or inconsistent evidence; no output should be committed."""


def require(condition, message):
    if not condition:
        raise LayoutError(message)


def finite(value):
    require(isinstance(value, (int, float)) and not isinstance(value, bool), "Expected number")
    require(math.isfinite(value), "Non-finite coordinate")
    return float(value)


def pair(value):
    require(isinstance(value, (tuple, list)) and len(value) == 2, "Expected coordinate pair")
    return tuple(finite(x) for x in value)


def fnum(value):
    value = float(value.replace("D", "E").replace("d", "e"))
    require(math.isfinite(value), "Non-finite source coordinate")
    return value


def mv(matrix, point):
    return tuple(sum(matrix[i][j] * point[j] for j in range(2)) for i in range(2))


def inverse(matrix):
    return tuple(zip(*matrix))  # Every supported D4 matrix is orthogonal.


def fmt(value):
    require(math.isfinite(value), "Non-finite serialized coordinate")
    return f"{value:.9f}"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_number(literal):
    """Canonical numeric value using tuple operations, never Decimal context arithmetic."""
    value = Decimal(literal.replace("D", "E").replace("d", "e"))
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    if not any(digits):
        return '0e0'
    while len(digits) > 1 and digits[-1] == 0:
        digits.pop(); exponent += 1
    return ('-' if sign else '') + ''.join(map(str, digits)) + 'e' + str(exponent)


def lexical_tokens(text):
    """Keep every quoted span opaque, including quotes immediately after KEY=."""
    out, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1; continue
        start = i
        if text[i] in ('"', "'"):
            quote = text[i]; i += 1
            while i < len(text):
                if text[i] == '\\':
                    require(i + 1 < len(text), 'Incomplete quoted escape')
                    i += 2
                elif text[i] == quote:
                    if i + 1 < len(text) and text[i+1] == quote:
                        i += 2
                    else:
                        i += 1; break
                else:
                    i += 1
            else:
                raise LayoutError('Unterminated physical quoted string')
            out.append(text[start:i])
        else:
            while i < len(text) and not text[i].isspace() and text[i] not in ('"', "'"):
                i += 1
            item = text[start:i]
            if item == '&':
                continue
            item = re.sub(r"(?<![A-Za-z0-9_.$+\-])" + NUM + r"(?![A-Za-z0-9_.$+\-])",
                          lambda m: exact_number(m[0]), item)
            out.append(item)
    return tuple(out)


def physical_tokens(raw, *, allow_elink=False):
    """All genuine cards, including report cards after graphics; no prefix shortcut."""
    lines = [x for x in raw.decode("latin1").splitlines() if not x.lstrip().startswith(";")]
    markers = [i for i, x in enumerate(lines) if x.strip() == "E_LINK"]
    if markers:
        require(allow_elink and len(markers) == 1, "Unexpected E_LINK marker")
        require(not any(x.strip() for x in lines[markers[0] + 1:]), "E_LINK is not the final genuine record")
        lines.pop(markers[0])
    return lexical_tokens("\n".join(lines))


LEGEND_FIELDS = ("LEGEND", "Version:", "Unfixed", "# of PFS Objects", "VIEWPORT", "LAYOUT", "TableFormat", "Pages", "PAGESETUP", "PAPERSIZE", "PAPERSOURCE", "ORIENTATION", "PRINTPAGENO", "LEFTMARGIN", "RIGHTMARGIN", "TOPMARGIN", "BOTTOMMARGIN", "VISIBILITY", "PFDFLAG", "PFDMODE", "SCALE")


def legend_records(text):
    """Strict supported empty-legend schema; record order may change on export."""
    records = {}
    for line in text.splitlines():
        matches = [key for key in LEGEND_FIELDS if line == key or line.startswith(key + ' ')]
        require(len(matches) == 1, 'Unsupported LEGEND/object record')
        key = matches[0]
        require(key not in records, 'Duplicate LEGEND field: ' + key)
        records[key] = lexical_tokens(line[len(key):].strip())
    for key in ('LEGEND', 'Version:', 'Unfixed', '# of PFS Objects', 'VIEWPORT', 'LAYOUT', 'TableFormat', 'Pages', 'PAGESETUP', 'SCALE'):
        require(key in records, 'Missing LEGEND field: ' + key)
    require(records['Version:'] == (exact_number('2'),), 'Unsupported LEGEND version')
    require(records['# of PFS Objects'] == ('=', exact_number('0')), 'Nonempty LEGEND unsupported')
    for key in ('LEGEND', 'Unfixed', 'LAYOUT', 'PAGESETUP'):
        require(not records[key], 'Unexpected LEGEND header value: ' + key)
    viewport = line_pair4('VIEWPORT', text)
    require(viewport[0] < viewport[2] and viewport[3] < viewport[1], 'Invalid LEGEND VIEWPORT bounds')
    return records


def line_pair4(key, text):
    match = unique_match(r'^' + re.escape(key) + r' (' + NUM + r') (' + NUM + r') (' + NUM + r') (' + NUM + r')$', text, key)
    return tuple(fnum(x) for x in match.groups())


def unique_match(pattern, text, label):
    matches = list(re.finditer(pattern, text, re.M))
    require(len(matches) == 1, f"Expected exactly one {label}")
    return matches[0]


def line_pair(key, text):
    match = unique_match(r"^" + re.escape(key) + r" (" + NUM + r") (" + NUM + r")$", text, key)
    return tuple(fnum(x) for x in match.groups())


def set_pair(key, text, value):
    line_pair(key, text)
    return re.sub(r"(?m)^" + re.escape(key) + r" .*?$", key + " " + " ".join(map(fmt, value)), text, count=1)


def binding(raw):
    text = raw.decode("latin1").replace("\r", "")
    text = "\n".join(x for x in text.splitlines() if not x.lstrip().startswith(";"))
    flow = unique_match(r"^FLOWSHEET[^\n]*$", text, "FLOWSHEET")
    body = text[flow.end():].lstrip("\n")
    end = re.search(r"(?m)^\S", body)
    body = body[:end.start()] if end else body
    body = body.replace("&\n", " ")
    entries = re.findall(r"(?ms)^\s+BLOCK (\S+) IN=(.*?) OUT=(.*?)(?=\n\s+BLOCK |\Z)", body)
    require(entries, "No supported FLOWSHEET BLOCK IN/OUT bindings")
    blocks, sources, destinations = {}, {}, {}
    for name, ins, outs in entries:
        require(name not in blocks, f"Duplicate physical block {name}")
        links = {"in": ins.split(), "out": outs.split()}
        require(all(re.fullmatch(r"[A-Za-z0-9_.$+\-]+", x) for v in links.values() for x in v), "Unsupported physical stream binding syntax")
        blocks[name] = links
        for values, target in [(links["in"], destinations), (links["out"], sources)]:
            for stream in values:
                require(stream not in target, f"Ambiguous stream binding {stream}")
                target[stream] = name
    return blocks, sources, destinations


@dataclass
class Block:
    name: str
    text: str
    at: tuple
    scale: float
    modifier: int
    label: tuple
    icon: str


@dataclass
class Route:
    points: list
    direction: str | None
    displacement: tuple
    connection: float | None


def parse_route(text):
    points, direction, displacement, connection = [], None, (0.0, 0.0), None
    seen_d = seen_c = False
    closed = False
    for line in text.splitlines():
        if not line.strip():
            continue
        require(not closed, "Data after route terminator")
        if line == "$ $ 0.0 0.0":
            closed = True
            continue
        d = re.fullmatch(r"\$ D (" + NUM + r") (" + NUM + r")", line)
        c = re.fullmatch(r"\$ C (" + NUM + r") (" + NUM + r")", line)
        pt = re.fullmatch(r"([rxy t]) ([rludxy0]) (" + NUM + r") (" + NUM + r") ([01])", line)
        if d:
            require(direction is not None and not seen_d and not seen_c, "Misordered or duplicate $D")
            displacement = tuple(fnum(x) for x in d.groups()); seen_d = True
        elif c:
            require(direction is not None and not seen_c, "Misordered or duplicate $C")
            require(fnum(c[2]) == 0, "Unsupported $C auxiliary value")
            connection = fnum(c[1]); require(connection in (0, 1), "Unsupported $C value"); seen_c = True
        elif pt:
            require(direction is None and not seen_d and not seen_c, "Points after terminal")
            kind, direct, x, y, flag = pt.groups()
            require(kind.strip() and (bool(points) or kind == "r"), "Route must begin at r")
            require(not points or kind != "r", "Repeated route root")
            require(flag == "0", "Pinned/flagged stream point not supported")
            points.append((fnum(x), fnum(y)))
            if kind == "t":
                require(direct in DIRECTIONS, "Invalid terminal direction"); direction = direct
        else:
            raise LayoutError(f"Unsupported route record: {line}")
    require(closed, "Missing route terminator")
    if points:
        require(len(points) >= 2 and direction is not None and seen_c, "Incomplete material route")
        require(not seen_d or connection == 0, "$D requires witnessed $C 0 syntax")
    else:
        require(not seen_d and not seen_c, "Metadata on empty route")
    return Route(points, direction, displacement, connection)


@dataclass
class Stream:
    name: str
    text: str
    header: str
    secondary: str
    routes: dict
    terminal: int
    path: list


def parse_stream(text):
    name = unique_match(r"^ID: (\S+)$", text, "stream ID")[1]
    unique_match(r"^Version: 2$", text, "stream Version 2")
    typ = unique_match(r"^TYPE (\d+) TERMINAL ([012])$", text, "material stream TYPE")
    require(typ[1] == "0", "Only material TYPE 0 streams are supported")
    matches = list(re.finditer(r"(?m)^ROUTE ([01]) ([012])$", text))
    require(len(matches) == 6 and [(m[1], m[2]) for m in matches] == [(str(a), str(b)) for b in range(3) for a in range(2)], "Unsupported route layer schema")
    first_extra = text.rfind("\nAt ", matches[1].end(), matches[2].start())
    require(first_extra >= 0, "Missing secondary layer header")
    routes = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        part = text[m.end():end]
        if i in (1, 3):
            cut = part.find("\nAt ")
            require(cut >= 0, "Missing additional layer metadata")
            part = part[:cut]
        route = parse_route(part)
        if m[2] != "0":
            require(not route.points, "Nonempty additional route layer unsupported")
        else:
            routes[int(m[1])] = route
    header = text[:matches[0].start()]
    for line in header.splitlines()[1:]:
        require(re.match(r"^(ID:|Version:|Flag |GLOBAL |STYLE |TYPE |At |Label At )", line), f"Unsupported stream header: {line}")
    line_pair("At", header); line_pair("Label At", header)
    a, b = routes[0].points, routes[1].points
    terminal = int(typ[2])
    require((bool(a), bool(b)) == ((False, True) if terminal == 1 else (True, False) if terminal == 2 else (True, True)), "Stream terminal/route inconsistency")
    if a and b:
        require(math.dist(a[0], b[0]) < EPS, "Stream route roots disagree")
        path = list(reversed(a)) + b[1:]
    else:
        path = list(reversed(a)) if a else list(b)
    return Stream(name, text, header, text[first_extra + 1:], routes, terminal, path)


class Document:
    def __init__(self, raw):
        self.raw = raw
        require(b"\x00" not in raw, "Expected text Export(18), not binary archive")
        self.lines = raw.decode("latin1").replace("\r\n", "\n").splitlines(keepends=True)
        start = [i for i, x in enumerate(self.lines) if x.rstrip("\n") == ";PFSVData"]
        require(len(start) == 1, "Expected one comment PFSVData graphics section")
        self.start = start[0]; self.end = self.start + 1
        while self.end < len(self.lines) and self.lines[self.end].startswith(";"):
            if self.lines[self.end].startswith(";PFS V "):
                break
            self.end += 1
        outside = "".join(self.lines[:self.start] + self.lines[self.end:])
        for key in [r";PFS V \S+", r";#APWNLIB", r";#APWNBLOCK"]:
            unique_match("^" + key + "$", outside, "complete PFS config/icon marker " + key)
        self.outside = outside
        graphics = "".join(x[1:] for x in self.lines[self.start:self.end]).rstrip("\n")
        chunks = re.split(r"(?m)^(?=BLOCK$|STREAM$|LEGEND$)", graphics)
        self.preamble = chunks[0]
        require(re.fullmatch(r"PFSVData\n# of PFS Objects = \d+\nSIZE (?:" + NUM + r" ){3}" + NUM + r"\n?", self.preamble), "Unsupported graphics preamble or object")
        self.size = line_pair4('SIZE', self.preamble)
        require(self.size[0] < self.size[1] and self.size[2] < self.size[3], 'Invalid SIZE bounds')
        self.blocks, self.streams, self.order, self.legend = {}, {}, [], None
        for chunk in chunks[1:]:
            chunk = chunk.rstrip("\n") + "\n"
            if chunk.startswith("BLOCK\n"):
                require(self.legend is None, "Object after LEGEND unsupported")
                name = unique_match(r"^ID: (\S+)$", chunk, "block ID")[1]
                require(name not in self.blocks, f"Duplicate graphic BLOCK ID {name}")
                for line in chunk.splitlines()[1:]:
                    require(re.match(r"^(ID:|Version:|ICON:|Flag |Section |At |Label At |Annotation At |Scale )", line), f"Unsupported BLOCK record: {line}")
                unique_match(r"^Version: 1$", chunk, "block Version 1")
                icon = unique_match(r'^ICON: "([^"]+)"$', chunk, "ICON")[1]
                sm = unique_match(r"^Scale (" + NUM + r") Modifier ([0-7])$", chunk, "Scale/Modifier")
                scale = fnum(sm[1]); require(scale > 0, "Scale must be positive")
                self.blocks[name] = Block(name, chunk, line_pair("At", chunk), scale, int(sm[2]), line_pair("Label At", chunk), icon)
                self.order.append(("block", name))
            elif chunk.startswith("STREAM\n"):
                require(self.legend is None, "Object after LEGEND unsupported")
                stream = parse_stream(chunk)
                require(stream.name not in self.streams, f"Duplicate graphic STREAM ID {stream.name}")
                self.streams[stream.name] = stream; self.order.append(("stream", stream.name))
            else:
                require(self.legend is None and chunk.startswith("LEGEND\n"), "Unsupported graphics object")
                # Only the evidenced empty legend; textual/drawing objects fail closed.
                legend_records(chunk)
                self.legend = chunk
        require(self.legend is not None, "Missing empty LEGEND")
        count = int(unique_match(r"^# of PFS Objects = (\d+)$", self.preamble, "object count")[1])
        require(count == len(self.blocks) + len(self.streams) + 1, "Object count mismatch")
        self.netlist, self.sources, self.destinations = binding(raw)
        require(set(self.blocks) == set(self.netlist), "Physical/graphic BLOCK sets differ")
        require(set(self.streams) == set(self.sources) | set(self.destinations), "Physical/graphic STREAM sets differ")
        definitions = re.findall(r"(?m)^;>VERSION 0\n;([^\n]+)\n;([^\n]+)\n;([^\n]+)\n;([^\n]+)\n", outside)
        require(len(definitions) == len(self.blocks) and {x[0] for x in definitions} == set(self.blocks), "Missing, duplicate or unsupported icon block definitions")
        self.icon_definitions = {x[0]: x[1:] for x in definitions}
        config_start = outside.index(';PFS V ')
        # Native re-export may duplicate identical databank records. A set is
        # used only for config readback equivalence, never for physical cards.
        self.config_records = {x for x in outside[config_start:].splitlines() if x.startswith(';') and x != ';'}
        self.anchors = {}
        for name, stream in self.streams.items():
            for side, ends in [(0, self.sources), (1, self.destinations)]:
                route = stream.routes[side]
                require(bool(route.points) == (name in ends), f"Wrong physical role for {name}:{side}")
                if not route.points:
                    continue
                block = self.blocks[ends[name]]
                relative = tuple((route.points[-1][i] - block.at[i] - route.displacement[i]) / block.scale for i in range(2))
                self.anchors[name, side] = {"block": block.name, "canonical": mv(inverse(MATRICES[block.modifier]), relative), "direction": route.direction}

    def inspect(self):
        return {"scope": "offline graphic evidence; no simulation acceptance", "sha256": sha(self.raw),
                "physical_tokens_sha256": sha("\n".join(physical_tokens(self.raw, allow_elink=True)).encode("utf-8")),
                "netlist": self.netlist, "size": self.size,
                "blocks": {n: {"at": b.at, "scale": b.scale, "modifier": b.modifier, "label": b.label, "icon": b.icon} for n, b in self.blocks.items()},
                "streams": {n: {"path": s.path, "label": line_pair("Label At", s.header), "ports": {str(side): {**self.anchors[n, side], "point": s.routes[side].points[-1], "D": s.routes[side].displacement, "direction": s.routes[side].direction} for side in (0, 1) if (n, side) in self.anchors}} for n, s in self.streams.items()}}


def validate_path(path, name):
    require(isinstance(path, list) and len(path) >= 2, f"Incomplete path {name}")
    points = [pair(x) for x in path]
    for a, b in zip(points, points[1:]):
        require(math.dist(a, b) > EPS, f"Zero-length path segment {name}")
        require(abs(a[0] - b[0]) < EPS or abs(a[1] - b[1]) < EPS, f"Nonorthogonal path {name}")
    for a, b, c in zip(points, points[1:], points[2:]):
        u, v = (b[0]-a[0], b[1]-a[1]), (c[0]-b[0], c[1]-b[1])
        require(not (abs(u[0]*v[1]-u[1]*v[0]) < EPS and u[0]*v[0]+u[1]*v[1] < -EPS), f"Immediate path backtracking: {name}")
    return points


def overlap_check(paths):
    segments = []
    for name, points in paths.items():
        for index, (a, b) in enumerate(zip(points, points[1:])):
            axis = 0 if abs(a[1] - b[1]) < EPS else 1
            segments.append((name, index, axis, a[1-axis], sorted((a[axis], b[axis]))))
    for i, (name, index, axis, fixed, limits) in enumerate(segments):
        for n2, j, ax2, fix2, lim2 in segments[i+1:]:
            if name == n2 and abs(index-j) <= 1:
                continue
            if axis == ax2 and abs(fixed-fix2) < EPS:
                require(min(limits[1], lim2[1]) - max(limits[0], lim2[0]) <= EPS, f"Collinear route overlap: {name}/{n2}")


def split_path(points):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    half, total = sum(lengths)/2, 0.0
    for i, length in enumerate(lengths):
        if total + length >= half:
            t = (half-total)/length
            root = tuple(points[i][j] + t*(points[i+1][j]-points[i][j]) for j in range(2))
            left = list(reversed(points[:i+1] + [root]))
            right = [root] + points[i+1:]
            return root, deduplicate(left), deduplicate(right)
        total += length
    raise LayoutError("Cannot split stream path")


def deduplicate(points):
    result = []
    for point in points:
        if not result or math.dist(result[-1], point) > EPS:
            result.append(point)
    return result


def serialize_route(side, points, direction=None, displacement=(0, 0)):
    lines = [f"ROUTE {side} 0"]
    if points:
        require(len(points) >= 2, "Route collapsed to endpoint")
        lines.append(f"r r {fmt(points[0][0])} {fmt(points[0][1])} 0")
        for j, q in enumerate(points[1:-1], 1):
            axis = "x" if abs(q[0]-points[j-1][0]) > EPS else "y"
            nxt = "x" if abs(points[j+1][0]-q[0]) > EPS else "y"
            lines.append(f"{axis} {nxt if j < len(points)-2 else '0'} {fmt(q[0])} {fmt(q[1])} 0")
        lines.append(f"t {direction} {fmt(points[-1][0])} {fmt(points[-1][1])} 0")
        if max(map(abs, displacement)) > 1e-8:
            lines.extend(["$ D " + " ".join(map(fmt, displacement)), "$ C 0.000000 0.0"])
        else:
            lines.append("$ C 1.000000 0.0")
    lines.append("$ $ 0.0 0.0")
    return "\n".join(lines) + "\n"


def apply_layout(raw, export4, plan):
    doc = Document(raw)
    require(physical_tokens(raw, allow_elink=True) == physical_tokens(export4), "Export18 and complete Export4 genuine cards disagree")
    require(isinstance(plan, dict) and plan.get("version") == 1, "Expected layout plan version 1")
    require(not set(plan) - {"version", "blocks", "streams", "size"}, "Unknown plan field")
    block_plans, stream_plans = plan.get("blocks", {}), plan.get("streams", {})
    require(isinstance(block_plans, dict) and isinstance(stream_plans, dict), "Invalid plan maps")
    require(set(block_plans) <= set(doc.blocks) and set(stream_plans) <= set(doc.streams), "Plan adds unknown BLOCK/STREAM")
    blocks, changed = {}, set()
    for name, b in doc.blocks.items():
        cfg = block_plans.get(name)
        if cfg is None:
            blocks[name] = b; continue
        require(set(cfg) == {"at", "scale", "modifier", "label"}, f"Complete explicit block plan required: {name}")
        at, label, scale = pair(cfg["at"]), pair(cfg["label"]), finite(cfg["scale"])
        mod = cfg["modifier"]; require(type(mod) is int and mod in MATRICES and scale > 0, "Invalid Scale/Modifier")
        text = set_pair("At", b.text, at); text = set_pair("Label At", text, label)
        text = re.sub(r"(?m)^Scale .*?$", f"Scale {fmt(scale)} Modifier {mod}", text, count=1)
        blocks[name] = Block(name, text, at, scale, mod, label, b.icon)
        if at != b.at or scale != b.scale or mod != b.modifier:
            changed.add(name)
    centers = [b.at for b in blocks.values()]
    require(len(set(centers)) == len(centers), "Coincident BLOCK centers")
    paths, stream_texts = {}, {}
    for name, stream in doc.streams.items():
        cfg = stream_plans.get(name)
        related = {doc.anchors[name, side]["block"] for side in (0, 1) if (name, side) in doc.anchors}
        if cfg is None:
            require(not related & changed, f"Missing route for changed BLOCK: {name}")
            paths[name] = validate_path(stream.path, name); stream_texts[name] = stream.text; continue
        require(set(cfg) == {"path", "ports", "label"}, f"Explicit path/ports/label required: {name}")
        path = validate_path(cfg["path"], name); paths[name] = path
        require(set(cfg["ports"]) == {str(s) for s in (0, 1) if (name, s) in doc.anchors}, f"Physical endpoint role mismatch: {name}")
        port_data = {}
        for side in (0, 1):
            if (name, side) not in doc.anchors:
                continue
            pc = cfg["ports"][str(side)]; require(set(pc) == {"direction"}, "Only explicit drawing direction is accepted in port plan")
            direction = pc["direction"]; require(direction in DIRECTIONS, "Invalid drawing direction")
            point = path[0] if side == 0 else path[-1]
            lead = path[1] if side == 0 else path[-2]
            delta = tuple(lead[i]-point[i] for i in range(2)); vector = DIRECTIONS[direction]
            require(delta[0]*vector[0]+delta[1]*vector[1] > EPS and abs(delta[0]*vector[1]-delta[1]*vector[0]) < EPS, f"Endpoint lead/direction mismatch: {name}:{side}")
            anchor = doc.anchors[name, side]; b = blocks[anchor["block"]]
            rotated = mv(MATRICES[b.modifier], anchor["canonical"])
            true_point = tuple(b.at[i]+b.scale*rotated[i] for i in range(2))
            port_data[side] = (direction, tuple(point[i]-true_point[i] for i in range(2)))
        root, r0, r1 = split_path(path)
        if stream.terminal == 1:
            root, r0, r1 = path[0], [], path
        elif stream.terminal == 2:
            root, r0, r1 = path[-1], list(reversed(path)), []
        header = set_pair("At", stream.header, root)
        header = set_pair("Label At", header, pair(cfg["label"]))
        text = header
        for side, route in [(0, r0), (1, r1)]:
            direction, displacement = port_data.get(side, (None, (0, 0)))
            text += serialize_route(side, route, direction, displacement)
        stream_texts[name] = text + stream.secondary
    overlap_check(paths)
    preamble, legend = doc.preamble, doc.legend
    if "size" in plan:
        size = plan["size"]; require(isinstance(size, list) and len(size) == 4, "SIZE needs xmin xmax ymin ymax")
        size = [finite(x) for x in size]; require(size[0] < size[1] and size[2] < size[3], "Invalid SIZE bounds")
        preamble = re.sub(r"(?m)^SIZE .*?$", "SIZE " + " ".join(map(fmt, size)), preamble)
        viewport = [size[0], size[3], size[1], size[2]]
        require(len(re.findall(r"(?m)^VIEWPORT .*?$", legend)) == 1, "Missing/ambiguous LEGEND VIEWPORT")
        legend = re.sub(r"(?m)^VIEWPORT .*?$", "VIEWPORT " + " ".join(map(fmt, viewport)), legend)
    graph = preamble.rstrip() + "\n"
    for kind, name in doc.order:
        graph += blocks[name].text if kind == "block" else stream_texts[name]
    graph += legend
    newlines = doc.lines[:doc.start] + [";"+x+"\n" for x in graph.splitlines()] + doc.lines[doc.end:]
    newlines = [x for x in newlines if x.strip() != "E_LINK"]
    result = "".join(newlines).replace("\n", "\r\n").encode("latin1")
    require(physical_tokens(result) == physical_tokens(export4), "Complete genuine cards changed during layout")
    parsed = Document(result)
    for key, old in doc.anchors.items():
        require(math.dist(old["canonical"], parsed.anchors[key]["canonical"]) < EPS, f"Canonical physical port changed: {key}")
    return result


def verify_layout(expected, readback, export4):
    """Compare exact planned graphics with a native re-export; all physical cards included."""
    a, b = Document(expected), Document(readback)
    require(physical_tokens(expected, allow_elink=True) == physical_tokens(export4), "Expected file changes physical cards")
    require(physical_tokens(readback, allow_elink=True) == physical_tokens(export4), "Readback changes physical cards")
    require(a.netlist == b.netlist, "Physical netlist changed")
    require(all(abs(x-y) < EPS for x, y in zip(a.size, b.size)), 'PFS SIZE frame mismatch')
    require(legend_records(a.legend) == legend_records(b.legend), 'LEGEND frame/viewport/settings mismatch')
    require(a.icon_definitions == b.icon_definitions, "Native block icon definitions changed")
    require(a.config_records == b.config_records, "Native config records changed")
    require(set(a.blocks) == set(b.blocks) and set(a.streams) == set(b.streams), "Graphic object set changed")
    for name, ba in a.blocks.items():
        bb = b.blocks[name]
        require(ba.icon == bb.icon and ba.modifier == bb.modifier and abs(ba.scale-bb.scale) < EPS and math.dist(ba.at, bb.at) < EPS and math.dist(ba.label, bb.label) < EPS, f"BLOCK graphic mismatch: {name}")
        for field in ("Flag", "Section"):
            require(unique_match("^"+field+" (.*)$", ba.text, field)[1] == unique_match("^"+field+" (.*)$", bb.text, field)[1], f"BLOCK metadata mismatch: {name}/{field}")
    paths = {}
    for name, sa in a.streams.items():
        sb = b.streams[name]
        require(sa.terminal == sb.terminal, f"Terminal role changed: {name}")
        require(math.dist(line_pair("At", sa.header), line_pair("At", sb.header)) < EPS and math.dist(line_pair("Label At", sa.header), line_pair("Label At", sb.header)) < EPS, f"STREAM label/root mismatch: {name}")
        for field in ("Flag", "GLOBAL", "STYLE"):
            require(re.findall("^"+field+" (.*)$", sa.header, re.M) == re.findall("^"+field+" (.*)$", sb.header, re.M), f"STREAM metadata mismatch: {name}/{field}")
        for side in (0, 1):
            ra, rb = sa.routes[side], sb.routes[side]
            require(len(ra.points) == len(rb.points), f"Route corner count changed: {name}:{side}")
            require(all(math.dist(p, q) < EPS for p, q in zip(ra.points, rb.points)), f"Route points changed: {name}:{side}")
            require(ra.direction == rb.direction and ra.connection == rb.connection and math.dist(ra.displacement, rb.displacement) < EPS, f"Endpoint D/C/direction mismatch: {name}:{side}")
        paths[name] = validate_path(sb.path, name)
    overlap_check(paths)
    return {"offline_graphic_readback_pass": True, "all_genuine_cards_equal_export4": True, "netlist_identical": True, "frame_and_legend_equal": True, "icon_definitions_identical": True, "config_record_sets_identical": True, "config_comparison_note": "Exact record set; ignores only repeated identical config lines generated by native re-export. All physical-card order and multiplicity are preserved.", "graphic_coordinate_epsilon": EPS, "epsilon_scope": "graphic comparison only; never an Aspen solver tolerance", "expected_sha256": sha(expected), "readback_sha256": sha(readback), "export4_sha256": sha(export4), "block_count": len(a.blocks), "stream_count": len(a.streams), "simulation_acceptance": "NOT_CLAIMED", "native_gui_visual_review": "NOT_CLAIMED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect", help="Extract physical bindings and scale/modifier/D-corrected canonical anchors")
    p.add_argument("source", type=Path); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("apply", help="Apply explicit JSON block/path/port-direction plan; requires full Export4")
    p.add_argument("source", type=Path); p.add_argument("--export4", type=Path, required=True); p.add_argument("--plan", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("verify", help="Offline comparison of expected layout and native readback")
    p.add_argument("expected", type=Path); p.add_argument("readback", type=Path); p.add_argument("--export4", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        sources = [getattr(args, key, None) for key in ("source", "expected", "readback", "export4", "plan")]
        require(all(args.output.resolve() != p.resolve() for p in sources if p), "Output may not overwrite input evidence")
        require(not args.output.exists(), "Output already exists; choose a new candidate path")
        if args.command == "inspect":
            output = json.dumps(Document(args.source.read_bytes()).inspect(), indent=2).encode("utf-8")
        elif args.command == "apply":
            output = apply_layout(args.source.read_bytes(), args.export4.read_bytes(), json.loads(args.plan.read_text(encoding="utf-8-sig")))
        else:
            output = json.dumps(verify_layout(args.expected.read_bytes(), args.readback.read_bytes(), args.export4.read_bytes()), indent=2).encode("utf-8")
        args.output.write_bytes(output)
        print(json.dumps({"output": str(args.output), "sha256": sha(output), "scope": "offline graphics only"}))
    except (LayoutError, OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"error": str(error), "status": "rejected"}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
