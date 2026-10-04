"""
轴流风机叶片型线生成器

基于翼型截面（CLARK-Y、LS 系列、RAF 系列、NACA 系列等）
生成三维叶片曲面。

核心流程：
1. 生成翼型坐标（上下表面点云）
2. 按安装角旋转
3. 沿径向定位
4. 输出点云坐标

支持导出 .sldcrv 格式（SolidWorks 曲线文件）
"""

import math
import csv
from typing import Optional

from .params import AirfoilType, BladeSection


# ═══════════════════════════════════════════════════════════════
# 翼型坐标生成
# ═══════════════════════════════════════════════════════════════
#
# 用参数化方法生成各类翼型坐标。
# 每种翼型由：
#   1. 中弧线（camber line）—— y_c(x)
#   2. 厚度分布 —— t(x)
#   3. 上下表面：y_upper = y_c + t/2, y_lower = y_c - t/2
#
# x 为弦长方向，0~1（无量纲）
# y 为厚度方向（无量纲，以弦长为单位）
# ═══════════════════════════════════════════════════════════════


def generate_airfoil_coords(
    airfoil: AirfoilType,
    n_upper: int = 50,
    n_lower: int = 50,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    生成翼型上下表面坐标

    返回 (upper, lower)，每个元素为 (x/c, y/c) 列表。
    x: % 弦长位置 (0~1)
    y: % 弦长的厚度

    Args:
        airfoil: 翼型类型
        n_upper: 上表面点数
        n_lower: 下表面点数

    Returns:
        (upper_coords, lower_coords)
    """
    # 获取中弧线和厚度分布参数
    camber_fn, thickness_fn = _get_airfoil_functions(airfoil)

    # ── 生成上表面 ──
    upper = []
    # 从前缘到后缘，上表面
    for i in range(n_upper + 1):
        x = i / n_upper
        x = _cosine_spacing(x)  # 前缘加密
        y_c = camber_fn(x)
        t = thickness_fn(x)
        y_u = y_c + t / 2.0
        upper.append((round(x, 6), round(y_u, 6)))

    # ── 生成下表面 ──
    lower = []
    for i in range(n_lower + 1):
        x = i / n_lower
        x = _cosine_spacing(x)  # 后缘不加密，直接线性也ok
        # 反转排序使下表面从前缘到后缘
        x = 1.0 - x  # 从后缘到前缘再反转
        y_c = camber_fn(x)
        t = thickness_fn(x)
        y_l = y_c - t / 2.0
        lower.append((round(x, 6), round(y_l, 6)))

    return upper, lower


def _cosine_spacing(t: float) -> float:
    """
    余弦分布点：前缘和后缘加密，中间稀疏

    输入 t ∈ [0,1] 均匀分布
    输出 x ∈ [0,1] 余弦分布
    """
    return 0.5 * (1.0 - math.cos(t * math.pi))


def _get_airfoil_functions(
    airfoil: AirfoilType,
) -> tuple:
    """
    获取翼型的中弧线和厚度分布函数

    返回 (camber_fn, thickness_fn) 两个函数。
    输入 x ∈ [0,1]，输出 y/c（单位弦长的y值）。
    """
    airfoil_map = {
        AirfoilType.CLARK_Y: (_clark_y_camber, _clark_y_thickness),
        AirfoilType.LS_0413: (_naca_style_camber, _ls_0413_thickness),
        AirfoilType.LS_0409: (_naca_style_camber, _ls_0409_thickness),
        AirfoilType.RAF_30: (_raf_30_camber, _raf_30_thickness),
        AirfoilType.RAF_38: (_raf_38_camber, _raf_38_thickness),
        AirfoilType.NACA_4412: (_naca_4412_camber, _naca_4412_thickness),
        AirfoilType.NACA_2412: (_naca_2412_camber, _naca_2412_thickness),
        AirfoilType.CUSTOM: (_clark_y_camber, _clark_y_thickness),
    }
    fn = airfoil_map.get(airfoil, (_clark_y_camber, _clark_y_thickness))
    return fn


# ═══════════════════════════════════════════════════════════════
# CLARK-Y 翼型
#
# CLARK-Y 是美国 NACA 早期翼型，扁平下表面，最大弯度 3.5% @ 40%弦长
# 最大厚度 11.7% @ 28%弦长
# ═══════════════════════════════════════════════════════════════


def _clark_y_camber(x: float) -> float:
    """
    CLARK-Y 中弧线
    近似：最大弯度 3.5% @ 40% 弦长
    """
    if x <= 0:
        return 0.0
    if x <= 0.40:
        return 0.035 * (x / 0.40) * (2.0 - x / 0.40)
    else:
        return 0.035 * ((1.0 - x) / 0.60) * (2.0 - (1.0 - x) / 0.60)


def _clark_y_thickness(x: float) -> float:
    """
    CLARK-Y 厚度分布
    最大厚度 11.7% @ 28% 弦长
    使用 NACA 4位 厚度分布近似
    """
    t_max = 0.117
    return _naca_thickness_distribution(x, t_max)


# ═══════════════════════════════════════════════════════════════
# NACA 4位数字翼型
#
# NACA 4位由 4 个数字定义:
#  第1位: 最大弯度 (%弦长)
#  第2位: 最大弯度位置 (10倍%弦长)
#  第3-4位: 最大厚度 (%弦长)
# ═══════════════════════════════════════════════════════════════


def _naca_thickness_distribution(x: float, t_max: float) -> float:
    """
    NACA 厚度分布公式

    t(x) = 5·t_max · (0.2969·√x - 0.1260·x - 0.3516·x² + 0.2843·x³ - 0.1015·x⁴)
    """
    if x <= 0 or x >= 1.0:
        return 0.0
    sqrt_x = math.sqrt(x)
    return 5.0 * t_max * (
        0.2969 * sqrt_x
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )


def _naca_camber_line(x: float, m: float, p: float) -> float:
    """
    NACA 中弧线公式

    m: 最大弯度 (%弦长)
    p: 最大弯度位置 (%弦长)
    """
    if x <= 0:
        return 0.0
    if x <= p:
        return m / p**2 * (2.0 * p * x - x**2)
    else:
        return m / (1.0 - p)**2 * ((1.0 - 2.0 * p) + 2.0 * p * x - x**2)


def _naca_4412_camber(x: float) -> float:
    """NACA 4412: 最大弯度 4%, 最大弯度位置 40%"""
    return _naca_camber_line(x, 0.04, 0.40)


def _naca_4412_thickness(x: float) -> float:
    """NACA 4412: 最大厚度 12%"""
    return _naca_thickness_distribution(x, 0.12)


def _naca_2412_camber(x: float) -> float:
    """NACA 2412: 最大弯度 2%, 最大弯度位置 40%"""
    return _naca_camber_line(x, 0.02, 0.40)


def _naca_2412_thickness(x: float) -> float:
    """NACA 2412: 最大厚度 12%"""
    return _naca_thickness_distribution(x, 0.12)


# ═══════════════════════════════════════════════════════════════
# LS 系列翼型（薄翼型，用于低压轴流）
#
# LS-0413: 厚度 4%, LS-0409: 厚度 3%
# 都是对称/低弯度翼型
# ═══════════════════════════════════════════════════════════════


def _naca_style_camber(x: float) -> float:
    """
    LS 系列中弧线 — 很小弯度，近似对称

    最大弯度 1.5% @ 40% 弦长
    """
    m = 0.015
    p = 0.40
    return _naca_camber_line(x, m, p)


def _ls_0413_thickness(x: float) -> float:
    """LS-0413: 最大厚度 4%"""
    return _naca_thickness_distribution(x, 0.04)


def _ls_0409_thickness(x: float) -> float:
    """LS-0409: 最大厚度 3%"""
    return _naca_thickness_distribution(x, 0.03)


# ═══════════════════════════════════════════════════════════════
# RAF 系列翼型（经典厚翼型）
#
# RAF-30: 最大厚度 12%，中弯度
# RAF-38: 最大厚度 15%，高弯度（适合高压轴流）
# ═══════════════════════════════════════════════════════════════


def _raf_30_camber(x: float) -> float:
    """
    RAF-30 中弧线近似
    最大弯度 3.0% @ 40% 弦长
    """
    m = 0.03
    p = 0.40
    return _naca_camber_line(x, m, p)


def _raf_30_thickness(x: float) -> float:
    """RAF-30: 最大厚度 12%"""
    return _naca_thickness_distribution(x, 0.12)


def _raf_38_camber(x: float) -> float:
    """
    RAF-38 中弧线近似
    最大弯度 4.5% @ 40% 弦长
    """
    m = 0.045
    p = 0.40
    return _naca_camber_line(x, m, p)


def _raf_38_thickness(x: float) -> float:
    """RAF-38: 最大厚度 15%"""
    return _naca_thickness_distribution(x, 0.15)


# ═══════════════════════════════════════════════════════════════
# 三维叶片生成
# ═══════════════════════════════════════════════════════════════
#
# 轴向坐标系约定 (SolidWorks 标准)：
#   X — 轴向（沿旋转轴），正方向为出风方向
#   Y — 径向，指向叶片叶尖方向
#   Z — 周向，完成右手系
#
# 每个截面的翼型定位：
#   1. 在局部 2D 坐标系中生成翼型 (x_airfoil, y_airfoil)
#      弦长方向沿 x_local，厚度方向沿 y_local
#   2. 旋转安装角 χ（stagger angle）
#      (x_local 绕原点转 χ 到 SW 的 X-Z 平面)
#   3. 平移到径向位置 r 和轴向位置
# ═══════════════════════════════════════════════════════════════


def generate_blade_points(
    sections: list[BladeSection],
    airfoil: AirfoilType,
    n_per_section: int = 40,
    z_layers: int = 1,
) -> list[dict]:
    """
    生成完整三维叶片点云

    Args:
        sections: 各截面参数列表（来自设计引擎）
        airfoil: 翼型类型
        n_per_section: 每截面上/下表面点数
        z_layers: 厚度方向层数（>1 用于体网格）

    Returns:
        [{"x", "y", "z", "r", "c", "chi", "section_idx", "layer"}, ...]
    """
    if not sections:
        return []

    # 生成翼型
    upper, lower = generate_airfoil_coords(airfoil, n_per_section, n_per_section)

    # 组合完整翼型截面（从上表面前缘到上表面后缘）
    # 上表面: 前缘 → 后缘
    # 下表面: 后缘 → 前缘（反向）
    airfoil_polyline = []
    for xu, yu in upper:
        airfoil_polyline.append((xu, yu))
    for xl, yl in reversed(lower):
        airfoil_polyline.append((xl, yl))

    points = []

    for idx, sec in enumerate(sections):
        r = sec.r           # 截面半径 mm
        c = sec.c           # 弦长 mm
        chi = sec.chi       # 安装角 (°)

        # 弦长方向在 SW X-Z 平面中旋转
        chi_rad = math.radians(chi)

        # 轴向位置（各截面在轴向上居中排列）
        # 简单处理：所有截面在同一轴向平面（轴流叶片基本在同一平面）
        x_axial_offset = 0.0  # 所有截面共面

        for ip, (x_local, y_local) in enumerate(airfoil_polyline):
            # 缩放至实际弦长
            xs = x_local * c      # 弦长方向尺寸 (mm)
            ys = y_local * c      # 厚度方向尺寸 (mm)

            # 坐标系映射到 SW 全局坐标系：
            #   x_local (弦长) → SW: X cos(χ) - Z sin(χ)
            #   y_local (厚度) → SW: Y（径向）—— 简化处理
            #
            # 更精确的处理：叶片在 X-Z 平面内转动
            # X ← xs * cos(χ)      （轴向）
            # Y ← r                 （径向位置）
            # Z ← xs * sin(χ) + ys  （周向）

            x_sw = xs * math.cos(chi_rad) + x_axial_offset
            y_sw = r                   # 径向位置 = 该截面半径
            z_sw = xs * math.sin(chi_rad) + ys

            point = {
                "x": round(x_sw, 3),
                "y": round(y_sw, 3),
                "z": round(z_sw, 3),
                "r": round(r, 2),
                "c": round(c, 2),
                "chi": round(chi, 2),
                "section_idx": idx,
                "point_idx": ip,
                "layer": 0,
            }
            points.append(point)

    return points


def generate_blade_loft_profile(
    sections: list[BladeSection],
    airfoil: AirfoilType,
    n_per_section: int = 20,
) -> dict:
    """
    生成适合放样的叶片曲线数据

    返回上下表面各一条 3D 样条曲线。
    用于 SolidWorks Loft 特征。

    Returns:
        {
            "upper_curves": [[{x,y,z}, ...], ...],  每个截面一条
            "lower_curves": [[{x,y,z}, ...], ...],
            "hub_curve": [{x,y,z}, ...],     轮毂侧
            "tip_curve": [{x,y,z}, ...],     叶尖侧
        }
    """
    if not sections:
        return {"upper_curves": [], "lower_curves": [], "hub_curve": [], "tip_curve": []}

    upper, lower = generate_airfoil_coords(airfoil, n_per_section, n_per_section)

    upper_curves = []
    lower_curves = []
    hub_curve = []
    tip_curve = []

    # 每个截面的上表面曲线
    for idx, sec in enumerate(sections):
        r = sec.r
        c = sec.c
        chi = sec.chi
        chi_rad = math.radians(chi)

        # 上表面点
        up_pts = []
        for xu, yu in upper:
            xs = xu * c
            ys = yu * c
            x_sw = xs * math.cos(chi_rad)
            y_sw = r
            z_sw = xs * math.sin(chi_rad) + ys
            up_pts.append({"x": round(x_sw, 3), "y": round(y_sw, 3), "z": round(z_sw, 3)})
        upper_curves.append(up_pts)

        # 下表面点
        lo_pts = []
        for xl, yl in lower:
            xs = xl * c
            ys = yl * c
            x_sw = xs * math.cos(chi_rad)
            y_sw = r
            z_sw = xs * math.sin(chi_rad) + ys
            lo_pts.append({"x": round(x_sw, 3), "y": round(y_sw, 3), "z": round(z_sw, 3)})
        lower_curves.append(lo_pts)

    # 叶根和叶尖曲线（上下表面连接线）
    if sections:
        # 叶根：第一个截面（轮毂侧）
        hub_upper = upper_curves[0]
        hub_lower = list(reversed(lower_curves[0]))  # 反向连接
        # 从前缘到后缘再回前缘
        hub_curve = hub_upper + hub_lower

        # 叶尖：最后一个截面（叶尖侧）
        tip_upper = upper_curves[-1]
        tip_lower = list(reversed(lower_curves[-1]))
        tip_curve = tip_upper + tip_lower

    return {
        "upper_curves": upper_curves,
        "lower_curves": lower_curves,
        "hub_curve": hub_curve,
        "tip_curve": tip_curve,
    }


# ═══════════════════════════════════════════════════════════════
# 数据导出
# ═══════════════════════════════════════════════════════════════


def export_csv(points: list[dict], path: str):
    """导出点云 CSV"""
    keys = ["x", "y", "z", "r", "c", "chi", "section_idx"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for pt in points:
            w.writerow({k: pt.get(k, 0) for k in keys})
    print(f"  📄 {path}  ({len(points)} pts)")


def export_sw_curve(points_3d: list[dict], path: str):
    """
    导出 SolidWorks .sldcrv 曲线文件

    格式：每行 x,y,z
    适合 SolidWorks 曲线通过 XYZ 点功能导入。
    """
    with open(path, "w") as f:
        f.write(f"# SW Curve — Axial Fan Blade ({len(points_3d)} pts)\n")
        f.write("x,y,z\n")
        for pt in points_3d:
            f.write(f"{pt['x']},{pt['y']},{pt.get('z', 0)}\n")
    print(f"  📄 {path}")


def export_loft_sections(loft_data: dict, path_prefix: str):
    """
    导出放样截面曲线（每个截面一个 .csv 文件）

    用于 SolidWorks 放样建模。

    Args:
        loft_data: generate_blade_loft_profile 的返回值
        path_prefix: 文件路径前缀
    """
    upper_curves = loft_data["upper_curves"]
    lower_curves = loft_data["lower_curves"]

    for idx in range(len(upper_curves)):
        # 上表面截面
        path = f"{path_prefix}_section_{idx}_upper.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["x", "y", "z"])
            writer.writeheader()
            writer.writerows(upper_curves[idx])
        print(f"  📄 {path}")

        # 下表面截面
        path = f"{path_prefix}_section_{idx}_lower.csv"
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["x", "y", "z"])
            writer.writeheader()
            writer.writerows(lower_curves[idx])
        print(f"  📄 {path}")

    # 叶根/叶尖曲线
    for name in ["hub_curve", "tip_curve"]:
        curve = loft_data[name]
        if curve:
            path = f"{path_prefix}_{name}.csv"
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["x", "y", "z"])
                writer.writeheader()
                writer.writerows(curve)
            print(f"  📄 {path}")


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "..")

    # 生成各翼型坐标验证
    print(f"{'='*60}")
    print("  翼型坐标测试")
    print(f"{'='*60}")

    for airfoil in AirfoilType:
        if airfoil == AirfoilType.CUSTOM:
            continue
        upper, lower = generate_airfoil_coords(airfoil, 20, 20)
        print(f"  {airfoil.value:15s}: upper={len(upper)}pts  lower={len(lower)}pts  "
              f"t_max={airfoil.max_thickness_pct:.1f}%")

    # 测试三维叶片点云生成
    print(f"\n{'='*60}")
    print("  3D 叶片点云测试")
    print(f"{'='*60}")

    # 创建测试截面
    from .params import BladeSection, AirfoilType
    test_sections = [
        BladeSection(r=100, r_pct=0.0, r_star=0.4, u=30, w1=35, w2=30,
                     v1=20, v2=22, beta1=55, beta2=35, alpha1=90, alpha2=65,
                     theta=20, chi=45, c=80, t=9.4, cl=0.8, aoa=4.0, Gamma=2.5),
        BladeSection(r=150, r_pct=0.33, r_star=0.6, u=45, w1=50, w2=45,
                     v1=20, v2=22, beta1=45, beta2=28, alpha1=90, alpha2=65,
                     theta=17, chi=36.5, c=65, t=7.6, cl=0.8, aoa=4.0, Gamma=1.8),
        BladeSection(r=200, r_pct=0.67, r_star=0.8, u=60, w1=65, w2=60,
                     v1=20, v2=22, beta1=35, beta2=22, alpha1=90, alpha2=65,
                     theta=13, chi=28.5, c=50, t=5.9, cl=0.8, aoa=4.0, Gamma=1.3),
        BladeSection(r=250, r_pct=1.0, r_star=1.0, u=75, w1=80, w2=75,
                     v1=20, v2=22, beta1=28, beta2=18, alpha1=90, alpha2=65,
                     theta=10, chi=23, c=40, t=4.7, cl=0.8, aoa=4.0, Gamma=1.0),
    ]

    points = generate_blade_points(test_sections, AirfoilType.CLARK_Y, 30)
    print(f"  生成点云: {len(points)} pts ({len(test_sections)} 截面)")

    loft = generate_blade_loft_profile(test_sections, AirfoilType.CLARK_Y, 20)
    print(f"  放样数据: {len(loft['upper_curves'])} 上表面曲线, "
          f"{len(loft['hub_curve'])} 叶根点, {len(loft['tip_curve'])} 叶尖点")

    # 导出测试
    export_csv(points, "/tmp/axial_blade_test.csv")
    export_sw_curve(points[:200], "/tmp/axial_blade_test.sldcrv")
