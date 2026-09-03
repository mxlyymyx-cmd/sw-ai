"""
风机性能曲线生成 — P-Q / η-Q 曲线 + 变转速相似换算

从设计工况点出发，按无量纲相似原理生成整条性能曲线：
  离心风机: ψ/ψ_d = a − (a−1)·x^p 幂律（按真实系列选用表最小二乘标定）
  轴流风机: 驼峰形压力曲线 + 失速鞍形跌落 + 窄高效区

标定状态（2026-09，详见下方系数表注释与 tests/test_perf_calibration.py）：
  离心 — 后弯/前弯/径向已按 T4-72、9-19、9-26 选用表标定（残差≤5%）
  轴流 — 文献驼峰模型（未经实测标定）

输出:
  - PerfCurve 对象（数据点 + 摘要 + 变转速换算 at_speed()）
  - CSV 导出（Q, P, η, N）
  - SVG 图表导出（P-Q 与 η-Q 双曲线，标注设计点与失速区）

用法:
    from perf import perf_curve
    curve = perf_curve(design_result)
    print(curve.summary)
    curve.export_csv("fan_curve.csv")
    curve.export_svg("fan_curve.svg")
"""

import csv
import math
from dataclasses import dataclass, field
from typing import Union

from impeller.params import ImpellerDesignResult, BladeType
from axial.params import AxialFanResult


# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════


@dataclass
class PerfPoint:
    """性能曲线上的一个工况点"""
    Q: float          # 流量 m³/h
    P: float          # 全压 Pa
    eta: float        # 效率
    N: float          # 轴功率 kW

    def to_dict(self) -> dict:
        return {"Q": round(self.Q, 1), "P": round(self.P, 1),
                "eta": round(self.eta, 4), "N": round(self.N, 3)}


@dataclass
class PerfCurve:
    """整机性能曲线（固定转速 n）"""
    machine: str                # "centrifugal" | "axial"
    n: float                    # 转速 r/min
    Q_d: float                  # 设计流量 m³/h
    P_d: float                  # 设计全压 Pa
    eta_d: float                # 设计效率
    N_d: float                  # 设计轴功率 kW
    points: list[PerfPoint] = field(default_factory=list)
    Q_stall: float = 0.0        # 失速/喘振边界流量 m³/h（0=未定义）

    @property
    def machine_name(self) -> str:
        return "离心风机" if self.machine == "centrifugal" else "轴流风机"

    @property
    def stability_margin(self) -> float:
        """稳定裕度（设计流量距失速边界的距离）"""
        if self.Q_stall <= 0 or self.Q_d <= 0:
            return 0.0
        return (self.Q_d - self.Q_stall) / self.Q_d

    @property
    def eta_peak(self) -> float:
        return max((p.eta for p in self.points), default=0.0)

    @property
    def summary(self) -> str:
        lines = [
            f"{'='*55}",
            f"  性能曲线（{self.machine_name} @ {self.n:.0f} r/min）",
            f"  设计点: Q={self.Q_d:.0f} m³/h  P={self.P_d:.0f} Pa  η={self.eta_d:.1%}",
            f"{'='*55}",
            f"",
            f"  {'流量Q':>8} {'全压P':>8} {'效率η':>8} {'轴功率N':>8} {'工况':>6}",
            f"  {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*6}",
        ]
        for p in self.points:
            x = p.Q / self.Q_d if self.Q_d > 0 else 0
            if self.Q_stall > 0 and x < self.Q_stall / self.Q_d:
                state = "失速区"
            elif abs(x - 1.0) < 0.03:
                state = "★设计"
            elif x > 1.15:
                state = "超载"
            else:
                state = ""
            lines.append(
                f"  {p.Q:>8.0f} {p.P:>8.0f} {p.eta:>8.1%} {p.N:>8.2f} {state:>6}")
        lines.append(f"")
        lines.append(f"  峰值效率      η_max = {self.eta_peak:.1%}")
        if self.Q_stall > 0:
            lines.append(
                f"  失速边界      Q_stall ≈ {self.Q_stall:.0f} m³/h"
                f"（{self.Q_stall/self.Q_d:.0%}·Q_d），稳定裕度 {self.stability_margin:.0%}")
        lines.append(f"")
        lines.append(f"  💡  变转速换算（相似律）: Q∝n, P∝n², N∝n³")
        return "\n".join(lines)

    def at_speed(self, n2: float) -> "PerfCurve":
        """
        相似换算到另一转速（几何不变）

        Q₂ = Q·(n₂/n), P₂ = P·(n₂/n)², N₂ = N·(n₂/n)³, η 不变
        """
        if n2 <= 0:
            raise ValueError(f"转速必须为正: {n2}")
        k = n2 / self.n
        pts = [
            PerfPoint(Q=p.Q * k, P=p.P * k * k, eta=p.eta, N=p.N * k**3)
            for p in self.points
        ]
        return PerfCurve(
            machine=self.machine, n=n2,
            Q_d=self.Q_d * k, P_d=self.P_d * k * k,
            eta_d=self.eta_d, N_d=self.N_d * k**3,
            points=pts, Q_stall=self.Q_stall * k,
        )

    def export_csv(self, path: str):
        """导出性能曲线 CSV"""
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Q_m3h", "P_Pa", "eta", "N_shaft_kW"])
            for p in self.points:
                w.writerow([round(p.Q, 1), round(p.P, 1),
                            round(p.eta, 4), round(p.N, 3)])

    def export_svg(self, path: str):
        """导出性能曲线 SVG（P-Q + η-Q 双曲线图）"""
        svg = self._render_svg()
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)

    # ── SVG 渲染 ──

    def _render_svg(self) -> str:
        W, H = 900, 560
        ml, mr, mt, mb = 80, 80, 56, 64
        pw, ph = W - ml - mr, H - mt - mb

        Qmax = max(p.Q for p in self.points) * 1.03 if self.points else 1.0
        Pmax = max(p.P for p in self.points) * 1.10 if self.points else 1.0

        def X(q): return ml + q / Qmax * pw
        def YP(p_val): return mt + ph - p_val / Pmax * ph
        def YE(e): return mt + ph - e * ph  # η ∈ [0,1] 满量程

        def fmt(v): return f"{v:.0f}"

        parts = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'font-family="Segoe UI, Microsoft YaHei, sans-serif">')
        parts.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

        # 失速区阴影
        if self.Q_stall > 0 and self.points:
            x_s = X(self.Q_stall)
            parts.append(
                f'<rect x="{ml}" y="{mt}" width="{x_s-ml:.1f}" height="{ph}" '
                f'fill="#fdecea"/>')
            parts.append(
                f'<text x="{(ml+x_s)/2:.0f}" y="{mt+18}" font-size="12" '
                f'fill="#c0392b" text-anchor="middle">失速区</text>')
            parts.append(
                f'<line x1="{x_s:.1f}" y1="{mt}" x2="{x_s:.1f}" y2="{mt+ph}" '
                f'stroke="#e74c3c" stroke-width="1" stroke-dasharray="5,4"/>')

        # 网格 + 坐标
        for i in range(6):
            y = mt + ph - i * ph / 5
            parts.append(
                f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" '
                f'stroke="#e8e8e8" stroke-width="1"/>')
            parts.append(
                f'<text x="{ml-10}" y="{y+4:.1f}" font-size="12" fill="#555" '
                f'text-anchor="end">{fmt(Pmax*i/5)}</text>')
            parts.append(
                f'<text x="{ml+pw+10}" y="{y+4:.1f}" font-size="12" fill="#555" '
                f'text-anchor="start">{i*20}%</text>')

        for i in range(6):
            x = ml + i * pw / 5
            parts.append(
                f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}" '
                f'stroke="#f0f0f0" stroke-width="1"/>')
            parts.append(
                f'<text x="{x:.1f}" y="{mt+ph+22}" font-size="12" fill="#555" '
                f'text-anchor="middle">{fmt(Qmax*i/5)}</text>')

        # 坐标轴
        parts.append(
            f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#333" stroke-width="1.5"/>')
        parts.append(
            f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#333" stroke-width="1.5"/>')
        parts.append(
            f'<line x1="{ml+pw}" y1="{mt}" x2="{ml+pw}" y2="{mt+ph}" stroke="#333" stroke-width="1.5"/>')

        # 轴标签
        parts.append(
            f'<text x="{ml-52}" y="{mt+ph/2:.0f}" font-size="13" fill="#333" '
            f'transform="rotate(-90 {ml-52} {mt+ph/2:.0f})">全压 P (Pa)</text>')
        parts.append(
            f'<text x="{ml+pw+40}" y="{mt+ph/2:.0f}" font-size="13" fill="#333" '
            f'transform="rotate(90 {ml+pw+40} {mt+ph/2:.0f})">效率 η</text>')
        parts.append(
            f'<text x="{ml+pw/2:.0f}" y="{H-18}" font-size="13" fill="#333" '
            f'text-anchor="middle">流量 Q (m³/h)</text>')
        parts.append(
            f'<text x="{W/2:.0f}" y="{mt-22}" font-size="16" fill="#222" '
            f'text-anchor="middle" font-weight="600">'
            f'{self.machine_name}性能曲线 @ {self.n:.0f} r/min</text>')

        if self.points:
            # P-Q 曲线（蓝）
            pts_p = " ".join(f"{X(p.Q):.1f},{YP(p.P):.1f}" for p in self.points)
            parts.append(
                f'<polyline points="{pts_p}" fill="none" stroke="#1f6fb5" '
                f'stroke-width="2.5"/>')
            # η-Q 曲线（绿）
            pts_e = " ".join(f"{X(p.Q):.1f},{YE(p.eta):.1f}" for p in self.points)
            parts.append(
                f'<polyline points="{pts_e}" fill="none" stroke="#2e9e5b" '
                f'stroke-width="2.5" stroke-dasharray="8,4"/>')

            # 设计点标注
            xd, yd = X(self.Q_d), YP(self.P_d)
            parts.append(
                f'<circle cx="{xd:.1f}" cy="{yd:.1f}" r="6" fill="#1f6fb5" '
                f'stroke="#fff" stroke-width="2"/>')
            parts.append(
                f'<text x="{xd+10:.1f}" y="{yd-10:.1f}" font-size="12" fill="#1f6fb5">'
                f'设计点 Q={self.Q_d:.0f}, P={self.P_d:.0f}</text>')

            # 图例
            lx, ly = ml + 16, mt + 30
            parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+34}" y2="{ly}" '
                         f'stroke="#1f6fb5" stroke-width="2.5"/>')
            parts.append(f'<text x="{lx+42}" y="{ly+4}" font-size="13" fill="#333">P-Q 全压曲线</text>')
            parts.append(f'<line x1="{lx}" y1="{ly+24}" x2="{lx+34}" y2="{ly+24}" '
                         f'stroke="#2e9e5b" stroke-width="2.5" stroke-dasharray="8,4"/>')
            parts.append(f'<text x="{lx+42}" y="{ly+28}" font-size="13" fill="#333">η-Q 效率曲线</text>')

        parts.append('</svg>')
        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# 曲线形状（无量纲归一化）— 2026-09 按真实系列选用表标定
# ═══════════════════════════════════════════════════════════════
#
# 标定基准（x = Q/Q_d，Q_d = 系列表中 η_max 工况）：
#   后弯/机翼   T4-72 No.4A/4.5A/5A @2900 r/min，8 点，x∈[0.66, 1.26]
#   前弯        9-19  No.4A/4.5A    @2900 r/min，7 点，x∈[0.65, 1.35]
#   径向(斜前)  9-26  No.4A         @2900 r/min，7 点，x∈[0.73, 1.27]
#   轴流        T35-11 型谱 + 文献驼峰形（未经实测标定）
#
# 压力曲线: ψ/ψ_d = a − (a−1)·x^p （最小二乘拟合，全表点等权）
# 效率曲线: η/η_d = 1 − k·(1−x)²  （失速侧 k_lo / 超载侧 k_hi）
# 拟合残差: T4-72 |Δψ|≤0.8%、|Δη|≤0.7%；9-26 |Δψ|≤0.6%；
#           9-19 |Δψ|≤4.7%（首点，驼峰形致单调模型偏差）、|Δη|≤0.7%
# 验证: tests/test_perf_calibration.py

_PSI_COEFFS = {
    # blade_type.value: (a, p)
    "backward":   (1.19, 4.0),   # T4-72 实测拟合
    "airfoil":    (1.19, 4.0),   # 同后弯（G4-73 类）
    "radial":     (1.16, 3.0),   # 9-26 实测拟合
    "radial_tip": (1.16, 3.0),
    "forward":    (1.06, 3.0),   # 9-19 实测拟合（前弯曲线平缓是其特征）
}

_ETA_COEFFS = {
    # blade_type.value: (k_lo, k_hi)
    "backward":   (0.90, 1.50),  # T4-72: 失速侧平缓，超载侧较陡
    "airfoil":    (0.90, 1.50),
    "radial":     (0.78, 1.05),  # 9-26 无公开效率表，前后弯插值估计
    "radial_tip": (0.78, 1.05),
    "forward":    (0.65, 0.70),  # 9-19: 表内 η 全程平坦（±8%）
}

_X_STALL = {
    # 失速边界 ≈ 系列表流量下限（表内不存在更小流量即失速区）
    "backward":   0.60,   # T4-72 表下限 0.66
    "airfoil":    0.60,
    "radial":     0.72,   # 9-26 表下限 0.73
    "radial_tip": 0.72,
    "forward":    0.62,   # 9-19 表下限 0.65
}

AXIAL_STALL_X = 0.66   # 轴流失速边界 x_s = Q_stall/Q_d（T35 型谱及文献）


def _blade_key(blade_type) -> str:
    if isinstance(blade_type, BladeType):
        return blade_type.value
    return str(blade_type)


def _psi_shape_centrifugal(blade_type: BladeType, x: float) -> float:
    """
    离心风机无量纲压力曲线 ψ/ψ_d = a − (a−1)·x^p

    系数按 T4-72（后弯）/ 9-19（前弯）/ 9-26（径向）选用表最小二乘标定。
    前弯曲线明显平缓于后弯 —— 这是前向叶轮的固有特征。
    """
    a, p = _PSI_COEFFS.get(_blade_key(blade_type), (1.19, 4.0))
    return a - (a - 1.0) * x ** p


def _psi_shape_axial(x: float) -> float:
    """
    轴流风机无量纲压力曲线 — 驼峰形 + 失速鞍形（文献模型，未标定）

      x ≥ x_s（稳定段）: x≤1 时 ψ_r = 1+0.354(1−x²)，失速边界处峰值≈1.20；
                        x>1 时陡降（轴流右侧曲线显著陡于离心）
      x < x_s（失速后）: 跌落至鞍底≈0.86 后向关死点≈1.12 缓升（马鞍形）
    """
    x_s = AXIAL_STALL_X
    if x < x_s:
        return 0.86 + 0.26 * (1.0 - x / x_s) ** 2
    if x <= 1.0:
        return 1.0 + 0.354 * (1.0 - x * x)
    dx = x - 1.0
    return 1.0 - 0.80 * dx - 1.50 * dx * dx


def _eta_ratio(machine: str, blade_type, x: float) -> float:
    """
    无量纲效率曲线 η/η_d = f(x)

    设计点为峰值。离心按系列表标定；轴流为文献模型（窄高效区），
    失速后效率坍缩（最低至 0.25·η_d）。
    """
    if machine == "axial":
        x_s = AXIAL_STALL_X
        if x < x_s:
            return max(0.25, 1.0 - 3.5 * (x_s - x))
        k_lo, k_hi = 2.0, 2.4
    else:
        k_lo, k_hi = _ETA_COEFFS.get(_blade_key(blade_type), (0.9, 1.5))
    if x < 1.0:
        r = 1.0 - k_lo * (1.0 - x) ** 2
    else:
        r = 1.0 - k_hi * (x - 1.0) ** 2
    return max(0.05, min(r, 1.05))


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════


def centrifugal_perf_curve(
    design: ImpellerDesignResult,
    x_range: tuple = (0.30, 1.35),
    n_points: int = 22,
) -> PerfCurve:
    """从离心叶轮设计结果生成整机性能曲线"""
    inp = design.input_params
    n = inp.n
    Q_d, P_d, eta_d = inp.Q, inp.P, design.eta
    N_d = Q_d / 3600.0 * P_d / (1000.0 * eta_d)

    x_stall = _X_STALL.get(design.blade_type.value, 0.60)

    pts = []
    for i in range(n_points):
        x = x_range[0] + (x_range[1] - x_range[0]) * i / (n_points - 1)
        psi_r = _psi_shape_centrifugal(design.blade_type, x)
        eta = eta_d * _eta_ratio("centrifugal", design.blade_type, x)
        Q = Q_d * x
        P = P_d * psi_r
        N = Q / 3600.0 * P / (1000.0 * eta)
        pts.append(PerfPoint(Q=Q, P=P, eta=eta, N=N))

    return PerfCurve(
        machine="centrifugal", n=n, Q_d=Q_d, P_d=P_d, eta_d=eta_d,
        N_d=N_d, points=pts, Q_stall=Q_d * x_stall,
    )


def axial_perf_curve(
    design: AxialFanResult,
    x_range: tuple = (0.40, 1.30),
    n_points: int = 22,
) -> PerfCurve:
    """从轴流风机设计结果生成整机性能曲线"""
    inp = design.input_params
    n = inp.n
    Q_d, P_d, eta_d = inp.Q, inp.P, design.eta
    N_d = Q_d / 3600.0 * P_d / (1000.0 * eta_d)

    pts = []
    for i in range(n_points):
        x = x_range[0] + (x_range[1] - x_range[0]) * i / (n_points - 1)
        psi_r = _psi_shape_axial(x)
        eta = eta_d * _eta_ratio("axial", None, x)
        Q = Q_d * x
        P = P_d * psi_r
        N = Q / 3600.0 * P / (1000.0 * eta)
        pts.append(PerfPoint(Q=Q, P=P, eta=eta, N=N))

    return PerfCurve(
        machine="axial", n=n, Q_d=Q_d, P_d=P_d, eta_d=eta_d,
        N_d=N_d, points=pts, Q_stall=Q_d * AXIAL_STALL_X,
    )


def perf_curve(
    design: Union[ImpellerDesignResult, AxialFanResult],
) -> PerfCurve:
    """自动判别机型并生成性能曲线"""
    if isinstance(design, ImpellerDesignResult):
        return centrifugal_perf_curve(design)
    if isinstance(design, AxialFanResult):
        return axial_perf_curve(design)
    raise TypeError(f"不支持的设计结果类型: {type(design).__name__}")


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    os.makedirs("outputs", exist_ok=True)

    from impeller.design import design_impeller
    from impeller.params import ImpellerDesignInput
    from axial.design import design_axial_fan
    from axial.params import AxialFanInput

    print("── 离心风机性能曲线 ──")
    d = design_impeller(ImpellerDesignInput(Q=5000, P=2500, n=2900))
    c = perf_curve(d)
    print(c.summary)
    c.export_csv("outputs/centrifugal_curve.csv")
    c.export_svg("outputs/centrifugal_curve.svg")

    # 变转速换算验证
    c2 = c.at_speed(1450)
    print(f"相似换算至 1450 r/min: Q={c2.Q_d:.0f} m³/h, P={c2.P_d:.0f} Pa, "
          f"N={c2.N_d:.2f} kW（Q∝n P∝n² N∝n³）")

    print()
    print("── 轴流风机性能曲线 ──")
    d2 = design_axial_fan(AxialFanInput(Q=50000, P=300, n=730))
    c3 = perf_curve(d2)
    print(c3.summary)
    c3.export_csv("outputs/axial_curve.csv")
    c3.export_svg("outputs/axial_curve.svg")
