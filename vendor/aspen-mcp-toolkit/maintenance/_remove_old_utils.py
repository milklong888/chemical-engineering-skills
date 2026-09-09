"""Remove old-named utilities directly via COM."""
import sys
sys.coinit_flags = 0  # STA

import win32com.client
import pythoncom

pythoncom.CoInitialize()

try:
    ap = win32com.client.GetActiveObject("Apwn.Document")
    tree = ap.RootModel("")
    utils = tree.Elements("Data").Elements("Utilities")
    
    old_names = ["CWR-01", "CWR-02", "CWR-03", "LPS-01", "LPS-02", "ELC-01", "ELC-02", "ELC-03"]
    
    for old_name in old_names:
        try:
            utils.Elements.Remove(old_name)
            print(f"Removed: {old_name}")
        except Exception as e:
            print(f"Failed to remove {old_name}: {e}")
    
    # Verify
    remaining = []
    for i in range(200):
        try:
            c = utils.Elements(i)
            if c is None:
                break
            n = c.Name
            if n and n not in ("Input", "Output", "CC Nodes"):
                remaining.append(n)
        except Exception:
            break
    print(f"Remaining utilities: {remaining}")
    
    ap.Engine.Reinit()
    ap.Run2()
    print("Reinit and run completed.")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    pythoncom.CoUninitialize()
