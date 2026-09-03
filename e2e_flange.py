#!/usr/bin/env python3
"""
法兰 4 类型 SolidWorks E2E 验证
=================================
流程:
  1. Python 计算 4 类法兰几何（轮廓点 + 螺栓孔）+ 解析体积基准
  2. 生成 VBS（复刻 generate_sw_macro 的完整建模序列，去掉 MsgBox）
  3. cscript 驱动运行中的 SolidWorks 建模，读取 IMassProperties.Volume
  4. 对比解析体积（Pappus 旋转体 + 螺栓孔扣除），容差 1%

用法: python e2e_flange.py
"""

import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flange.gb_standards import lookup
from flange.generator import _flange_profile, _bolt_hole_geometry

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
VBS_PATH = os.path.join(OUT_DIR, "e2e_flange.vbs")

# (dn, pn, type, save_model)
CASES = [
    (100, 16, "plate", True),
    (100, 16, "slip_on", True),
    (100, 16, "weld_neck", True),
    (100, 16, "blind", True),
    (50, 10, "blind", False),
    (300, 16, "weld_neck", False),
    (150, 25, "slip_on", False),
]


def revolve_volume_mm3(pts):
    """Pappus-Guldinus 多边形旋转体体积 (mm^3)，绕 X=0 轴"""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += (x1 + x2) * (x1 * y2 - x2 * y1)
    return abs(math.pi * s / 3.0)


def analytic_volume_mm3(params, pts):
    """解析净体积 = 旋转体毛坯 - 螺栓孔

    螺栓孔穿过两层：
      - 密封凸台（厚 f，径向 rb→r1）：孔与凸台外缘仅部分重叠，按圆弓形面积修正
      - 法兰盘（厚 C，径向 rb→R）：孔整圆穿过
    """
    gross = revolve_volume_mm3(pts)
    _, k_r, n_bolts, bolt_r = _bolt_hole_geometry(params)
    r1 = (params.d1 or params.d * 0.85) / 2.0
    d = k_r - r1  # 孔心到凸台外缘的径向距离
    if d <= -bolt_r:
        a_face = math.pi * bolt_r ** 2
    elif d >= bolt_r:
        a_face = 0.0
    else:
        a_face = bolt_r ** 2 * math.acos(d / bolt_r) - d * math.sqrt(bolt_r ** 2 - d ** 2)
    bolt_cut = n_bolts * (a_face * params.f + math.pi * bolt_r ** 2 * params.c)
    return gross - bolt_cut


def build_case(params, save_model):
    """生成单个 case 的 VBS 代码块"""
    pts = _flange_profile(params)
    r_pick, k_r, n_bolts, bolt_r = _bolt_hole_geometry(params)
    y_min = min(p[1] for p in pts)

    def d(v):
        return "{:.6f}".format(v / 1000.0)

    tag = "{}_DN{}_PN{}".format(params.flange_type.value, params.dn, params.pn)

    lines = []
    lines.append("    ' ---- case {} ----".format(tag))
    # VBS 外进程调用 NewDocument("") 返回 Nothing（VBA 内进程可用），NewPart() 已实测可用
    lines.append("    Set Part = swApp.NewPart()")
    lines.append("    If Part Is Nothing Then")
    lines.append("        WScript.Echo \"CASE {} NEWDOC_FAIL\"".format(tag))
    lines.append("    Else")
    lines.append("    Set skMgr = Part.SketchManager")
    lines.append("    Set featMgr = Part.FeatureManager")
    lines.append("    skMgr.InsertSketch True")
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        lines.append(
            "    Part.CreateLine2 {}, {}, 0, {}, {}, 0".format(d(x1), d(y1), d(x2), d(y2))
        )
    # 轴心线：构造线（中心线），对象引用 + mark=1 选择 + 8 参数 FeatureRevolve（实测配方）
    lines.append(
        "    Set segAxis = Part.CreateLine2(0, 0.02, 0, 0, {}, 0)".format(d(y_min - 20.0))
    )
    lines.append("    segAxis.ConstructionGeometry = True")
    lines.append("    skMgr.InsertSketch True")
    lines.append("    Part.ClearSelection2 True")
    lines.append("    segAxis.Select2 True, 1")
    lines.append(
        "    Set revFeat = featMgr.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)"
    )
    lines.append("    If revFeat Is Nothing Then")
    lines.append('        WScript.Echo "CASE {} REVOLVE_FAIL"'.format(tag))
    lines.append("    Else")
    lines.append("        Part.ClearSelection2 True")
    # 螺栓孔：上视基准面（第 2 个 RefPlane，即 y=0 密封面所在平面）作草图面
    lines.append("        cutOK = False")
    lines.append("        Set feat0 = Part.FirstFeature")
    lines.append("        idx = 0")
    lines.append("        Do While Not feat0 Is Nothing")
    lines.append('            If feat0.GetTypeName2 = "RefPlane" Then')
    lines.append("                idx = idx + 1")
    lines.append("                If idx = 2 Then Exit Do")
    lines.append("            End If")
    lines.append("            Set feat0 = feat0.GetNextFeature")
    lines.append("        Loop")
    lines.append("        If Not feat0 Is Nothing Then")
    lines.append("            If feat0.Select2(False, 0) Then")
    lines.append("                skMgr.InsertSketch True")
    for i in range(n_bolts):
        th = 2.0 * math.pi * i / n_bolts
        cx = k_r * math.cos(th)
        cy = k_r * math.sin(th)
        lines.append(
            "                skMgr.CreateCircle {}, {}, 0, {}, {}, 0".format(
                d(cx), d(cy), d(cx + bolt_r), d(cy)
            )
        )
    lines.append("                skMgr.InsertSketch True")
    lines.append("                Set cutFeat = Nothing")
    lines.append("                On Error Resume Next")
    lines.append(
        "                Set cutFeat = featMgr.FeatureCut3(True, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)"
    )
    lines.append(
        "                If cutFeat Is Nothing Then Err.Clear: Set cutFeat = featMgr.FeatureCut3(True, False, False, 0, 0, 0.06, 0.06, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)"
    )
    lines.append(
        "                If cutFeat Is Nothing Then Err.Clear: Set cutFeat = featMgr.FeatureCut(False, False, False, 0, 0, 1, 0.5, 0, False, False, False, False, 0, 0, False, False)"
    )
    lines.append("                On Error Goto 0")
    lines.append("                cutOK = Not cutFeat Is Nothing")
    lines.append("            End If")
    lines.append("        End If")
    lines.append("        Set mp = Part.Extension.CreateMassProperty")
    lines.append(
        '        WScript.Echo "CASE {} VOL " & FormatNumber(mp.Volume, 12) & " CUT " & cutOK'.format(
            tag
        )
    )
    if save_model:
        model_dir = os.path.join(OUT_DIR, "e2e_models")
        os.makedirs(model_dir, exist_ok=True)
        base = os.path.join(
            model_dir,
            "Flange_DN{}_PN{}_{}".format(params.dn, params.pn, params.flange_type.value),
        ).replace("\\", "/")
        lines.append("        Part.ViewZoomtofit2")
        lines.append('        e1 = 0: w1 = 0')
        lines.append('        On Error Resume Next')
        lines.append('        Err.Clear')
        lines.append('        Part.Extension.SaveAs "{}.SLDPRT", 0, 1, Nothing, e1, w1'.format(base))
        lines.append('        If Err.Number <> 0 Then Err.Clear: Part.SaveAs "{}.SLDPRT"'.format(base))
        lines.append('        Err.Clear')
        lines.append('        Part.Extension.SaveAs "{}.jpg", 0, 1, Nothing, e1, w1'.format(base))
        lines.append('        On Error Goto 0')
    lines.append("        swApp.CloseDoc Part.GetTitle()")
    lines.append("    End If")
    lines.append("    End If")
    return "\n".join(lines)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    blocks = []
    expected = {}
    for dn, pn, t, save in CASES:
        p = lookup(dn, pn, t)
        pts = _flange_profile(p)
        expected["{}_DN{}_PN{}".format(t, dn, pn)] = analytic_volume_mm3(p, pts)
        blocks.append(build_case(p, save))

    vbs = "\n".join([
        "' E2E flange driver -- auto generated by e2e_flange.py",
        "Dim swApp, Part, skMgr, featMgr, revFeat, cutFeat, mp, cutOK, segAxis, feat0, idx",
        "On Error Resume Next",
        'Set swApp = GetObject(, "SldWorks.Application")',
        "If Err.Number <> 0 Then",
        '    WScript.Echo "FATAL connect SolidWorks failed"',
        "    WScript.Quit 1",
        "End If",
        "On Error Goto 0",
        "\n".join(blocks),
        'WScript.Echo "E2E_DONE"',
    ])

    with open(VBS_PATH, "w", encoding="ascii") as f:
        f.write(vbs)
    print("[e2e] VBS written: {} ({} chars, {} cases)".format(VBS_PATH, len(vbs), len(CASES)))

    r = subprocess.run(
        ["cscript", "//nologo", VBS_PATH],
        capture_output=True, timeout=600,
    )
    out = r.stdout.decode("gbk", errors="replace").strip()
    print(out)
    if r.returncode != 0 and "FATAL" in out:
        sys.exit(1)

    results, fails = [], 0
    for line in out.splitlines():
        if not line.startswith("CASE"):
            continue
        parts = line.split()
        tag = parts[1]
        if "REVOLVE_FAIL" in line or "NEWDOC_FAIL" in line:
            results.append((tag, None, expected.get(tag), None, False))
            fails += 1
            continue
        vol_s = parts[3]
        cut_ok = parts[-1] == "True"
        vol_sw = float(vol_s.replace(",", "")) * 1e9  # m^3 -> mm^3
        exp = expected.get(tag)
        dev = abs(vol_sw - exp) / exp if exp else None
        ok = dev is not None and dev < 0.01
        if not ok or not cut_ok:
            fails += 1
        results.append((tag, vol_sw, exp, dev, cut_ok))

    print("\n========== E2E 结果 ==========")
    for tag, sw, exp, dev, cut in results:
        if sw is None:
            print("X {} REVOLVE FAILED".format(tag))
        else:
            mark = "OK" if (dev < 0.01 and cut) else "X "
            print(
                "{} {:24s} SW={:9.1f}cm3  analytic={:9.1f}cm3  dev={:.3%}  boltCut={}".format(
                    mark, tag, sw / 1000, exp / 1000, dev, cut
                )
            )
    print("==============================")
    if fails:
        print("FAILED: {}/{}".format(fails, len(results)))
        sys.exit(1)
    print("ALL {} PASSED".format(len(results)))


if __name__ == "__main__":
    main()
