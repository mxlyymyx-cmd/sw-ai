"""Insert WScript.Echo line markers before each executable statement to
locate the failing COM call."""
import sys

src = r"C:\Users\ADMINI~1\AppData\Local\Temp\SWAI_probe.vbs"
dst = r"C:\Users\ADMINI~1\AppData\Local\Temp\SWAI_probe_dbg.vbs"

with open(src, "r", encoding="ascii") as f:
    lines = f.read().splitlines()

out = []
prev_continues = False
for i, ln in enumerate(lines, 1):
    s = ln.strip()
    if (not prev_continues and s and not s.startswith("'")
            and not s.startswith("Dim")
            and not s.startswith("Sub") and not s.startswith("End")
            and not s.startswith("On Error") and not s.startswith("If ")
            and s != "End If" and not s.startswith("WScript")
            and not s.startswith("main")):
        out.append('WScript.Echo "L{}"'.format(i))
    out.append(ln)
    prev_continues = s.endswith("_")

with open(dst, "w", encoding="ascii") as f:
    f.write("\n".join(out))
print("[ok] debug vbs written")
