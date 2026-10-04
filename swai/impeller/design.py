"""
离心风机叶轮设计计算引擎

输入 Q, P, n → 输出全部设计参数

方法来源：《通风机设计手册》（商景泰主编）《离心式通风机》（成心德）
经验数据：工业风机设计通用惯例

所有单位：mm, °, m/s, Pa, kW, r/min
"""

import math
from typing import Optional

from .params import (
    ImpellerDesignInput, ImpellerDesignResult,
    BladeType, DriveType,
)


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════


def _clamp(val: float, lo: float, hi: float) -> float:
    """限制在区间内"""
    return max(lo, min(hi, val))


def _round_step(val: float, step: float) -> float:
    """按步长取整"""
    return round(val / step) * step


# ═══════════════════════════════════════════════════════════════
# 设计计算引擎
# ═══════════════════════════════════════════════════════════════


def design_impeller(inp: ImpellerDesignInput) -> ImpellerDesignResult:
    """
    离心风机叶轮设计 — 主入口

    11步完整流程：
    1. 比转速定型
    2. 压力系数 + 叶轮外径
    3. 轮径比 + 进口直径
    4. 速度参数
    5. 叶片宽度
    6. 叶片角
    7. 叶片数
    8. 功率估算
    9. 叶片厚度
    10. 强度校核（初步）
    11. 结果汇总

    Args:
        inp: 设计输入

    Returns:
        ImpellerDesignResult
    """
    r = ImpellerDesignResult(input_params=inp)

    # ── 单位换算 ──
    Q_s = inp.Q / 3600.0         # m³/h → m³/s
    P_mmH2O = inp.P / 9.80665    # Pa → mmH₂O
    omega = inp.n * math.pi / 30.0  # r/min → rad/s

    # ═══════════════════════════════════════════════════════════
    # Step 1: 比转速 n_s — 最重要的定型参数
    # 公式: n_s = n · √Q / P_y^(3/4)
    # 式中 Q: m³/s, P_y: mmH₂O
    # ═══════════════════════════════════════════════════════════

    if P_mmH2O <= 0 or Q_s <= 0:
        raise ValueError(f"流量和全压必须为正: Q={inp.Q}m³/h, P={inp.P}Pa")

    ns = inp.n * math.sqrt(Q_s) / (P_mmH2O ** 0.75)
    r.ns = ns

    # 根据比转速确认/修正叶型
    r.blade_type = _select_blade_type(ns, inp.blade_type)
    r.notes.append(f"比转速 n_s={ns:.1f} → {r.blade_type.value} 叶型")

    # ═══════════════════════════════════════════════════════════
    # Step 2: 压力系数 ψ + 叶轮外径 D₂
    # ψ 根据叶型 + 比转速经验取值
    # D₂ = 60/πn · √(2P/ρψ)
    # ═══════════════════════════════════════════════════════════

    psi = _pressure_coefficient(r.blade_type, ns)
    r.psi = psi

    # 出口圆周速度
    u2 = math.sqrt(2.0 * inp.P / (inp.rho * psi))
    r.u2 = u2

    # 叶轮外径
    D2 = 60.0 * u2 / (math.pi * inp.n) * 1000.0  # m → mm
    D2 = _clamp(D2, 100, 5000)

    # 如果有最大外径限制
    if inp.max_diameter > 0 and D2 > inp.max_diameter:
        D2 = inp.max_diameter
        r.warnings.append(f"外径受限制，D₂ 从 {D2:.0f} 截断至 {inp.max_diameter}mm")
        # 需要重算圆周速度
        u2 = math.pi * inp.n * D2 / 60000.0
        r.u2 = u2

    r.D2 = _round_step(D2, 5)  # 按 5mm 取整

    # ═══════════════════════════════════════════════════════════
    # Step 3: 轮径比 ν + 进口直径 D₁
    # ν = D₁/D₂，根据 n_s 经验回归
    # ═══════════════════════════════════════════════════════════

    nu = _hub_ratio(ns, r.blade_type)
    r.nu = nu
    r.D1 = _round_step(r.D2 * nu, 5)

    # 轮毂直径（悬臂结构）
    r.dh = _round_step(0.25 * r.D1, 2)

    # 集流器进口直径
    r.D0 = _round_step(r.D1 * 0.95, 5)

    # ═══════════════════════════════════════════════════════════
    # Step 4: 速度参数
    # u₁, c₀, c₂r
    # ═══════════════════════════════════════════════════════════

    # 进口圆周速度
    r.u1 = math.pi * inp.n * r.D1 / 60000.0  # mm/min → m/s

    # 进口流速（考虑轮毂和进口阻塞）
    A0 = math.pi / 4.0 * (r.D1**2 - r.dh**2) / 1e6  # m² (mm²→m²)
    tau1 = _inlet_block_coeff(r.blade_type)  # 阻塞系数
    r.c0 = Q_s / (A0 * tau1)
    r.notes.append(f"进口阻塞系数 τ₁={tau1:.2f}")

    # 出口径向速度
    phi = _flow_coefficient(r.blade_type, r.beta2 if r.beta2 > 0 else 45)
    r.phi = phi
    r.c2r = r.u2 * phi

    # ═══════════════════════════════════════════════════════════
    # Step 5: 叶片宽度 b₁, b₂
    # ═══════════════════════════════════════════════════════════

    A1 = math.pi * r.D1 / 1000.0  # 进口圆周单位宽度面积 m²/m
    b1_raw = Q_s / (A1 * r.c0 * tau1) * 1000.0  # m → mm
    r.b1 = _round_step(_clamp(b1_raw, 20, 500), 2)

    # 出口宽度 = 进口宽度 × 宽度比
    b2_ratio = _width_ratio(r.blade_type, ns)
    r.b2 = _round_step(r.b1 * b2_ratio, 2)

    # ═══════════════════════════════════════════════════════════
    # Step 6: 叶片角 β₁, β₂
    # ═══════════════════════════════════════════════════════════

    # 进口角：无冲击进气条件 + 冲角
    beta1_opt = math.degrees(math.atan(r.c0 / r.u1)) if r.u1 > 0 else 30.0
    attack_angle = _attack_angle(r.blade_type)
    r.beta1 = _clamp(beta1_opt + attack_angle, 12, 70)
    r.notes.append(f"进口冲角 i={attack_angle:.1f}°")

    # 出口角：由叶型决定
    r.beta2 = _exit_angle(r.blade_type, ns)

    # ═══════════════════════════════════════════════════════════
    # Step 7: 叶片数 Z (Pfleiderer 公式)
    # Z ≈ 8.5·sin(β₂) / (1 - ν)
    # ═══════════════════════════════════════════════════════════

    beta2_rad = math.radians(r.beta2)
    Z_raw = 8.5 * math.sin(beta2_rad) / (1.0 - nu)
    r.Z = _clamp(round(Z_raw), 6, 32)
    r.notes.append(f"Pfleiderer 公式计算叶片数 Z={Z_raw:.1f} → 取 Z={r.Z}")

    # ═══════════════════════════════════════════════════════════
    # Step 7.5: 设计闭环验证（欧拉方程 + Stodola 滑移 + DeHaller）
    #
    # 完整出口速度三角形（β₂ 从切向测量）：
    #   c₂u = u₂ − c₂r·cot(β₂)                （无限叶片数理论值）
    #   Stodola 滑移（有限叶片数）: Δc₂u = (π/Z)·sin(β₂)·u₂
    #   c₂u' = μ·u₂ − c₂r·cot(β₂)，μ = 1−(π/Z)sin(β₂)
    #   欧拉理论全压: P_th = ρ·u₂·c₂u'
    #   几何压力系数: ψ_geo = 2·c₂u'/u₂
    #
    # 闭环判据: η·ψ_geo vs 定型用的经验 ψ，偏差 ±20% 内为工程可接受；
    # 定型尺寸仍以实测校准的经验 ψ 为准（闭环含未建模损失，系统性偏高）。
    # ═══════════════════════════════════════════════════════════

    eta = _efficiency_estimate(r.blade_type, ns)
    r.eta = eta

    r.c1u = 0.0  # 无预旋设计
    r.c2u = r.u2 - r.c2r * (math.cos(beta2_rad) / math.sin(beta2_rad))
    r.slip_mu = 1.0 - (math.pi / r.Z) * math.sin(beta2_rad)
    r.c2u_slip = r.slip_mu * r.u2 - r.c2r * (math.cos(beta2_rad) / math.sin(beta2_rad))
    r.c2 = math.sqrt(r.c2u_slip**2 + r.c2r**2)

    r.P_th = inp.rho * r.u2 * r.c2u_slip
    r.psi_geo = 2.0 * r.c2u_slip / r.u2 if r.u2 > 0 else 0.0
    r.psi_dev = (r.eta * r.psi_geo - r.psi) / r.psi if r.psi > 0 else 0.0

    # 进出口相对速度 → DeHaller 扩散因子（防叶道分离）
    r.w1 = math.sqrt(r.u1**2 + r.c0**2)  # c₁ ≈ c₀（无预旋）
    r.w2 = math.sqrt(abs(r.u2 - r.c2u_slip) ** 2 + r.c2r**2)
    r.dehaller = r.w2 / r.w1 if r.w1 > 0 else 0.0

    if r.P_th > 0 and r.psi > 0:
        if abs(r.psi_dev) <= 0.20:
            r.notes.append(
                f"欧拉闭环: P_th={r.P_th:.0f}Pa, 偏差{r.psi_dev:+.1%}（±20%内，可接受）")
        elif abs(r.psi_dev) <= 0.35:
            r.warnings.append(
                f"欧拉闭环偏差{r.psi_dev:+.1%}（>±20%），建议 D₂ 或 β₂/Z 复核")
        else:
            r.warnings.append(
                f"欧拉闭环偏差{r.psi_dev:+.1%}（>±35%），叶型参数 β₂/Z/φ 需复核")

    if r.blade_type in (BladeType.BACKWARD, BladeType.AIRFOIL) and 0 < r.dehaller < 0.55:
        r.warnings.append(
            f"DeHaller 数 w₂/w₁={r.dehaller:.2f} < 0.55，叶道扩散过度，叶片易分离")

    # ═══════════════════════════════════════════════════════════
    # Step 8: 功率估算
    # ═══════════════════════════════════════════════════════════

    # N_shaft = Q·P / (1000·η)
    N_shaft = Q_s * inp.P / (1000.0 * eta)
    r.N_shaft = round(N_shaft, 2)

    # 电机功率：加 15% 裕量
    r.N_motor = round(N_shaft * 1.15, 1)

    # ═══════════════════════════════════════════════════════════
    # Step 9: 叶片厚度（初步估算）
    # ═══════════════════════════════════════════════════════════

    r.delta = _blade_thickness(r.blade_type, r.D2, inp.material)

    # ═══════════════════════════════════════════════════════════
    # Step 10: 强度校核（初步 — 离心应力）
    # σ_r ≈ ρ_m · u₂² / 3（旋转圆盘径向应力近似）
    # σ_t ≈ ρ_m · u₂²（旋转圆盘切向应力近似）
    # ═══════════════════════════════════════════════════════════

    rho_material = _material_density(inp.material)
    u2_ms = r.u2

    # 切向应力（最大主应力）
    r.sigma_t = rho_material * u2_ms**2 / 1e6  # Pa → MPa
    # 径向应力（轮盘中部）
    r.sigma_r = rho_material * u2_ms**2 / 3e6

    sigma_yield = _yield_strength(inp.material)
    if sigma_yield > 0:
        r.safety_factor = sigma_yield / max(r.sigma_t, 0.1)

    if r.safety_factor < 2.0 and r.safety_factor > 0:
        r.warnings.append(f"安全系数 {r.safety_factor:.1f} < 2.0，需加厚轮盘或换材料")
    elif r.safety_factor > 5.0:
        r.notes.append(f"安全系数 {r.safety_factor:.1f}，有减重空间")

    # ═══════════════════════════════════════════════════════════
    # Step 11: 汇总验证
    # ═══════════════════════════════════════════════════════════

    # 合理性检查
    _validate_design(r)

    return r


# ═══════════════════════════════════════════════════════════════
# 经验函数（可独立调用的设计子模块）
# ═══════════════════════════════════════════════════════════════


def _select_blade_type(ns: float, preferred: BladeType) -> BladeType:
    """
    根据比转速推荐叶型

    参考范围：
      n_s < 25     → 前向
      25 ≤ n_s < 55 → 径向或前向（看偏好）
      55 ≤ n_s < 85 → 后向（最常用区间）
      n_s ≥ 85     → 双吸入或轴流

    如果用户指定的叶型在合理范围内，保留用户选择。
    """
    # 后向叶轮适用区间最广
    preferred_ok = {
        BladeType.BACKWARD: (30, 100),
        BladeType.FORWARD: (10, 55),
        BladeType.RADIAL: (15, 65),
        BladeType.RADIAL_TIP: (20, 70),
        BladeType.AIRFOIL: (50, 90),
    }
    lo, hi = preferred_ok.get(preferred, (0, 200))
    if lo <= ns <= hi:
        return preferred

    # 自动推荐
    if ns < 25:
        return BladeType.FORWARD
    elif ns < 55:
        return BladeType.RADIAL
    elif ns < 90:
        return BladeType.BACKWARD
    else:
        return BladeType.BACKWARD  # 超过 90 建议双吸入或轴流


def _pressure_coefficient(blade_type: BladeType, ns: float) -> float:
    """
    压力系数 ψ = 2P/(ρ·u₂²)（Eck 约定）

    按真实工业风机校准（2026-08 复核）：
      4-72（后向机翼）: 8D@960rpm 实测 P=887Pa, u₂=40.2 → ψ=0.915
                        10D@1450 实测 P=2532~3202Pa, u₂=75.9 → ψ=0.73~0.93
      9-19（前向高压）: ψ ≈ 1.7~1.8
    中国风机型号命名首位数字 ≈ 10·P/(ρu₂²)，据此换算为本约定（×2）。

    后向叶轮有 n_s 回归修正：ψ ≈ 0.85 - 0.002·(n_s - 55)
    """
    base = {
        BladeType.BACKWARD: 0.85,
        BladeType.FORWARD: 1.75,
        BladeType.RADIAL: 1.15,
        BladeType.RADIAL_TIP: 1.05,
        BladeType.AIRFOIL: 0.88,
    }.get(blade_type, 0.85)

    # 后向叶轮用 n_s 修偏（低比转速 → 高压力系数）
    if blade_type in (BladeType.BACKWARD, BladeType.AIRFOIL) and 20 < ns < 110:
        adj = base - 0.002 * (ns - 55)
        return round(_clamp(adj, 0.65, 1.10), 3)

    return round(_clamp(base, 0.60, 2.00), 3)


def _flow_coefficient(blade_type: BladeType, beta2: float) -> float:
    """
    流量系数 φ = c₂r / u₂

    基于出口角和叶型的经验公式。
    """
    b2_rad = math.radians(beta2)

    if blade_type == BladeType.FORWARD:
        # 前向叶轮 φ 较小
        base = 0.18
    elif blade_type == BladeType.RADIAL:
        base = 0.20
    elif blade_type == BladeType.AIRFOIL:
        base = 0.14
    else:
        # 后向: φ = 0.15 ~ 0.35，出口角越大流量越大
        base = 0.12 + 0.004 * (beta2 - 20)

    return round(_clamp(base, 0.08, 0.40), 3)


def _hub_ratio(ns: float, blade_type: BladeType) -> float:
    """
    轮径比 ν = D₁/D₂

    经验公式（回归自风机设计数据）：
      ν = 0.535 + 0.0028·(100 - n_s)
    适用 n_s = 10~100，超出范围则截断。
    """
    if blade_type == BladeType.FORWARD:
        # 前向叶轮轮径比较大
        raw = 0.62 + 0.0015 * (50 - ns)
    elif blade_type == BladeType.RADIAL:
        raw = 0.44 + 0.0035 * (60 - ns)
    else:
        # 后向（最常用）：ν ≈ 0.47~0.72 对应 ns=30~90
        # ν = 0.45 + 0.003·ns 适用于 ns≥30
        raw = 0.45 + 0.0030 * ns

    return round(_clamp(raw, 0.30, 0.80), 3)


def _inlet_block_coeff(blade_type: BladeType) -> float:
    """
    进口阻塞系数 τ₁
    
    考虑叶片厚度对进口面积的阻塞效应。
    """
    return {
        BladeType.FORWARD: 0.88,
        BladeType.RADIAL: 0.90,
        BladeType.RADIAL_TIP: 0.92,
        BladeType.BACKWARD: 0.92,
        BladeType.AIRFOIL: 0.95,
    }.get(blade_type, 0.90)


def _attack_angle(blade_type: BladeType) -> float:
    """
    进口冲角 i (°)

    为了改善大流量工况的进气条件，通常在最佳进气角上加冲角。
    """
    return {
        BladeType.FORWARD: 5.0,
        BladeType.RADIAL: 4.0,
        BladeType.RADIAL_TIP: 3.0,
        BladeType.BACKWARD: 4.0,
        BladeType.AIRFOIL: 3.0,
    }.get(blade_type, 4.0)


def _exit_angle(blade_type: BladeType, ns: float) -> float:
    """
    叶片出口角 β₂ (°)
    
    由叶型决定，但后向叶轮的出口角可随 n_s 微调。
    """
    angles = {
        BladeType.FORWARD: (120.0, 170.0, 150.0),
        BladeType.RADIAL: (90.0, 90.0, 90.0),
        BladeType.RADIAL_TIP: (30.0, 60.0, 45.0),
        BladeType.BACKWARD: (25.0, 55.0, 0.0),
        BladeType.AIRFOIL: (30.0, 50.0, 40.0),
    }
    lo, hi, fixed = angles.get(blade_type, (30, 50, 45))

    if fixed > 0:
        return fixed

    # 后向叶轮出口角与 n_s 相关
    # n_s 越大，出口角越大
    beta2 = 25.0 + 0.3 * (ns - 30)
    return round(_clamp(beta2, lo, hi), 1)


def _width_ratio(blade_type: BladeType, ns: float) -> float:
    """
    出口/进口宽度比 b₂/b₁
    
    后向叶轮通常出口变窄，前向叶轮出口变宽。
    """
    if blade_type == BladeType.FORWARD:
        base = 1.3
    elif blade_type == BladeType.RADIAL:
        base = 1.0
    else:
        # 后向叶轮：n_s 越大，b₂/b₁ 越大
        base = 0.50 + 0.005 * ns

    return round(_clamp(base, 0.30, 1.80), 2)


def _efficiency_estimate(blade_type: BladeType, ns: float) -> float:
    """
    效率估算 η

    基于叶型和比转速的经验估算。
    实际效率还取决于蜗壳匹配、制造精度等。
    """
    base = {
        BladeType.BACKWARD: 0.84,
        BladeType.FORWARD: 0.72,
        BladeType.RADIAL: 0.74,
        BladeType.RADIAL_TIP: 0.78,
        BladeType.AIRFOIL: 0.88,
    }.get(blade_type, 0.80)

    # n_s 修正：在最佳比转速区间效率最高
    if 55 <= ns <= 80:
        adj = 0.02
    elif 40 <= ns <= 90:
        adj = 0.01
    else:
        adj = -0.03

    return round(_clamp(base + adj, 0.50, 0.90), 3)


def _blade_thickness(blade_type: BladeType, D2: float, material: str) -> float:
    """
    叶片厚度 δ (mm)

    根据叶轮直径和材料的粗略估算。
    最终厚度应由强度计算确定。
    """
    # 碳钢
    base = 2.0 + 0.003 * D2
    # 不锈钢略薄（强度更高）
    if material.startswith(("304", "316", "1Cr")):
        base *= 0.85
    return round(_clamp(base, 1.0, 12.0), 1)


def _material_density(material: str) -> float:
    """材料密度 kg/m³"""
    if material in ("Q235B", "Q345", "20#", "45#"):
        return 7850.0
    elif material.startswith(("304", "316")):
        return 7930.0
    elif material.startswith(("2A", "7A", "5A")):
        return 2700.0
    return 7850.0


def _yield_strength(material: str) -> float:
    """材料屈服强度 MPa"""
    data = {
        "Q235B": 235,
        "Q345": 345,
        "20#": 245,
        "45#": 355,
        "304": 205,
        "316L": 170,
        "2A12": 280,
        "LY12": 280,
    }
    return data.get(material, 200)


def _validate_design(r: ImpellerDesignResult):
    """设计结果合理性检查"""
    w = r.warnings

    if r.b1 < 5:
        w.append(f"进口宽度 b₁={r.b1:.0f}mm 过窄")
    if r.b2 < 3:
        w.append(f"出口宽度 b₂={r.b2:.0f}mm 过窄")
    if r.eta < 0.55:
        w.append(f"估算效率 {r.eta:.1%} 偏低")
    if r.D2 / r.D1 > 3.5:
        w.append(f"D₂/D₁={r.D2/r.D1:.1f} 偏大，考虑双级方案")
    if r.ns > 95:
        w.append(f"比转速 n_s={r.ns:.1f} > 95，建议改用双吸入或轴流")


# ═══════════════════════════════════════════════════════════════
# 辅助计算函数（供外部调用）
# ═══════════════════════════════════════════════════════════════


def calc_ns(Q: float, P: float, n: float) -> float:
    """
    计算比转速（单独使用）

    Args:
        Q: 流量 m³/h
        P: 全压 Pa
        n: 转速 r/min

    Returns:
        比转速 n_s
    """
    return n * math.sqrt(Q / 3600.0) / ((P / 9.80665) ** 0.75)


def calc_u2(D2: float, n: float) -> float:
    """
    计算叶轮出口圆周速度

    Args:
        D2: 叶轮外径 mm
        n: 转速 r/min

    Returns:
        圆周速度 m/s
    """
    return math.pi * n * D2 / 60000.0


def recommend_speed(ns: float, D2: float, P: float) -> float:
    """
    推荐转速（用于初步选电机）

    给定比转速和叶轮外径，估算合适的转速。

    Args:
        ns: 目标比转速
        D2: 叶轮外径 mm
        P: 全压 Pa

    Returns:
        推荐转速 r/min
    """
    # 从 n_s 反推转速
    D2_m = D2 / 1000.0
    n_rev = 30.0 * math.sqrt(2 * P / 1.2 / 0.5) / (math.pi * D2_m)
    return round(n_rev)


if __name__ == "__main__":
    # 快速测试
    test_cases = [
        ImpellerDesignInput(Q=5000, P=2500, n=1450, blade_type=BladeType.BACKWARD),
        ImpellerDesignInput(Q=10000, P=3500, n=980, blade_type=BladeType.BACKWARD),
        ImpellerDesignInput(Q=2000, P=5000, n=2900, blade_type=BladeType.RADIAL),
        ImpellerDesignInput(Q=30000, P=2000, n=720, blade_type=BladeType.FORWARD),
    ]

    for i, inp in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"  测试案例 {i}: Q={inp.Q}m³/h  P={inp.P}Pa  n={inp.n}r/min")
        print(f"{'='*60}")
        try:
            result = design_impeller(inp)
            print(result.summary)
        except Exception as e:
            print(f"  ❌ 设计失败: {e}")
