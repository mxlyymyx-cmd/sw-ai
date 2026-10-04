"""
离心风机蜗壳设计

等边基元法（等环量法）—— 工程最常用的蜗壳型线设计方法。
与叶轮设计结果自动匹配，组成整机。

蜗壳参数：
  B    — 蜗壳宽度 (mm)
  A    — 蜗壳展开宽度 (mm)
  R(θ) — 外壁半径，从蜗舌到出口线性增大

建模输出：VBA 宏（SW 直接运行）+ 坐标 CSV
"""

import math
import csv
import os
from dataclasses import dataclass, field
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# 蜗壳参数模型
# ═══════════════════════════════════════════════════════════════


@dataclass
class VoluteParams:
    """蜗壳全部设计参数"""
    # ── 匹配的叶轮参数 ──
    D2: float           # 叶轮外径 mm
    b2: float           # 叶片出口宽度 mm
    D0: float           # 叶轮进口直径 mm

    # ── 设计输入 ──
    Q: float            # 流量 m³/h
    P: float            # 全压 Pa

    # ── 蜗壳尺寸 ──
    B: float = 0.0      # 蜗壳宽度 mm
    A: float = 0.0      # 展开宽度 mm
    delta: float = 0.0  # 蜗舌间隙 mm
    r_tongue: float = 0.0  # 蜗舌半径 mm
    theta_start: float = 25.0  # 蜗舌起始角 °

    # ── 出口 ──
    outlet_w: float = 0.0  # 出口宽度 mm
    outlet_h: float = 0.0  # 出口高度 mm
    outlet_v: float = 0.0  # 出口风速 m/s

    # ── 壁厚 ──
    wall_thk: float = 4.0

    @property
    def R2(self) -> float:
        """叶轮半径 mm"""
        return self.D2 / 2.0

    @property
    def summary(self) -> str:
        return (
            f"  蜗壳设计（匹配叶轮 D₂={self.D2:.0f}mm）\n"
            f"    宽度 B = {self.B:.0f}mm\n"
            f"    展开 A = {self.A:.0f}mm  (A/D₂={self.A/self.D2:.2f})\n"
            f"    蜗舌间隙 δ = {self.delta:.1f}mm\n"
            f"    出口 {self.outlet_w:.0f}×{self.outlet_h:.0f}mm  "
            f"风速 {self.outlet_v:.1f}m/s\n"
            f"    壁厚 {self.wall_thk:.0f}mm"
        )


# ═══════════════════════════════════════════════════════════════
# 蜗壳设计计算
# ═══════════════════════════════════════════════════════════════


def design_volute(
    D2: float,
    b2: float,
    D0: float,
    Q: float,
    P: float,
    width_ratio: float = 0.0,
    expand_ratio: float = 0.0,
    wall_thk: float = 4.0,
    target_outlet_v: float = 12.0,
) -> VoluteParams:
    """
    蜗壳设计主入口

    自动匹配叶轮参数，计算全部蜗壳尺寸。

    Args:
        D2: 叶轮外径 mm
        b2: 叶片出口宽度 mm
        D0: 叶轮进口直径 mm
        Q: 流量 m³/h
        P: 全压 Pa
        width_ratio: 蜗壳宽度比 B/b₂（0=自动取 2.0）
        expand_ratio: 展开比 A/D₂（0=自动估算）
        wall_thk: 壁厚 mm
        target_outlet_v: 目标出口风速 m/s

    Returns:
        VoluteParams
    """
    R2 = D2 / 2.0

    # ── Step 1: 蜗壳宽度 B ──
    B = b2 * (width_ratio or 2.0)
    B = _round_step(B, 5)

    # ── Step 2: 展开宽度 A ──
    # 先按经验取 A/D₂ = 0.45
    A_est = D2 * (expand_ratio or 0.45)
    # 按出口风速校核
    v_test = Q / 3600.0 / (B / 1000.0) / (A_est / 1000.0)
    if v_test < 8:
        A_est *= v_test / target_outlet_v
    elif v_test > 16:
        A_est *= v_test / target_outlet_v

    A = _round_step(A_est, 5)
    v_out = Q / 3600.0 / (B / 1000.0) / (A / 1000.0)

    # ── Step 3: 蜗舌 ──
    delta = 0.10 * R2  # 蜗舌间隙
    r_t = 0.04 * R2    # 蜗舌半径

    # ── Step 4: 出口 ──
    outlet_w = B
    outlet_h = A
    if v_out < 6:
        # 出口风速太低，减小出口面积
        outlet_h = Q / 3600.0 / (B / 1000.0) / target_outlet_v * 1000.0
        v_out = target_outlet_v

    return VoluteParams(
        D2=D2, b2=b2, D0=D0, Q=Q, P=P,
        B=B, A=A,
        delta=delta, r_tongue=r_t,
        outlet_w=_round_step(outlet_w, 5),
        outlet_h=_round_step(outlet_h, 5),
        outlet_v=round(v_out, 1),
        wall_thk=wall_thk,
    )


def volute_profile(v: VoluteParams, n_points: int = 72) -> list[dict]:
    """
    生成蜗壳外壁型线（极坐标）

    等边基元法：
      R(θ) = R₂ + A × θ / 360°
      θ 从蜗舌起始角到 360°+起始角

    Returns:
        [{theta, R, x, y}, ...]
    """
    R2 = v.R2
    A = v.A

    points = []
    for i in range(n_points):
        t = i / n_points
        theta_deg = v.theta_start + t * 360.0
        theta = math.radians(theta_deg)

        # 展开半径
        R = R2 + A * t
        x = R * math.cos(theta)
        y = R * math.sin(theta)

        points.append({
            "theta": round(theta_deg, 2),
            "R": round(R, 1),
            "x": round(x, 2),
            "y": round(y, 2),
        })

    return points


def volute_inner_profile(v: VoluteParams, n_points: int = 36) -> list[dict]:
    """
    蜗壳内壁型线（叶轮外径去除区域）

    内壁就是叶轮外径圆弧 + 蜗舌区域
    """
    R2 = v.R2
    theta_start = v.theta_start
    points = []

    # 叶轮外径圆弧（从蜗舌到 360°）
    for i in range(n_points):
        t = i / n_points
        theta_deg = theta_start + t * (360.0 - theta_start)
        theta = math.radians(theta_deg)
        x = R2 * math.cos(theta)
        y = R2 * math.sin(theta)
        points.append({
            "theta": round(theta_deg, 2), "R": round(R2, 1),
            "x": round(x, 2), "y": round(y, 2),
        })

    return points


# ═══════════════════════════════════════════════════════════════
# 与叶轮设计自动匹配
# ═══════════════════════════════════════════════════════════════


def match_impeller(design_result) -> VoluteParams:
    """
    从叶轮设计结果自动计算蜗壳参数

    Args:
        design_result: ImpellerDesignResult

    Returns:
        VoluteParams
    """
    p = design_result
    return design_volute(
        D2=p.D2,
        b2=p.b2,
        D0=p.D0,
        Q=p.input_params.Q,
        P=p.input_params.P,
    )


# ═══════════════════════════════════════════════════════════════
# VBA 宏（SW 建模）
# ═══════════════════════════════════════════════════════════════


def generate_vba_macro(v: VoluteParams, full_profile: list[dict]) -> str:
    """
    生成蜗壳 VBA 宏（SW-2022 VBS/cscript 通道实测配方）

    建模步骤：
    1. 首草图（默认前视基准面）：蜗壳螺旋外壁折线（单封闭回路）
       —— VBS 中 CreateSpline 返回 Nothing，必须用 CreateLine2 折线逼近
    2. FeatureExtrusion3 23 参数、MidPlane、深度 B —— 20 参数版本报 449
    3. 前视基准面（特征树第 1 个基准面）画叶轮内腔圆 → FeatureCut3 贯穿切除
       —— 螺旋起点与内腔圆必须留间隙（相切会切除失败）
    """
    R2 = v.R2

    # 蜗舌间隙：螺旋起点外移，避免与内腔圆相切（实测相切时切除返回 Nothing）
    gap = max(2.0, 0.006 * R2)

    # 型线点外移 gap 后转折线（米）
    pts = []
    for pt in full_profile:
        r = math.hypot(pt["x"], pt["y"])
        if r > 1e-9:
            s = (r + gap) / r
            pts.append((pt["x"] * s / 1000.0, pt["y"] * s / 1000.0))
        else:
            pts.append((0.0, 0.0))

    spiral_lines = []
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        spiral_lines.append(
            f"    Part.CreateLine2 {x1:.6f}, {y1:.6f}, 0, {x2:.6f}, {y2:.6f}, 0"
        )
    # 闭合径向线（终点 → 起点）
    x1, y1 = pts[-1]
    x2, y2 = pts[0]
    spiral_lines.append(
        f"    Part.CreateLine2 {x1:.6f}, {y1:.6f}, 0, {x2:.6f}, {y2:.6f}, 0"
    )
    spiral_block = "\n".join(spiral_lines)

    macro = f"""' SolidWorks Macro - Centrifugal Fan Volute (scroll casing)
' Matching impeller: D2={v.D2:.0f}mm  b2={v.b2:.0f}mm
' Volute: B={v.B:.0f}mm  A={v.A:.0f}mm  tongue gap={gap:.1f}mm
' Recipes verified on SW2022 via cscript/VBS channel
' ============================================================

Dim swApp As Object
Dim Part As Object
Dim skMgr As Object
Dim featMgr As Object
Dim extFeat As Object
Dim cutFeat As Object
Dim feat0 As Object
Dim idx As Integer

Sub main()
    Set swApp = Application.SldWorks
    Set Part = swApp.NewDocument("", 0, 0, 0)
    swApp.Visible = True
    Set skMgr = Part.SketchManager
    Set featMgr = Part.FeatureManager

    ' === 1. Scroll outer wall: spiral polyline + closing radial line ===
    skMgr.InsertSketch True
{spiral_block}
    skMgr.InsertSketch True

    Set extFeat = featMgr.FeatureExtrusion3(True, False, False, 6, 0, {v.B / 1000.0:.6f}, 0, False, False, False, False, 0, 0, False, False, False, False, True, True, True, 0, 0, False)

    ' === 2. Impeller cavity: circle on front plane, cut through all ===
    Set feat0 = Part.FirstFeature
    idx = 0
    Do While Not feat0 Is Nothing
        If feat0.GetTypeName2 = "RefPlane" Then
            idx = idx + 1
            If idx = 1 Then Exit Do
        End If
        Set feat0 = feat0.GetNextFeature
    Loop
    If feat0 Is Nothing Then Exit Sub
    feat0.Select2 False, 0
    skMgr.InsertSketch True
    Part.CreateCircle2 0, 0, 0, {R2 / 1000.0:.6f}, 0, 0
    skMgr.InsertSketch True

    Set cutFeat = featMgr.FeatureCut3(True, False, False, 1, 1, 0, 0, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)

    Part.ViewZoomtofit2
    MsgBox "Fan Volute D2={v.D2:.0f}mm  B={v.B:.0f}mm  A={v.A:.0f}mm", vbInformation, "sw-ai"
End Sub
"""
    return macro


def _round_step(v: float, step: float) -> float:
    return round(v / step) * step


# ═══════════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════════


def export_csv(points: list[dict], path: str):
    """导出蜗壳型线 CSV（SW 曲线文件格式）"""
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["x", "y", "theta", "R"], extrasaction="ignore")
        w.writeheader()
        for pt in points:
            w.writerow(pt)
    print(f"  📄 {path} ({len(points)} pts)")


def export_sw_curve(points_3d: list[dict], path: str):
    """导出 SW 曲线"""
    with open(path, "w") as f:
        f.write(f"# Volute curve — {len(points_3d)} pts\nx,y,z\n")
        for pt in points_3d:
            f.write(f"{pt['x']},{pt['y']},{pt.get('z', 0)}\n")
    print(f"  📄 {path}")


# ═══════════════════════════════════════════════════════════════
# 完整 Pipeline
# ═══════════════════════════════════════════════════════════════


def design_and_output(
    Q: float, P: float, n: float,
    blade_type: str = "backward",
    material: str = "Q235B",
    output_dir: str = ".",
    gen_macro: bool = True,
) -> dict:
    """
    完整流程：叶轮设计 → 蜗壳匹配 → 输出

    Returns:
        {"impeller": ..., "volute": ..., "summary": ..., ...}
    """
    from .design import design_impeller
    from .params import ImpellerDesignInput

    inp = ImpellerDesignInput(Q=Q, P=P, n=n, blade_type=blade_type, material=material)
    imp = design_impeller(inp)
    vol = match_impeller(imp)

    result = {
        "impeller": imp,
        "volute": vol,
        "summary": f"{imp.summary}\n\n{vol.summary}",
        "macro_path": None,
        "profile_path": None,
    }

    os.makedirs(output_dir, exist_ok=True)
    safe = f"Fan_{Q:.0f}m3h_{P:.0f}Pa_{n:.0f}rpm"

    # 蜗壳型线
    profile = volute_profile(vol)
    csv_path = os.path.join(output_dir, f"{safe}_volute.csv")
    export_csv(profile, csv_path)
    result["profile_path"] = csv_path

    if gen_macro:
        macro = generate_vba_macro(vol, profile)
        mp = os.path.join(output_dir, f"{safe}.bas")
        with open(mp, "w", encoding="utf-8") as f:
            f.write(macro)
        result["macro_path"] = mp
        print(f"  ✅ VBA Macro: {mp}")

    return result


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from .design import design_impeller
    from .params import ImpellerDesignInput

    # 用之前的叶轮案例
    inp = ImpellerDesignInput(Q=5000, P=2500, n=1450)
    imp = design_impeller(inp)

    print("=" * 60)
    print("  叶轮设计")
    print("=" * 60)
    print(imp.summary)

    print("\n" + "=" * 60)
    print("  蜗壳匹配")
    print("=" * 60)
    vol = match_impeller(imp)
    print(vol.summary)

    profile = volute_profile(vol)
    print(f"\n  蜗壳型线: {len(profile)} 个点")
    print(f"    进口 (θ={vol.theta_start}°): R={profile[0]['R']:.0f}mm")
    print(f"    出口 (θ={profile[-1]['theta']}°): R={profile[-1]['R']:.0f}mm")

    macro = generate_vba_macro(vol, profile)
    print(f"\n  VBA Macro: {len(macro)} chars")
