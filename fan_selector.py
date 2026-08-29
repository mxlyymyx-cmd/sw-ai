"""
风机选型模块 — 离心 vs 轴流 机型选择 + 转速推荐

输入 Q（m³/h）、P（Pa），输出推荐机型 + 转速 + 完整设计结果。

选型流程：
  1. 对每个标准电机转速（2900/1450/960/730/580 r/min）计算比转速 n_s
  2. 按比转速判定机型适用性：
       n_s < 100        → 离心（前向/径向/后向由叶轮引擎按 n_s 细分）
       n_s 100~180      → 混流过渡区（离心、轴流皆可）
       n_s > 180        → 轴流
  3. 对每个可行的（机型, 转速）组合调用真实设计引擎完整试算
  4. 综合评分：闭环偏差、设计警告数、机型-比转速适配度、
     叶尖速度（噪音）、预期效率
  5. 推荐最优方案，附全部候选对比表

用法:
    from fan_selector import select_fan
    sel = select_fan(Q=20000, P=800)
    print(sel.summary)
    print(sel.best.design.summary)   # 完整设计结果
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Union

from impeller.params import ImpellerDesignInput, ImpellerDesignResult
from impeller.design import design_impeller
from axial.params import AxialFanInput, AxialFanResult
from axial.design import design_axial_fan

# 标准电机转速（异步电机额定转速，r/min）
STANDARD_SPEEDS = [2900, 1450, 960, 730, 580]

# 机型适用比转速范围（中国通风机行业惯例）
CENTRIFUGAL_NS_RANGE = (5.0, 110.0)
AXIAL_NS_RANGE = (60.0, 400.0)


def calc_ns(Q: float, P: float, n: float) -> float:
    """
    比转速 n_s = n·√Q / P^0.75

    Q: m³/h, P: Pa, n: r/min
    """
    Q_s = Q / 3600.0
    P_mm = P / 9.80665
    if Q_s <= 0 or P_mm <= 0:
        raise ValueError(f"流量和全压必须为正: Q={Q}m³/h, P={P}Pa")
    return n * math.sqrt(Q_s) / (P_mm ** 0.75)


# ═══════════════════════════════════════════════════════════════
# 候选方案
# ═══════════════════════════════════════════════════════════════


@dataclass
class FanCandidate:
    """一个（机型, 转速）候选方案，含完整设计结果"""
    machine: str            # "centrifugal" | "axial"
    n: float                # 转速 r/min
    ns: float               # 比转速
    design: Union[ImpellerDesignResult, AxialFanResult]
    score: float = 0.0      # 综合评分（越低越好）

    @property
    def machine_name(self) -> str:
        return "离心风机" if self.machine == "centrifugal" else "轴流风机"

    @property
    def D(self) -> float:
        """叶轮直径 mm"""
        return self.design.D2 if self.machine == "centrifugal" else self.design.D

    @property
    def eta(self) -> float:
        return self.design.eta

    @property
    def N_motor(self) -> float:
        return self.design.N_motor

    @property
    def tip_speed(self) -> float:
        """叶轮特征速度（离心 u₂ / 轴流叶尖 u_t）m/s"""
        return self.design.u2 if self.machine == "centrifugal" else self.design.u_tip

    @property
    def loop_dev(self) -> float:
        """设计闭环偏差（欧拉方程）"""
        return self.design.psi_dev if self.machine == "centrifugal" else self.design.P_dev

    @property
    def n_warnings(self) -> int:
        return len(self.design.warnings)


def _machine_fit_penalty(machine: str, ns: float) -> float:
    """
    机型-比转速适配度惩罚（0 = 最佳，越大越差）

    离心最佳 n_s = 40~70（高效区），可用 10~110
    轴流最佳 n_s = 180~250，可用 100~350
    """
    if machine == "centrifugal":
        if 40.0 <= ns <= 70.0:
            return 0.0
        if ns < 40.0:
            return (40.0 - ns) / 40.0            # 低 ns：径向/前向叶型仍可行
        return min((ns - 70.0) / 50.0, 2.0) * 2.0  # 高 ns 越界：轴流领地
    # axial
    if 180.0 <= ns <= 250.0:
        return 0.0
    if ns < 180.0:
        return min((180.0 - ns) / 180.0, 2.0) * 2.0  # 低 ns：叶根过载风险
    return min((ns - 250.0) / 100.0, 2.0)             # 高 ns：效率下滑


def _tip_speed_penalty(u: float) -> float:
    """叶尖速度惩罚（>110 m/s 开始，>150 m/s 严重——噪音与轮盘应力）"""
    if u <= 110.0:
        return 0.0
    return min((u - 110.0) / 40.0, 1.5)


def _score_candidate(cand: FanCandidate) -> float:
    """综合评分（越低越好）"""
    score = (
        8.0 * abs(cand.loop_dev)          # 闭环偏差：设计可信度
        + 2.0 * cand.n_warnings           # 设计警告
        + 1.0 * _machine_fit_penalty(cand.machine, cand.ns)
        + 0.8 * _tip_speed_penalty(cand.tip_speed)
        + 3.0 * max(0.0, 0.85 - cand.eta)  # 效率
    )
    if cand.n >= 2900:
        score += 0.2                       # 2 极电机噪音偏好
    return score


# ═══════════════════════════════════════════════════════════════
# 选型引擎
# ═══════════════════════════════════════════════════════════════


@dataclass
class SelectionResult:
    """选型结果"""
    Q: float
    P: float
    candidates: list[FanCandidate] = field(default_factory=list)
    best: Optional[FanCandidate] = None
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        lines = [
            f"{'='*55}",
            f"  风机选型结果",
            f"  工况: Q={self.Q:.0f} m³/h  P={self.P:.0f} Pa",
            f"{'='*55}",
        ]
        if self.best is None:
            lines.append("  ❌ 无可行方案（见说明）")
        else:
            b = self.best
            lines += [
                f"",
                f"  ✅ 推荐方案: {b.machine_name} @ {b.n:.0f} r/min",
                f"     比转速    n_s = {b.ns:.1f}",
                f"     叶轮直径  D   = {b.D:.0f} mm",
                f"     预期效率  η   = {b.eta:.1%}",
                f"     电机功率  N   = {b.N_motor:.1f} kW",
                f"     闭环偏差      = {b.loop_dev:+.1%}（欧拉方程验证）",
            ]
            if self.best.design.warnings:
                lines.append(f"     ⚠️  设计警告 {b.n_warnings} 条（详见设计结果）")

        if self.candidates:
            lines += [
                f"",
                f"  候选方案对比（按评分排序）:",
                f"  {'转速':>6} {'机型':>4} {'n_s':>7} {'D(mm)':>7} {'η':>6} "
                f"{'偏差':>7} {'警告':>4} {'评分':>6}",
                f"  {'─'*6} {'─'*4} {'─'*7} {'─'*7} {'─'*6} {'─'*7} {'─'*4} {'─'*6}",
            ]
            for c in sorted(self.candidates, key=lambda x: x.score):
                mark = " ←" if c is self.best else ""
                lines.append(
                    f"  {c.n:>6.0f} {('离心' if c.machine == 'centrifugal' else '轴流'):>4} "
                    f"{c.ns:>7.1f} {c.D:>7.0f} {c.eta:>6.1%} "
                    f"{c.loop_dev:>+7.1%} {c.n_warnings:>4} {c.score:>6.2f}{mark}")

        if self.notes:
            lines.append(f"")
            lines.append(f"  💡  选型说明:")
            for n in self.notes:
                lines.append(f"    • {n}")

        return "\n".join(lines)


def select_fan(
    Q: float,
    P: float,
    prefer: str = "auto",
    rho: float = 1.2,
) -> SelectionResult:
    """
    风机选型 — 主入口

    Args:
        Q: 流量 m³/h
        P: 全压 Pa
        prefer: 机型偏好 "auto"（自动）| "centrifugal" | "axial"
        rho: 介质密度 kg/m³

    Returns:
        SelectionResult（含推荐方案与全部候选）
    """
    if Q <= 0 or P <= 0:
        raise ValueError(f"流量和全压必须为正: Q={Q}m³/h, P={P}Pa")

    sel = SelectionResult(Q=Q, P=P)

    for n in STANDARD_SPEEDS:
        ns = calc_ns(Q, P, n)

        # ── 离心候选 ──
        if prefer in ("auto", "centrifugal") and \
                CENTRIFUGAL_NS_RANGE[0] <= ns <= CENTRIFUGAL_NS_RANGE[1]:
            try:
                design = design_impeller(ImpellerDesignInput(Q=Q, P=P, n=n, rho=rho))
                cand = FanCandidate(machine="centrifugal", n=n, ns=ns, design=design)
                cand.score = _score_candidate(cand)
                sel.candidates.append(cand)
            except (ValueError, ZeroDivisionError, OverflowError):
                pass

        # ── 轴流候选 ──
        if prefer in ("auto", "axial") and \
                AXIAL_NS_RANGE[0] <= ns <= AXIAL_NS_RANGE[1]:
            try:
                design = design_axial_fan(AxialFanInput(Q=Q, P=P, n=n, rho=rho))
                cand = FanCandidate(machine="axial", n=n, ns=ns, design=design)
                cand.score = _score_candidate(cand)
                sel.candidates.append(cand)
            except (ValueError, ZeroDivisionError, OverflowError):
                pass

    if not sel.candidates:
        sel.notes.append("所有标准转速下均无可行方案，请检查工况参数是否超出风机适用范围")
        return sel

    sel.candidates.sort(key=lambda x: x.score)
    sel.best = sel.candidates[0]

    # ── 选型说明 ──
    b = sel.best
    fit = _machine_fit_penalty(b.machine, b.ns)
    if fit < 0.05:
        sel.notes.append(
            f"n_s={b.ns:.1f} 位于{b.machine_name}高效区，机型匹配良好")
    elif b.machine == "centrifugal" and b.ns < 40:
        sel.notes.append(
            f"n_s={b.ns:.1f} 偏低，属高压小流量工况，离心叶型（径向/前向）为宜")
    elif b.machine == "axial" and b.ns < 180:
        sel.notes.append(
            f"n_s={b.ns:.1f} 处于混流过渡区，离心方案亦可比较（见候选表）")

    others = [c for c in sel.candidates if c.machine != b.machine]
    if others:
        alt = min(others, key=lambda x: x.score)
        if alt.score - b.score < 0.5:
            sel.notes.append(
                f"{alt.machine_name}@{alt.n:.0f}r/min 评分接近"
                f"（{alt.score:.2f} vs {b.score:.2f}），如有空间/噪音约束可改选")

    if b.tip_speed > 110:
        sel.notes.append(
            f"特征速度 {b.tip_speed:.0f} m/s 偏高，注意噪音治理与叶轮动平衡等级")

    return sel


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_cases = [
        (5000, 2500),     # 高压小流量 → 离心
        (20000, 800),      # 中压中流量 → 轴流/混流
        (50000, 300),      # 低压大流量 → 轴流
        (2000, 5000),      # 超高压 → 离心（前向）
        (100000, 1500),    # 大流量 → 轴流
        (50000, 2500),     # 中间工况
    ]

    for Q, P in test_cases:
        print(f"\n{'#'*60}")
        print(f"  工况: Q={Q} m³/h  P={P} Pa")
        print(f"{'#'*60}")
        try:
            sel = select_fan(Q=Q, P=P)
            print(sel.summary)
        except Exception as e:
            print(f"  ❌ 选型失败: {e}")
