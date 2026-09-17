import sys, os
sys.path.insert(0, r"c:\Users\Administrator\Desktop\workspace\SOLO\sw-ai")
from tools.vba_to_vbs import translate

src = r"C:\Users\Administrator\AppData\Local\Temp\SWAI_TempMacro.bas"
dst = r"C:\Users\Administrator\AppData\Local\Temp\SWAI_e2e_test.vbs"

vba = open(src, "r", encoding="gbk", errors="replace").read()
vbs = translate(vba)
with open(dst, "w", encoding="ascii", errors="replace") as f:
    f.write(vbs)
print(f"[ok] {dst} written ({len(vbs)} chars)")
print("---- tail ----")
print(vbs[-320:])
