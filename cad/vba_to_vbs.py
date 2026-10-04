"""VBA -> VBS translator (SW-2022 external COM execution path)

E2E-proven: cscript + GetObject drives SolidWorks; RunMacro2 cannot open .bas.
Rules derived from the 3 generators (flange/impeller/volute/axial):
  1. drop Attribute/Option Explicit lines
  2. Application.SldWorks        -> GetObject(, "SldWorks.Application")
  3. swApp.NewDocument("",0,0,0) -> swApp.NewPart()   (external NewDocument("")=Nothing)
  4. Dim x(0 To N) As T          -> Dim x(N)
  5. Dim x As T                  -> Dim x
  6. MsgBox statements (multi-line via _ continuation) -> commented out
  7. Next i                      -> Next
  8. wrap Sub main call with error trap + MACRO_DONE sentinel
"""
import re
import sys


def translate(vba: str) -> str:
    lines = vba.splitlines()
    out = []
    in_msgbox = False

    for ln in lines:
        s = ln.rstrip()

        if in_msgbox:
            out.append("' [swai] " + s)
            if not s.rstrip().endswith("_"):
                in_msgbox = False
            continue

        if re.match(r"^\s*Attribute\s+VB_Name", s):
            continue
        if re.match(r"^\s*Option\s+Explicit", s):
            continue

        if re.match(r"^\s*MsgBox\b", s, re.IGNORECASE):
            out.append("' [swai] " + s)
            if s.rstrip().endswith("_"):
                in_msgbox = True
            continue

        t = s
        t = re.sub(r"Application\.SldWorks",
                   'GetObject(, "SldWorks.Application")', t)
        t = re.sub(r"swApp\.NewDocument\s*\([^)]*\)", "swApp.NewPart()", t)
        # VBA literal type suffixes (0#, 1.5#, 2!) are invalid in VBS.
        # NB: never strip '&' — it is the VBS concatenation operator.
        t = re.sub(r"(\d(?:\.\d+)?)\s*[#!]", r"\1", t)
        t = re.sub(r"Dim\s+(\w+)\s*\(\s*\d+\s+To\s+(\d+)\s*\)\s+As\s+\w+",
                   r"Dim \1(\2)", t, flags=re.IGNORECASE)
        t = re.sub(r"Dim\s+(\w+)\s+As\s+\w+", r"Dim \1", t, flags=re.IGNORECASE)
        t = re.sub(r"^(\s*)Next\s+\w+\s*$", r"\1Next", t, flags=re.IGNORECASE)
        if re.match(r"^\s*Debug\.Print", t, re.IGNORECASE):
            t = "' [swai] " + t

        out.append(t)

    body = "\n".join(out)
    epilogue = (
        "\n\nOn Error Resume Next\n"
        "main\n"
        "If Err.Number <> 0 Then\n"
        "    WScript.Echo \"MACRO_ERROR \" & Err.Number & \": \" & "
        "Err.Description\n"
        "    WScript.Quit 1\n"
        "End If\n"
        "WScript.Echo \"MACRO_DONE\"\n"
    )
    return body + epilogue


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "r", encoding="gbk", errors="replace") as f:
        vba = f.read()
    vbs = translate(vba)
    with open(dst, "w", encoding="ascii", errors="replace") as f:
        f.write(vbs)
    print(f"[ok] {dst} written ({len(vbs)} chars)")
