"""
风机选型模块测试 — 比转速计算 + 6 类典型工况 + 评分与约束
"""

import math

import pytest

from fan_selector import (
    STANDARD_SPEEDS,
    calc_ns,
    select_fan,
)


def test_calc_ns_formula():
    """n_s = n·√Q / P^0.75（Q→m³/s，P→mmH2O）"""
    Q, P, n = 5000, 2500, 1450
    q_s = Q / 3600.0
    p_mm = P / 9.80665
    assert calc_ns(Q, P, n) == pytest.approx(n * math.sqrt(q_s) / p_mm ** 0.75)


def test_calc_ns_scales_with_speed():
    """同工况下 n_s ∝ n"""
    ns_2900 = calc_ns(20000, 800, 2900)
    ns_1450 = calc_ns(20000, 800, 1450)
    assert ns_2900 == pytest.approx(2 * ns_1450)


@pytest.mark.parametrize("Q,P", [(0, 100), (100, 0), (-1, -1)])
def test_invalid_input_raises(Q, P):
    with pytest.raises(ValueError):
        calc_ns(Q, P, n=1450)
    with pytest.raises(ValueError):
        select_fan(Q=Q, P=P)


# ═══════════════════════════════════════════════════════════════
# 典型工况选型（6 场景）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("Q,P,expect_machine", [
    (5000, 2500, "centrifugal"),    # 高压小流量 → 离心
    (2000, 5000, "centrifugal"),    # 超高压 → 离心（前向/径向）
    (50000, 300, "axial"),           # 低压大流量 → 轴流
    (100000, 1500, "axial"),         # 大流量 → 轴流
    (20000, 800, None),              # 混流过渡区（两类皆可，不指定）
    (50000, 2500, None),            # 中间工况（不指定）
])
def test_select_scenarios(Q, P, expect_machine):
    sel = select_fan(Q=Q, P=P)
    assert sel.candidates, "必须有可行候选"
    assert sel.best is not None
    if expect_machine:
        assert sel.best.machine == expect_machine
    assert sel.best.n in STANDARD_SPEEDS
    assert sel.best.D > 0
    assert 0.5 < sel.best.eta < 1.0
    assert sel.best.N_motor > 0
    assert sel.best.tip_speed > 0
    assert sel.Q == Q and sel.P == P


def test_all_candidates_physical():
    sel = select_fan(Q=20000, P=800)
    assert len(sel.candidates) >= 2
    for c in sel.candidates:
        assert c.machine in ("centrifugal", "axial")
        assert c.n in STANDARD_SPEEDS
        assert c.ns > 0
        assert c.score >= 0


def test_best_is_argmin_score():
    sel = select_fan(Q=20000, P=800)
    assert sel.best.score == pytest.approx(min(c.score for c in sel.candidates))


def test_candidates_sorted_by_score():
    sel = select_fan(Q=50000, P=300)
    scores = [c.score for c in sel.candidates]
    assert scores == sorted(scores)


def test_prefer_axial_forces_machine():
    sel = select_fan(Q=50000, P=300, prefer="axial")
    assert sel.candidates
    assert all(c.machine == "axial" for c in sel.candidates)


def test_prefer_centrifugal_forces_machine():
    sel = select_fan(Q=5000, P=2500, prefer="centrifugal")
    assert sel.candidates
    assert all(c.machine == "centrifugal" for c in sel.candidates)


def test_summary_renders():
    sel = select_fan(Q=50000, P=300)
    s = sel.summary
    assert "推荐方案" in s
    assert "候选方案对比" in s
    assert "轴流风机" in s
