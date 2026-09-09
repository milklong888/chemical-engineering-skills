"""Deep probe tool for Aspen COM node properties."""
from __future__ import annotations
from ..com_bridge import aspen
from ._common import walk


def tool_deep_probe(block_name: str = "") -> str:
    """Probe a block's Input.Error/Status and other node properties."""
    def impl():
        lines = []
        app = aspen._app
        tree = app.RootModel("")

        if not block_name:
            blocks = walk(tree, "Data", "Blocks")
            if blocks:
                lines.append("=== ALL BLOCKS ===")
                for i in range(200):
                    try:
                        b = blocks.Elements(i)
                        if b is None:
                            break
                        lines.append(f"  [{i}] {b.Name} = {b.Value}")
                    except:
                        break
            return "\n".join(lines)

        blk = walk(tree, "Data", "Blocks", block_name)
        if blk is None:
            return f"Block '{block_name}' not found"

        lines.append(f"=== BLOCK: {block_name} ({blk.Value}) ===")

        inp = walk(tree, "Data", "Blocks", block_name, "Input")
        if inp is None:
            return "No Input section"

        # --- Probe Input node sub-properties ---
        lines.append("")
        lines.append("--- Input node: Error/Status/Required sub-nodes ---")
        for prop in ["Error", "Status", "Warning", "Ready", "Required",
                     "IsRequired", "MinimumRequired", "Mandatory"]:
            try:
                obj = getattr(inp, prop)
                lines.append(f"  Input.{prop}:")
                lines.append(f"    type={type(obj).__name__}")
                for attr in ["Name", "Value", "ValueType"]:
                    try:
                        v = getattr(obj, attr)
                        lines.append(f"    {attr} = {v!r}")
                    except Exception as e:
                        lines.append(f"    {attr} -> {str(e)[:60]}")
                try:
                    cnt = obj.Elements.Count
                    lines.append(f"    Elements.Count = {cnt}")
                    for i in range(cnt):
                        try:
                            c2 = obj.Elements(i)
                            lines.append(f"      [{i}] {c2.Name} = {c2.Value!r}")
                        except:
                            break
                except Exception as e:
                    lines.append(f"    Elements -> {str(e)[:60]}")
            except Exception as e:
                lines.append(f"  Input.{prop} -> {str(e)[:80]}")

        # --- Deep probe Error node ---
        lines.append("")
        lines.append("--- Input.Error deep probe ---")
        try:
            err = inp.Error
            lines.append(f"  type={type(err).__name__}")
            lines.append(f"  repr={err!r}")
            for attr in ["Name", "Value", "Text", "Message", "FullName"]:
                try:
                    v = getattr(err, attr)
                    lines.append(f"  .{attr} = {v!r}")
                except Exception as e:
                    lines.append(f"  .{attr} -> {type(e).__name__}: {str(e)[:80]}")
            # Elements
            try:
                cnt = err.Elements.Count
                lines.append(f"  .Elements.Count = {cnt}")
                for i in range(cnt):
                    try:
                        c = err.Elements(i)
                        lines.append(f"    [{i}] {c.Name} = {c.Value!r}")
                    except Exception as e:
                        lines.append(f"    [{i}] -> {str(e)[:80]}")
            except Exception as e:
                lines.append(f"  .Elements -> {str(e)[:80]}")
            # AttributeValue on Error node
            lines.append("  .AttributeValue() scan:")
            for idx in range(30):
                try:
                    r = err.AttributeValue(idx)
                    if r is not None:
                        lines.append(f"    [{idx}] = {r!r}")
                except:
                    break
        except Exception as e:
            lines.append(f"  Error object access: {str(e)[:80]}")
        
        # --- BLKSTAT/BLKMSG ---
        out = walk(tree, "Data", "Blocks", block_name, "Output")
        if out:
            lines.append("")
            lines.append("--- BLKSTAT/BLKMSG ---")
            for name in ["BLKSTAT", "BLKMSG", "PER_ERROR", "PROPSTAT"]:
                try:
                    v = walk(tree, "Data", "Blocks", block_name, "Output", name)
                    if v is not None:
                        lines.append(f"  {name} = {v.Value!r}")
                except:
                    pass
        
        # --- AttributeValue on Input node itself ---
        lines.append("")
        lines.append("--- Input node AttributeValue() scan ---")
        for idx in range(20):
            try:
                r = inp.AttributeValue(idx)
                lines.append(f"  Input.AttributeValue({idx}) = {r!r}")
            except Exception as e:
                lines.append(f"  Input.AttributeValue({idx}) -> {str(e)[:60]}")
                break
        
        # --- CC Nodes search for non-binary values ---
        lines.append("")
        lines.append("--- CC Nodes non-binary values ---")
        cc = walk(tree, "Data", "Blocks", block_name, "CC Nodes")
        if cc:
            for i in range(200):
                try:
                    n = cc.Elements(i)
                    if n is None:
                        break
                    val = n.Value
                    if val is not None and val not in (0, 1, "", "0", "1"):
                        lines.append(f"  [{i}] {n.Name} = {val!r}")
                except:
                    break

        # --- First 5 params ---
        lines.append("")
        lines.append("--- First 5 params with AttributeValue metadata ---")
        for ii in range(min(5, 200)):
            try:
                n = inp.Elements(ii)
                if n is None:
                    break
                name = n.Name
                val = n.Value
                lines.append(f"")
                lines.append(f"  [{ii}] {name}={val!r}")
                for idx in [2, 3, 7, 11, 19, 22]:
                    try:
                        r = n.AttributeValue(idx)
                        lines.append(f"    ATTR({idx})={r!r}")
                    except:
                        break
            except:
                break

        # --- Unset params ---
        lines.append("")
        lines.append("--- Key params unset (i7=1, i11=0) ---")
        count = 0
        for ii in range(200):
            try:
                n = inp.Elements(ii)
                if n is None:
                    break
                name = n.Name
                val = n.Value
                vt = n.ValueType
                i7 = n.AttributeValue(7)
                i11 = n.AttributeValue(11)
                i19 = n.AttributeValue(19)

                if i7 == 1 and i11 == 0 and (vt == 0 or val is None):
                    if count >= 15:
                        continue
                    desc = str(i19)[:50] if i19 else ""
                    lines.append(f"  {name:20s}  {desc}")
                    count += 1
            except:
                break
        if count == 0:
            lines.append("  (none)")

        return "\n".join(lines)

    return aspen.call(impl)
