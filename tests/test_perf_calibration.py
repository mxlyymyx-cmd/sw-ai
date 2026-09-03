"""
性能曲线标定验证 — 对照真实风机系列选用表

标定基准（x = Q/Q_d，Q_d/P_d/η_d 取表内 η_max 工况）：
  T4-72 No.5A @2900 r/min（8 点，x∈[0.66,1.26]）— 后弯叶片
  9-19  No.4A @2900 r/min（7 点，x∈[0.65,1.35]）— 前向叶片
  9-26  No.4A @2900 r/min（7 点，x∈[0.73,1.27]）— 径向出口（斜前）
  轴流 — T35-11 型谱 + 文献驼峰形（未实测标定，仅验证形态）

数据来源（2026-09 抓取）：
  T4-72: zbsgfans.com T4-72 型离心通风机性能与选用件表
  9-19:  zbsgfans.com 9-19 No4A/4.5A/5A/5.6A 选用件表（含内效率）
  9-26:  sythfj.com 9-19/9-26 性能参数表（无效率列）
"""

import math

import pytest

from perf import (
    AXIAL_STALL_X,
    _X_STALL,
    _eta_ratio,
    _psi_shape_axial,
    _psi_shape_centrifugal,
    perf_curve,
)
from impeller.design import design_impeller
from impeller.params import BladeType, ImpellerDesignInput
from axial.design import design_axial_fan
from axial.params import AxialFanInput


# ═══════════════════════════════════════════════════════════════
# 真实系列选用表（原始量：Q m³/h, P Pa, η）
# ═══════════════════════════════════════════════════════════════

T4_72_5A_2900 = {   # 后弯基准，η_max=83.5% @ 序号5
    "Q": [7352, 8318, 9284, 10249, 11215, 12181, 13147, 14113],
    "P": [3195, 3145, 3067, 2954, 2778, 2581, 2314, 1998],
    "eta": [0.751, 0.783, 0.808, 0.826, 0.835, 0.828, 0.802, 0.751],
}

N919_4A_2900 = {    # 前向基准，η_max=76.0% @ 序号4
    "Q": [824, 970, 1116, 1264, 1410, 1558, 1704],
    "P": [3584, 3665, 3647, 3597, 3507, 3384, 3253],
    "eta": [0.700, 0.735, 0.755, 0.760, 0.755, 0.733, 0.700],
}

N926_4A_2900 = {    # 径向出口基准（无效率列，取序号4为设计点）
    "Q": [2198, 2473, 2748, 3022, 3297, 3572, 3847],
    "P": [3930, 3850, 3740, 3590, 3420, 3210, 3000],
}


def _normalized(series: dict, design_idx: int):
    """按设计工况归一化: x=Q/Q_d, psi_r=P/P_d, eta_r=eta/eta_d"""
    Q, P = series["Q"], series["P"]
    Qd, Pd = Q[design_idx], P[design_idx]
    etd = series["eta"][design_idx] if series.get("eta") else None
    pts = []
    for i in range(len(Q)):
        pts.append({
            "x": Q[i] / Qd,
            "psi_r": P[i] / Pd,
            "eta_r": series["eta"][i] / etd if etd else None,
        })
    return pts


# ═══════════════════════════════════════════════════════════════
# 离心压力曲线标定（ψ/ψ_d）
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("blade,series,idx,tol", [
    (BladeType.BACKWARD, T4_72_5A_2900, 4, 0.010),   # T4-72: 残差≤0.8%
    (BladeType.AIRFOIL, T4_72_5A_2900, 4, 0.010),    # 机翼型同后弯
    (BladeType.RADIAL_TIP, N926_4A_2900, 3, 0.010),   # 9-26: 残差≤0.6%
    (BladeType.RADIAL, N926_4A_2900, 3, 0.010),
    (BladeType.FORWARD, N919_4A_2900, 3, 0.050),      # 9-19: 首点驼峰偏差 4.7%
])
def test_psi_calibration(blade, series, idx, tol):
    """压力曲线模型 vs 系列表全工况点（归一化 ψ_r 逐点对比）"""
    for pt in _normalized(series, idx):
        model = _psi_shape_centrifugal(blade, pt["x"])
        assert abs(model - pt["psi_r"]) <= tol, (
            f"{blade.value} x={pt['x']:.3f}: "
            f"model={model:.4f} data={pt['psi_r']:.4f}")


# ═══════════════════════════════════════════════════════════════
# 离心效率曲线标定（η/η_d）
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("blade,series,idx", [
    (BladeType.BACKWARD, T4_72_5A_2900, 4),
    (BladeType.FORWARD, N919_4A_2900, 3),
])
def test_eta_calibration(blade, series, idx):
    """效率曲线模型 vs 系列表（归一化 η_r 逐点对比，容差 1%）"""
    for pt in _normalized(series, idx):
        if pt["eta_r"] is None:
            continue
        model = _eta_ratio("centrifugal", blade, pt["x"])
        assert abs(model - pt["eta_r"]) <= 0.010, (
            f"{blade.value} x={pt['x']:.3f}: "
            f"model={model:.4f} data={pt['eta_r']:.4f}")


# ═══════════════════════════════════════════════════════════════
# 轴流驼峰/失速形态（文献模型，未实测标定）
# ═══════════════════════════════════════════════════════════════

def test_axial_saddle_shape():
    """轴流压力曲线呈驼峰形：失速边界峰值 → 失速后跌落 → 关死点回升"""
    psi = _psi_shape_axial
    # 失速边界处峰值 ≈ 1.20·P_d
    assert abs(psi(AXIAL_STALL_X) - 1.20) < 0.01
    # 失速后压力跌落（鞍底明显低于失速峰值）
    assert psi(0.50) < psi(AXIAL_STALL_X) - 0.25
    # 关死点回升（马鞍形，但仍低于失速峰值）
    assert psi(0.0) > psi(0.35)
    assert psi(0.0) < psi(AXIAL_STALL_X)
    # 设计点锚定
    assert abs(psi(1.0) - 1.0) < 1e-9


def test_axial_stable_branch_monotone():
    """稳定段（x ≥ 失速边界）压力随流量单调下降且右侧陡峭"""
    xs = [x / 100 for x in range(70, 126, 5)]
    vals = [_psi_shape_axial(x) for x in xs]
    for a, b in zip(vals, vals[1:]):
        assert b < a, f"稳定段非单调下降: {xs} -> {vals}"
    # 右侧陡峭：x 1.0→1.2 压力降 ≥ 0.14·P_d
    assert _psi_shape_axial(1.0) - _psi_shape_axial(1.2) >= 0.14


def test_axial_eta_stall_collapse():
    """失速后效率坍缩；设计点效率为峰值"""
    assert _eta_ratio("axial", None, 1.0) == 1.0
    assert _eta_ratio("axial", None, 0.5) < 0.6
    assert _eta_ratio("axial", None, 0.2) == pytest.approx(0.25)
    # 高效区窄：x=0.75 与 x=1.2 处均降至 ~90%
    assert abs(_eta_ratio("axial", None, 0.75) - 0.875) < 0.01
    assert abs(_eta_ratio("axial", None, 1.2) - 0.904) < 0.01


# ═══════════════════════════════════════════════════════════════
# 整机曲线一致性
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def centrifugal_design():
    return design_impeller(ImpellerDesignInput(Q=5000, P=2500, n=2900))


@pytest.fixture(scope="module")
def axial_design():
    return design_axial_fan(AxialFanInput(Q=50000, P=300, n=730))


def test_design_point_anchor(centrifugal_design, axial_design):
    """x=1 采样点严格锚定设计工况（P=P_d, η=η_d, N=N_d）"""
    for design in (centrifugal_design, axial_design):
        curve = perf_curve(design)
        hits = [p for p in curve.points if abs(p.Q - curve.Q_d) / curve.Q_d < 0.01]
        assert hits, "曲线采样必须包含 x=1 设计点"
        p = hits[0]
        assert p.P == pytest.approx(curve.P_d, rel=1e-6)
        assert p.eta == pytest.approx(curve.eta_d, rel=1e-6)
        assert p.N == pytest.approx(curve.N_d, rel=1e-6)


def test_power_consistency(centrifugal_design, axial_design):
    """每个工况点满足 N = Q·P/(3600·1000·η)"""
    for design in (centrifugal_design, axial_design):
        for p in perf_curve(design).points:
            expected = p.Q / 3600.0 * p.P / (1000.0 * p.eta)
            assert p.N == pytest.approx(expected, rel=1e-6), f"Q={p.Q}"


def test_similarity_law(centrifugal_design):
    """变转速相似换算: Q∝n, P∝n², N∝n³, η 不变"""
    c1 = perf_curve(centrifugal_design)
    k = 0.5
    c2 = c1.at_speed(c1.n * k)
    assert c2.n == c1.n * k
    assert c2.Q_d == pytest.approx(c1.Q_d * k)
    assert c2.P_d == pytest.approx(c1.P_d * k * k)
    assert c2.N_d == pytest.approx(c1.N_d * k ** 3)
    assert c2.eta_d == c1.eta_d
    assert len(c2.points) == len(c1.points)
    for a, b in zip(c1.points, c2.points):
        assert b.Q == pytest.approx(a.Q * k)
        assert b.P == pytest.approx(a.P * k * k)
        assert b.N == pytest.approx(a.N * k ** 3)
        assert b.eta == a.eta


def test_at_speed_rejects_nonpositive(centrifugal_design):
    with pytest.raises(ValueError):
        perf_curve(centrifugal_design).at_speed(0)


def test_stall_boundaries(centrifugal_design, axial_design):
    """失速边界按系列表流量下限设定"""
    c = perf_curve(centrifugal_design)
    blade = centrifugal_design.blade_type.value
    assert c.Q_stall == pytest.approx(c.Q_d * _X_STALL[blade])
    a = perf_curve(axial_design)
    assert a.Q_stall == pytest.approx(a.Q_d * AXIAL_STALL_X)
    assert 0 < a.stability_margin < 1


def test_all_points_physical(centrifugal_design, axial_design):
    """曲线物理合理性: P>0, 0<η≤η_d·1.06, N>0"""
    for design in (centrifugal_design, axial_design):
        curve = perf_curve(design)
        for p in curve.points:
            assert p.P > 0
            assert 0 < p.eta <= curve.eta_d * 1.06
            assert p.N > 0
