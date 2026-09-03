"""
法兰几何生成器 + VBA 宏测试

体积基准来自 SolidWorks 2022 E2E 实测（2026-09-03，7/7 通过，偏差 0.000%），
见 e2e_flange.py — 毛坯为 Pappus 旋转体，螺栓孔扣除含密封凸台环带弓形重叠修正。
"""

import math

import pytest

from e2e_flange import analytic_volume_mm3, revolve_volume_mm3
from flange.gb_standards import lookup
from flange.generator import (
    _bolt_hole_geometry,
    _flange_profile,
    generate_sw_macro,
)
from flange.params import FlangeType

ALL_TYPES = ["plate", "slip_on", "weld_neck", "blind"]

# (dn, pn, type): SolidWorks 实测体积 cm³
E2E_BENCHMARKS_CM3 = {
    (100, 16, "plate"): 566.2,
    (100, 16, "slip_on"): 655.7,
    (100, 16, "weld_neck"): 656.2,
    (100, 16, "blind"): 758.8,
    (50, 10, "blind"): 382.9,
    (300, 16, "weld_neck"): 2922.0,
    (150, 25, "slip_on"): 1567.4,
}


def _polygon_area(pts):
    """鞋带公式（带符号）"""
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


# ═══════════════════════════════════════════════════════════════
# 半剖面轮廓
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("ftype", ALL_TYPES)
@pytest.mark.parametrize("dn,pn", [(100, 16), (50, 10), (300, 16)])
def test_profile_structure(ftype, dn, pn):
    p = lookup(dn, pn, ftype)
    pts = _flange_profile(p)

    expected_n = {"plate": 6, "slip_on": 8, "weld_neck": 9, "blind": 6}[ftype]
    assert len(pts) == expected_n

    # 半径非负（旋转轴 X=0 在轮廓一侧）
    assert all(x >= 0 for x, _ in pts)
    # 密封面顶 y=0，全部向下延伸
    assert max(y for _, y in pts) == 0.0
    # 总高 = f + C + 颈长
    y_min = min(y for _, y in pts)
    assert y_min == pytest.approx(-(p.f + p.c + p.neck_h))
    # 封闭多边形面积非零
    assert abs(_polygon_area(pts)) > 1.0


def test_blind_profile_touches_axis():
    pts = _flange_profile(lookup(100, 16, "blind"))
    assert pts[0] == (0.0, 0.0)            # 密封面圆心在轴上
    assert pts[-1][0] == 0.0               # 背面封死


def test_bore_plate_and_neck_share_axis():
    """plate/SO/WN 内孔贯通: 轮廓起点/终点在 rb 半径"""
    for ftype in ("plate", "slip_on", "weld_neck"):
        p = lookup(100, 16, ftype)
        pts = _flange_profile(p)
        rb = p.inner_d / 2.0
        assert pts[0] == (rb, 0.0)
        assert pts[-1][0] == rb


def test_profile_requires_neck_params():
    """SO/WN 缺颈部参数 → ValueError"""
    p = lookup(100, 16, "plate")           # plate 无颈部数据
    p.flange_type = FlangeType.SLIP_ON
    with pytest.raises(ValueError, match="颈部"):
        _flange_profile(p)
    p.flange_type = FlangeType.WELD_NECK
    with pytest.raises(ValueError, match="颈部"):
        _flange_profile(p)


def test_profile_rejects_bad_geometry():
    p = lookup(100, 16, "plate")
    p.d1 = p.d                              # 密封面 = 外径 → 矛盾
    with pytest.raises(ValueError, match="几何矛盾"):
        _flange_profile(p)


# ═══════════════════════════════════════════════════════════════
# 螺栓孔
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("ftype", ALL_TYPES)
def test_bolt_hole_geometry(ftype):
    p = lookup(100, 16, ftype)
    r_pick, k_r, n_bolts, bolt_r = _bolt_hole_geometry(p)
    assert k_r == p.k / 2.0
    assert bolt_r == p.l / 2.0
    assert n_bolts == p.n
    # 选面参考点位于密封面环形区内（BL 为圆盘内）
    assert 0 < r_pick < p.d1 / 2.0


def test_bolt_holes_outside_bore():
    """螺栓孔不能碰到内孔/轴心"""
    for ftype in ALL_TYPES:
        p = lookup(150, 16, ftype)
        _, k_r, _, bolt_r = _bolt_hole_geometry(p)
        assert k_r - bolt_r > p.inner_d / 2.0


# ═══════════════════════════════════════════════════════════════
# 体积解析基准（SolidWorks E2E 回归）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("key,expected_cm3", E2E_BENCHMARKS_CM3.items())
def test_volume_e2e_benchmark(key, expected_cm3):
    dn, pn, ftype = key
    p = lookup(dn, pn, ftype)
    v = analytic_volume_mm3(p, _flange_profile(p))
    assert v / 1000.0 == pytest.approx(expected_cm3, rel=0.002)


@pytest.mark.parametrize("ftype", ["slip_on", "weld_neck", "blind"])
def test_blind_heavier_than_plate(ftype):
    """同规格下法兰盖体积 > 板式（无内孔）"""
    vp = analytic_volume_mm3(lookup(100, 16, "plate"),
                            _flange_profile(lookup(100, 16, "plate")))
    vb = analytic_volume_mm3(lookup(100, 16, ftype),
                            _flange_profile(lookup(100, 16, ftype)))
    assert vb > vp


def test_revolve_volume_matches_simple_cylinder():
    """矩形剖面旋转体 = 圆柱体积（Pappus 校验）"""
    R, H = 100.0, 20.0
    pts = [(50.0, 0.0), (R, 0.0), (R, -H), (50.0, -H)]
    expect = math.pi * (R * R - 50.0 * 50.0) * H
    assert revolve_volume_mm3(pts) == pytest.approx(expect)


# ═══════════════════════════════════════════════════════════════
# VBA 宏（SolidWorks 实测配方回归）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("ftype", ALL_TYPES)
def test_macro_structure(ftype):
    p = lookup(100, 16, ftype)
    m = generate_sw_macro(p)

    # VBA 骨架
    assert m.startswith("' SolidWorks 宏")
    assert "Sub main()" in m and m.count("End Sub") == 1

    # 旋转: 轴心线构造线 + 对象引用选择 + 8 参数 FeatureRevolve
    assert "Set segAxis = Part.CreateLine2(0#, 0.02#" in m
    assert "segAxis.ConstructionGeometry = True" in m
    assert "segAxis.Select2 True, 1" in m
    assert "featMgr.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)" in m

    # 切除: 26 参数 FeatureCut3（ThroughAll T1=1，SolidWorks 2022 实测签名）
    assert "FeatureCut3(True, False, False, 1, 1, 0#, 0#" in m
    primary_cut = m.split("FeatureCut3(")[1].split(")")[0]
    assert primary_cut.count(",") == 25

    # 螺栓孔数量恰好 = n（回归: 曾被 For 循环重复绘制）
    assert m.count("skMgr.CreateCircle") == p.n


def test_macro_bolt_count_follows_dn():
    assert generate_sw_macro(lookup(50, 10, "plate")).count("skMgr.CreateCircle") == 4
    assert generate_sw_macro(lookup(250, 16, "plate")).count("skMgr.CreateCircle") == 12


def test_macro_contains_dimensions():
    p = lookup(100, 16, "weld_neck")
    m = generate_sw_macro(p)
    # 半径以米为单位出现（D=220mm → R=110mm → 0.110）
    assert "0.110000#" in m
    # 对焊法兰含颈部注释
    assert "颈部" in m


@pytest.mark.parametrize("ftype", ALL_TYPES)
def test_macro_zero_values_kept(ftype):
    """0 值不被过滤（项目硬约束）"""
    m = generate_sw_macro(lookup(100, 16, ftype))
    assert "0.000000#" in m       # 轴心线起点
