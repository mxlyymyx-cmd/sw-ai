"""
叶片型线生成器（v3 — 微分步进法主力）

β 角约定：从切向（圆周方向）测量（风机设计标准）
- 后向: β = 20°~55°
- 径向: β = 90°
- 前向: β = 120°~170°

核心算法：微分步进法（数值积分）
  dθ/dr = cot(β(r)) / r
  
单圆弧作为快速估计保留。
"""

import math
import csv
from enum import Enum


class CurveType(str, Enum):
    SINGLE_ARC = "single_arc"       # 单圆弧（快速估计）
    MARCHING = "marching"           # 微分步进（精确匹配 β₁ β₂）、


def generate_blade_profile(
    r1: float,
    r2: float,
    beta1: float,
    beta2: float,
    curve_type: CurveType = CurveType.MARCHING,
    n_points: int = 50,
) -> list[dict]:
    """
    生成叶片型线坐标

    Args:
        r1: 进口半径 mm
        r2: 出口半径 mm
        beta1: 进口角 °（从切向）
        beta2: 出口角 °（从切向）
        curve_type: 型线类型
        n_points: 生成点数

    Returns:
        [{r, theta, x, y, beta}, ...]
    """
    if r1 <= 0 or r2 <= 0:
        raise ValueError(f"半径必须为正: r₁={r1}, r₂={r2}")
    if r1 >= r2:
        raise ValueError(f"进口半径必须小于出口半径")
    if n_points < 3:
        raise ValueError("点数至少 3 个")

    if curve_type == CurveType.SINGLE_ARC:
        return _single_arc(r1, r2, beta1, beta2, n_points)
    else:
        return _marching(r1, r2, beta1, beta2, n_points)


# ═══════════════════════════════════════════════════════════════
# 微分步进法（主力算法）
# ═══════════════════════════════════════════════════════════════
#
# 从进口到出口，沿径向步进，用微分方程积分叶片轨迹：
#
#   dθ/dr = cot(β(r)) / r
#
# 其中 β(r) 从 β₁ 线性变化到 β₂。
# β 角是从切向测量的。
#
# 这个方法总能精确匹配给定的 β₁ 和 β₂。
# ═══════════════════════════════════════════════════════════════


def _marching(
    r1: float, r2: float,
    beta1: float, beta2: float,
    n: int,
) -> list[dict]:
    """
    微分步进法生成叶片型线

    将 β(r) 从 β₁ 到 β₂ 线性插值，用 Euler 法数值积分。
    """
    # 步长：细分用 200 步，再插值到 n 点
    n_fine = 500
    dr = (r2 - r1) / n_fine

    r_vals = [r1 + i * dr for i in range(n_fine + 1)]
    theta_vals = [0.0]

    for i in range(1, len(r_vals)):
        r = r_vals[i]
        t = (r - r1) / (r2 - r1)
        beta_at = math.radians(beta1 + t * (beta2 - beta1))
        # dθ/dr = cot(β) / r
        # 当 β → 0 或 β → 180° 时 cot 发散，做保护
        if abs(math.sin(beta_at)) < 1e-6:
            dtheta_dr = 0.0
        else:
            dtheta_dr = math.cos(beta_at) / (r * math.sin(beta_at))
        theta_vals.append(theta_vals[-1] + dtheta_dr * dr)

    # 插值到 n 点
    total = float(len(r_vals))
    points = []
    for i in range(n):
        idx = int(i * (n_fine) / (n - 1)) if n > 1 else 0
        idx = min(idx, n_fine)
        r = r_vals[idx]
        theta = theta_vals[idx]
        x = r * math.cos(theta)
        y = r * math.sin(theta)
        t = (r - r1) / (r2 - r1) if r2 != r1 else 0
        beta = beta1 + t * (beta2 - beta1)
        points.append({
            "r": round(r, 2),
            "theta": round(math.degrees(theta), 3),
            "x": round(x, 3),
            "y": round(y, 3),
            "beta": round(beta, 1),
        })

    return points


# ═══════════════════════════════════════════════════════════════
# 单圆弧法（快速估计）
# ═══════════════════════════════════════════════════════════════
#
# 一个圆弧只能精确满足进口角 β₁，出口角是计算结果。
# 对于 β₁ 和 β₂ 差异不大的情况，偏差较小。
#
# 圆弧的确定：
#   进口点 A(r₁, 0)，切线方向角 β₁（从切向）
#   圆心 O_c 在过 A 的法线上，法线方向 (cosβ₁, -sinβ₁)
#   O_c = (r₁ + R·cosβ₁, -R·sinβ₁)
#
#   圆弧半径 R = (r₂² - r₁²) / (2·(r₂·cosβ₂ - r₁·cosβ₁))
#
#   然后求 O_c 圆与出口圆 r₂ 的交点，即 B 点。
# ═══════════════════════════════════════════════════════════════


def _single_arc(
    r1: float, r2: float,
    beta1: float, beta2: float,
    n: int,
) -> list[dict]:
    """
    单圆弧叶片型线

    直接用 β 角（从切向）计算。
    """
    b1 = math.radians(beta1)
    b2 = math.radians(beta2)

    # ── 圆弧半径 ──
    denom = 2.0 * (r2 * math.cos(b2) - r1 * math.cos(b1))
    if abs(denom) < 1e-6:
        raise ValueError(f"圆弧半径解奇异: β₁={beta1}° β₂={beta2}°")
    R = (r2**2 - r1**2) / denom
    if abs(R) < 5:
        raise ValueError(f"圆弧半径 |R|={abs(R):.0f}mm 过小")

    # ── 圆心：法线方向 (cosβ₁, -sinβ₁) ──
    xc = r1 + abs(R) * math.cos(b1)
    yc = -abs(R) * math.sin(b1)

    # ── 求 O_c 圆与出口圆的交点 ──
    d_centers = math.sqrt(xc**2 + yc**2)  # 圆心距
    R_abs = abs(R)

    if d_centers > R_abs + r2:
        raise ValueError(f"圆弧不交出口圆: 圆心距={d_centers:.0f} > R+R₂={R_abs+r2:.0f}")
    if d_centers < abs(R_abs - r2) and abs(R_abs - r2) - d_centers > 1:
        raise ValueError(f"圆弧不交出口圆: 圆心距={d_centers:.0f} < |R-R₂|={abs(R_abs-r2):.0f}")

    # 两圆交点
    a_val = (R_abs**2 - r2**2 + d_centers**2) / (2.0 * d_centers)
    h = math.sqrt(max(0.0, R_abs**2 - a_val**2))

    # 从原点指向圆心的方向
    xm = xc / d_centers
    ym = yc / d_centers

    xb1 = xm * a_val + ym * h
    yb1 = ym * a_val - xm * h
    xb2 = xm * a_val - ym * h
    yb2 = ym * a_val + xm * h

    # 选择正确交点（θ_B > θ_A = 0）
    th1 = math.atan2(yb1, xb1)
    th2 = math.atan2(yb2, xb2)

    # 先试正角度
    theta_B = max(th1, th2)

    # 验证 B 在出口圆上
    bx = r2 * math.cos(theta_B)
    by = r2 * math.sin(theta_B)
    dist_to_center = math.sqrt((bx - xc)**2 + (by - yc)**2)
    if abs(dist_to_center - R_abs) > 2.0:
        theta_B = min(th1, th2)

    # A 点相对圆心的角度
    ax = r1 - xc
    ay = 0 - yc
    theta_A = math.atan2(ay, ax)
    if theta_A > 0 and theta_B < theta_A:
        theta_B += 2 * math.pi

    d_theta = theta_B - theta_A

    # ── 生成中间点 ──
    points = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0
        theta = theta_A + t * d_theta
        x = xc + R_abs * math.cos(theta)
        y = yc + R_abs * math.sin(theta)
        r = math.sqrt(x**2 + y**2)
        ang = math.degrees(math.atan2(y, x))

        # 计算该点的 β 角（从切向）
        # 圆弧切向量（逆时针）
        tx = -math.sin(theta)
        ty = math.cos(theta)

        # 切向方向
        tn = math.sqrt(x**2 + y**2)
        px = -y / tn
        py = x / tn

        dot = tx * px + ty * py
        dot = max(-1.0, min(1.0, dot))
        beta_actual = math.degrees(math.acos(dot))

        points.append({
            "r": round(r, 2),
            "theta": round(ang, 3),
            "x": round(x, 3),
            "y": round(y, 3),
            "beta": round(beta_actual, 1),
        })

    return points


# ═══════════════════════════════════════════════════════════════
# 3D 叶片
# ═══════════════════════════════════════════════════════════════


def generate_3d_blade(
    profile_2d: list[dict],
    b1: float,
    b2: float,
    z_layers: int = 5,
) -> list[dict]:
    """
    二维型线 → 三维点云

    宽度从 b₁（进口）渐变到 b₂（出口）。
    """
    n_pts = len(profile_2d)
    pts = []
    for iz in range(z_layers):
        tz = iz / (z_layers - 1) if z_layers > 1 else 0
        for ip, pt in enumerate(profile_2d):
            tp = ip / (n_pts - 1) if n_pts > 1 else 0
            w = b1 + tp * (b2 - b1)
            z = tz * w - w / 2.0
            pts.append({
                "x": pt["x"], "y": pt["y"], "z": round(z, 2),
                "r": pt["r"], "theta": pt["theta"], "beta": pt["beta"],
            })
    return pts


# ═══════════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════════


def export_csv(points: list[dict], path: str):
    """导出 CSV（可导入 SolidWorks）"""
    keys = ["x", "y", "z", "r", "theta", "beta"] if "z" in points[0] \
            else ["x", "y", "r", "theta", "beta"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for pt in points:
            w.writerow({k: pt.get(k, 0) for k in keys})
    print(f"  📄 {path}  ({len(points)} pts)")


def export_sw_curve(points_3d: list[dict], path: str):
    """导出 SW 曲线文件 (x,y,z 格式)"""
    with open(path, "w") as f:
        f.write(f"# SW Curve — {len(points_3d)} pts\nx,y,z\n")
        for pt in points_3d:
            f.write(f"{pt['x']},{pt['y']},{pt.get('z',0)}\n")
    print(f"  📄 {path}")


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        (252, 700, 28, 35, "后向 工业风机"),
        (250, 550, 30, 45, "后向 中压风机"),
        (225, 550, 15, 150, "前向多翼"),
        (175, 390, 12, 90, "径向耐磨"),
        (350, 1000, 32, 42, "后向 大叶轮"),
        (120, 300, 25, 40, "后向 小型风机"),
    ]

    for r1, r2, b1, b2, name in tests:
        print(f"\n{'='*65}")
        print(f"  {name}   r₁={r1}→r₂={r2}  β₁={b1}°→β₂={b2}°")
        print(f"{'='*65}")

        for ct in CurveType:
            try:
                pts = generate_blade_profile(r1, r2, b1, b2, ct, 20)
                theta_t = pts[-1]["theta"]
                ba1 = pts[0]["beta"]
                ba2 = pts[-1]["beta"]
                err_b1 = abs(ba1 - b1)
                err_b2 = abs(ba2 - b2)
                status = "✅"
                if err_b1 > 5 or err_b2 > 5:
                    status = "⚡"
                print(f"  {ct.value:14s} {status} "
                      f"θ={theta_t:6.1f}°  "
                      f"β₁={ba1:5.1f}°(Δ{err_b1:.0f})  "
                      f"β₂={ba2:5.1f}°(Δ{err_b2:.0f})  "
                      f"r₂={pts[-1]['r']:7.1f}")
            except ValueError as e:
                print(f"  {ct.value:14s} ❌ {e}")

    print("\n\n  ==== 导出测试 ====")
    pts = generate_blade_profile(252, 700, 28, 35, CurveType.MARCHING, 50)
    pts_3d = generate_3d_blade(pts, b1=80, b2=60)
    export_csv(pts_3d, "/tmp/blade_test_3d.csv")
    export_sw_curve(pts_3d, "/tmp/blade_test.sldcrv")
