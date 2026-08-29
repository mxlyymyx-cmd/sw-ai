"""
轴流风机设计计算引擎

输入 Q, P, n → 输出全部设计参数

方法来源：《通风机设计手册》（商景泰主编）《轴流式通风机实用技术》
《风机设计基础》（成心德）及空气动力学翼型理论

所有单位：mm, °, m/s, Pa, kW, r/min
"""

import math
from typing import Optional

from .params import (
    AxialFanInput, AxialFanResult, BladeSection,
    AirfoilType, CirculationType,
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


def design_axial_fan(inp: AxialFanInput) -> AxialFanResult:
    """
    轴流风机设计 — 主入口

    10步完整流程：
    1. 比转速定型 + 轮毂比确定
    2. 叶轮直径计算
    3. 叶片数确定
    4. 环量分布设计
    5. 各截面速度三角形
    6. 弦长和安装角计算
    7. 叶片扭角分布
    8. 性能预估
    9. 强度校核（初步）
    10. 结果汇总

    Args:
        inp: 设计输入

    Returns:
        AxialFanResult
    """
    r = AxialFanResult(input_params=inp)

    # ── 单位换算 ──
    Q_s = inp.Q / 3600.0           # m³/h → m³/s
    P_mmH2O = inp.P / 9.80665      # Pa → mmH₂O
    omega = inp.n * math.pi / 30.0 # r/min → rad/s

    if P_mmH2O <= 0 or Q_s <= 0:
        raise ValueError(f"流量和全压必须为正: Q={inp.Q}m³/h, P={inp.P}Pa")

    # ═══════════════════════════════════════════════════════════
    # Step 1: 比转速 n_s + 轮毂比 ν 确定
    #
    # 轴流风机比转速范围通常 ns = 100~300
    # 公式: n_s = n · √Q / P_y^(3/4)     （Q: m³/s, P_y: mmH₂O）
    # ═══════════════════════════════════════════════════════════

    ns = inp.n * math.sqrt(Q_s) / (P_mmH2O ** 0.75)
    r.ns = ns

    # 比直径 n_y — 辅助判断
    # n_y = D / (Q^0.5 / P^0.25) 的简化形式
    # 经验: n_y = 0.5 ~ 1.5 对应 ns = 100~300
    if ns > 0:
        r.n_y = 60.0 / ns * 100.0  # 粗略比直径

    # 轮毂比选择（根据 ns 经验公式）
    if inp.nu > 0:
        r.nu = inp.nu  # 用户指定
    else:
        r.nu = _hub_ratio_from_ns(ns)
    r.notes.append(f"比转速 n_s={ns:.1f} → 轮毂比 ν={r.nu:.3f}")

    # ═══════════════════════════════════════════════════════════
    # Step 2: 叶轮直径 D 计算
    #
    # 基于流量和轴向流速，先估算叶轮直径。
    #
    # 轴向流速 c_a 根据比转速选取：
    #   低 ns (100-150): c_a ≈ 10~20 m/s
    #   中 ns (150-250): c_a ≈ 20~35 m/s
    #   高 ns (250-300): c_a ≈ 30~50 m/s
    #
    # 环形面积 A = π/4 · (D² - d²) = π/4 · D² · (1 - ν²)
    # 流量 Q = A · c_a
    # → D = √(4·Q / (π·c_a·(1-ν²)))
    # ═══════════════════════════════════════════════════════════

    # 根据 ns 选取轴向流速
    c_a = _axial_velocity(ns)
    r.c_a = c_a

    nu = r.nu
    A_required = Q_s / c_a  # 所需环形面积 m²
    D_raw = math.sqrt(4.0 * A_required / (math.pi * (1.0 - nu**2)))
    D_m = D_raw * 1000.0  # m → mm

    if inp.D_override > 0:
        D_m = inp.D_override

    r.D = _round_step(D_m, 5)  # 按 5mm 取整
    r.R = r.D / 2.0
    r.d = r.D * nu
    r.r_hub = r.d / 2.0
    r.L = r.R - r.r_hub  # 叶高 mm

    # 重算轴向流速（基于实际直径）
    r.c_a = Q_s / (math.pi / 4.0 * ((r.D / 1000.0)**2 - (r.d / 1000.0)**2))

    # 叶尖圆周速度
    r.u_tip = omega * r.R / 1000.0  # rad/s * mm → m/s
    r.u_hub = omega * r.r_hub / 1000.0

    # 检查叶尖马赫数（轴流风机通常要求 Ma < 0.8）
    Ma_tip = r.u_tip / 340.0  # 声速约 340 m/s
    if Ma_tip > 0.7:
        r.warnings.append(f"叶尖马赫数 Ma={Ma_tip:.2f} > 0.7，需降速或加载消音")

    r.notes.append(f"轴向流速 c_a={r.c_a:.1f} m/s")
    r.notes.append(f"叶尖圆周速度 u_t={r.u_tip:.1f} m/s")

    # ═══════════════════════════════════════════════════════════
    # Step 3: 叶片数 Z 确定
    #
    # 叶片数经验公式（与轮毂比相关）：
    #   Z = 2π / (1.5~2.0) · (1 + ν) / (1 - ν)   （粗略估计）
    # 或者按轮毂比查表：
    #   ν = 0.3 → Z = 4~6
    #   ν = 0.4 → Z = 6~8
    #   ν = 0.5 → Z = 6~10
    #   ν = 0.6 → Z = 8~12
    #   ν = 0.7 → Z = 10~16
    # ═══════════════════════════════════════════════════════════

    if inp.Z > 0:
        r.Z = inp.Z
    else:
        r.Z = _blade_number(nu)

    r.notes.append(f"轮毂比 ν={nu:.3f} → 叶片数 Z={r.Z}")

    # ═══════════════════════════════════════════════════════════
    # Step 4: 环量分布设计
    #
    # 等环量（自由旋涡）：
    #   c_u · r = const  →  Γ = 2πr · c_u = const
    #   出口圆周分速 c_u2 = Γ / (2πr)
    #
    # 变环量：
    #   c_u · r^k = const  (k ≠ 1)
    #   偏轴处加载更大环量
    #
    # 平均环量由欧拉方程确定：
    #   P_theory = ρ · n · Γ_avg / 60
    #   Γ_avg = 60 · P_theory / (ρ · n)
    # ═══════════════════════════════════════════════════════════

    circ_type = inp.circulation
    r.circulation_type = circ_type

    # 欧拉方程估算理论全压（考虑损失）
    eta_est = _efficiency_estimate(ns, r.nu)
    r.eta = eta_est
    P_theory = inp.P / eta_est

    # 平均环量
    Gamma_avg = 60.0 * P_theory / (inp.rho * inp.n)
    r.notes.append(f"理论全压 P_th={P_theory:.0f}Pa, 平均环量 Γ_avg={Gamma_avg:.2f} m²/s")

    # ═══════════════════════════════════════════════════════════
    # Step 5~7: 各截面计算
    #
    # 沿叶高划分 N 个截面，每个截面计算：
    #   - 速度三角形
    #   - 弦长（基于翼型升力系数）
    #   - 安装角 / 扭角
    # ═══════════════════════════════════════════════════════════

    N = inp.sections
    c_a_actual = r.c_a

    sections = _compute_sections(
        r_hub=r.r_hub,
        R=r.R,
        N=N,
        nu=nu,
        omega=omega,
        c_a=c_a_actual,
        Gamma_avg=Gamma_avg,
        Z=r.Z,
        airfoil=inp.airfoil,
        circulation=circ_type,
    )
    r.sections = sections

    # ── 统计平均参数 ──
    beta1_sum = sum(s.beta1 for s in sections)
    beta2_sum = sum(s.beta2 for s in sections)
    c_sum = sum(s.c for s in sections)
    chi_sum = sum(s.chi for s in sections)
    N_s = len(sections)
    r.beta1_avg = beta1_sum / N_s
    r.beta2_avg = beta2_sum / N_s
    r.c_avg = c_sum / N_s
    r.chi_avg = chi_sum / N_s

    # 圆周分速平均值
    c_u2_sum = 0.0
    for s in sections:
        # 从速度三角形: c_u2 = u - c_a * cot(β₂)  (相对出口角的圆周分量)
        beta2_rad = math.radians(s.beta2)
        if abs(math.tan(beta2_rad)) > 1e-6:
            c_u2 = s.u - c_a_actual / math.tan(beta2_rad)
            c_u2_sum += c_u2
    r.c_u2_avg = c_u2_sum / N_s

    # ═══════════════════════════════════════════════════════════
    # Step 8: 性能预估
    #
    # 全压: 由欧拉方程验证
    # 效率: 已估算
    # 功率: N = Q · P / (1000 · η)
    # ═══════════════════════════════════════════════════════════

    # 轴功率
    r.N_shaft = round(Q_s * inp.P / (1000.0 * r.eta), 2)

    # 电机功率：加 15% 裕量
    r.N_motor = round(r.N_shaft * 1.15, 1)

    # ═══════════════════════════════════════════════════════════
    # Step 9: 叶顶间隙 + 集流器直径
    #
    # 叶顶间隙 δ = 0.5% ~ 1.5% · D
    # 集流器直径 Dc ≈ D + 2δ
    # ═══════════════════════════════════════════════════════════

    if inp.delta_clearance > 0:
        r.delta = inp.delta_clearance
    else:
        # 自动估算：δ = 0.5~1.5% D，直径越大比例越小
        delta_pct = _clamp(1.5 - 0.002 * r.D, 0.5, 1.5) / 100.0
        r.delta = round(r.D * delta_pct, 1)

    r.Dc = r.D + 2.0 * r.delta

    # ═══════════════════════════════════════════════════════════
    # Step 10: 强度校核（初步 — 离心应力
    #
    # 叶片根部离心应力：
    #   σ_max ≈ ρ_m · u_tip² · (1 - ν²) / 2
    # （简化：叶片根部截面离心应力）
    # ═══════════════════════════════════════════════════════════

    rho_material = _material_density(inp.material)
    u_tip = r.u_tip

    # 叶片根部离心拉应力（简化公式）
    r.sigma_max = rho_material * u_tip**2 * (1.0 - nu**2) / 2.0 / 1e6  # Pa → MPa

    sigma_yield = _yield_strength(inp.material)
    if sigma_yield > 0 and r.sigma_max > 0:
        r.safety_factor = sigma_yield / max(r.sigma_max, 0.1)

    if r.safety_factor < 2.0 and r.safety_factor > 0:
        r.warnings.append(f"安全系数 {r.safety_factor:.1f} < 2.0，需换材料或减小直径")
    elif r.safety_factor > 8.0:
        r.notes.append(f"安全系数 {r.safety_factor:.1f}，有减重/减厚空间")

    # ═══════════════════════════════════════════════════════════
    # Step 11: 汇总验证
    # ═══════════════════════════════════════════════════════════

    _validate_design(r)

    return r


# ═══════════════════════════════════════════════════════════════
# 经验函数（可独立调用的设计子模块）
# ═══════════════════════════════════════════════════════════════


def _hub_ratio_from_ns(ns: float) -> float:
    """
    根据比转速选择轮毂比 ν = d/D

    轴流风机经验数据（已标准化）：
      ns = 100~150 → ν = 0.25~0.35   （低压大流量，轮毂小）
      ns = 150~200 → ν = 0.35~0.50   （中压通用）
      ns = 200~250 → ν = 0.50~0.60   （中高压）
      ns = 250~300 → ν = 0.60~0.70   （高压小流量，轮毂大）

    回归公式：
      ν = 0.15 + 0.002 · ns          （拟合近似，适用 ns=100~300）
    """
    if ns < 60:
        return 0.25  # 接近离心风机，取最小轮毂比
    elif ns > 350:
        return 0.70  # 超高比转速，取最大轮毂比

    # 线性回归
    nu = 0.15 + 0.0018 * ns
    return round(_clamp(nu, 0.25, 0.70), 3)


def _axial_velocity(ns: float) -> float:
    """
    轴向流速估算 c_a (m/s)

    根据比转速选择。轴流风机轴向流速一般 10~50 m/s。
    """
    if ns < 100:
        base = 12.0   # 接近离心区，低速
    elif ns < 150:
        base = 15.0   # 低压大流量
    elif ns < 200:
        base = 22.0   # 中压通用
    elif ns < 250:
        base = 30.0   # 中高压
    else:
        base = 38.0   # 高压小流量

    return _clamp(base, 8.0, 50.0)


def _blade_number(nu: float) -> int:
    """
    根据轮毂比确定叶片数

    经验数据（工业轴流风机通用）：
      ν < 0.3  → 4 片
      ν = 0.3~0.4 → 6 片
      ν = 0.4~0.5 → 8 片
      ν = 0.5~0.6 → 10 片
      ν = 0.6~0.65 → 12 片
      ν = 0.65~0.70 → 14 片
      ν > 0.70 → 16 片
    """
    if nu < 0.30:
        return 4
    elif nu < 0.40:
        return 6
    elif nu < 0.50:
        return 8
    elif nu < 0.55:
        return 10
    elif nu < 0.60:
        return 10
    elif nu < 0.65:
        return 12
    elif nu < 0.70:
        return 14
    else:
        return 16


def _efficiency_estimate(ns: float, nu: float) -> float:
    """
    效率估算 η

    轴流风机典型效率范围 0.70~0.88。
    受比转速和轮毂比影响。
    """
    # 基准效率
    base = 0.80

    # ns 修偏：最佳效率在 ns=180~220
    if 170 <= ns <= 230:
        adj = 0.03
    elif 130 <= ns <= 270:
        adj = 0.01
    else:
        adj = -0.03

    # 轮毂比修正：过大过小的轮毂比效率降低
    if nu < 0.30:
        adj -= 0.02
    elif nu > 0.65:
        adj -= 0.02

    return round(_clamp(base + adj, 0.60, 0.90), 3)


def _compute_sections(
    r_hub: float,
    R: float,
    N: int,
    nu: float,
    omega: float,
    c_a: float,
    Gamma_avg: float,
    Z: int,
    airfoil: AirfoilType,
    circulation: CirculationType,
) -> list[BladeSection]:
    """
    沿径向计算各截面参数

    使用环量法（自由旋涡或变环量）确定各截面的
    速度三角形、弦长、安装角。

    每个截面一套独立的 BladeSection。

    Args:
        r_hub: 轮毂半径 mm
        R: 叶轮半径 mm
        N: 截面数
        nu: 轮毂比
        omega: 角速度 rad/s
        c_a: 轴向流速 m/s
        Gamma_avg: 平均环量 m²/s
        Z: 叶片数
        airfoil: 翼型类型
        circulation: 环量分布类型

    Returns:
        list[BladeSection]
    """
    sections = []
    L = R - r_hub  # 叶高 mm

    for i in range(N):
        # ── 径向位置 ──
        # 从 0.05 开始避开轮毂，到 0.95 避免叶尖效应
        t = (i + 0.5) / N  # 截面中心位置
        r = r_hub + t * L

        if i == 0:
            r = r_hub + 0.05 * L  # 离轮毂 5% 叶高
        if i == N - 1:
            r = R - 0.05 * L  # 离叶尖 5% 叶高

        r_star = r / R  # 无量纲半径
        r_pct = (r - r_hub) / L if L > 0 else 0

        # ── 圆周速度 ──
        u = omega * r / 1000.0  # m/s

        # ── 环量分布 ──
        if circulation == CirculationType.EQUAL:
            # 等环量（自由旋涡）：c_u · r = const
            # Γ = 2πr · c_u = const → c_u = Γ_avg / (2πr)
            Gamma = Gamma_avg
            c_u2 = Gamma / (2.0 * math.pi * (r / 1000.0))
        elif circulation == CirculationType.LINEAR:
            # 线性变化环量：从叶根到叶尖线性减少
            # 叶根加载更多
            k = 1.0 - 0.5 * (r_star - nu) / (1.0 - nu) if r > r_hub else 1.0
            Gamma = Gamma_avg * k
            c_u2 = Gamma / (2.0 * math.pi * (r / 1000.0))
        else:
            # 变环量（指数分布）：c_u · r^k = const, k ≈ 0.5~0.8
            k_exp = 0.7
            # 假设平均环量对应平均半径处
            r_avg = (r_hub + R) / 2.0
            const_val = Gamma_avg * (r_avg / 1000.0) ** (k_exp - 1.0) / (2.0 * math.pi)
            c_u2 = const_val / (r / 1000.0) ** k_exp
            Gamma = 2.0 * math.pi * c_u2 * (r / 1000.0)

        # 进口无预旋（c_u1 = 0，最常见的轴流设计）
        c_u1 = 0.0

        # ── 速度三角形 ──
        # 绝对速度
        v1 = math.sqrt(c_a**2 + c_u1**2)
        v2 = math.sqrt(c_a**2 + c_u2**2)

        # 绝对气流角
        alpha1 = math.degrees(math.atan2(c_a, c_u1)) if abs(c_u1) > 1e-6 else 90.0
        alpha2 = math.degrees(math.atan2(c_a, c_u2)) if abs(c_u2) > 1e-6 else 90.0

        # 相对速度
        w1 = math.sqrt(c_a**2 + (u - c_u1)**2)
        w2 = math.sqrt(c_a**2 + (u - c_u2)**2)

        # 相对气流角（从切向测量 —— 风机标准）
        beta1 = math.degrees(math.atan2(c_a, (u - c_u1))) if abs(u - c_u1) > 1e-6 else 90.0
        beta2 = math.degrees(math.atan2(c_a, (u - c_u2))) if abs(u - c_u2) > 1e-6 else 90.0

        # 叶片扭角
        theta = beta2 - beta1

        # 安装角（stagger angle）：取进出口角中间值
        chi = (beta1 + beta2) / 2.0

        # ── 弦长计算 ──
        # 基于翼型升力系数法：
        #   Γ = (1/2) · c · Z · cl · w_m   （环量 → 弦长）
        #   c = 2 · Γ / (Z · cl · w_m)
        #
        # 其中 w_m ≈ (w₁ + w₂) / 2  （平均相对速度）
        # 引入叶片实度修正

        w_m = (w1 + w2) / 2.0

        # 攻角（由翼型决定）
        aoa = airfoil.design_aoa
        cl = airfoil.design_cl

        # 叶片实度修正：Schlichting 修正
        # 实际轴流叶片相邻叶片干涉会降低升力
        # 先按孤立翼型计算弦长，再修正
        if w_m > 0 and abs(math.sin(math.radians(chi))) > 1e-6:
            # 弦长 c = 2 * Γ / (Z * cl * w_m)
            c_raw = 2000.0 * Gamma / (Z * cl * w_m)  # m → mm
        else:
            c_raw = 50.0  # 默认值

        # 限制弦长合理范围
        pitch = 2.0 * math.pi * r / Z  # 栅距 mm
        c = _clamp(c_raw, 0.3 * pitch, 1.5 * pitch)

        # 最大厚度
        t_max = c * airfoil.max_thickness_pct / 100.0

        # ── 实度检查 ──
        sigma = c / pitch if pitch > 0 else 0
        if sigma < 0.4:
            # 实度过小，增大弦长
            c = 0.4 * pitch
        elif sigma > 1.5:
            # 实度过大，减小弦长
            c = 1.5 * pitch

        section = BladeSection(
            r=round(r, 2),
            r_pct=round(r_pct, 4),
            r_star=round(r_star, 4),
            u=round(u, 3),
            w1=round(w1, 3),
            w2=round(w2, 3),
            v1=round(v1, 3),
            v2=round(v2, 3),
            beta1=round(beta1, 3),
            beta2=round(beta2, 3),
            alpha1=round(alpha1, 3),
            alpha2=round(alpha2, 3),
            theta=round(theta, 3),
            chi=round(chi, 3),
            c=round(c, 2),
            t=round(t_max, 2),
            cl=round(cl, 3),
            aoa=round(aoa, 2),
            Gamma=round(Gamma, 4),
            Z=Z,
        )
        sections.append(section)

    return sections


def _material_density(material: str) -> float:
    """材料密度 kg/m³"""
    if material in ("Q235B", "Q345", "20#", "45#"):
        return 7850.0
    elif material.startswith(("304", "316")):
        return 7930.0
    elif material.startswith(("2A", "7A", "5A")):
        return 2700.0
    elif material.startswith(("6061", "7075")):
        return 2700.0
    elif material == "LY12":
        return 2780.0
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
        "6061": 276,
        "7075": 503,
    }
    return data.get(material, 200)


def _validate_design(r: AxialFanResult):
    """设计结果合理性检查"""
    w = r.warnings

    if r.D < 100:
        w.append(f"叶轮直径 D={r.D:.0f}mm 过小，可能不是轴流")
    if r.D > 5000:
        w.append(f"叶轮直径 D={r.D:.0f}mm 过大，考虑结构")
    if r.nu < 0.20:
        w.append(f"轮毂比 ν={r.nu:.2f} < 0.25，叶片长宽比可能过大")
    if r.nu > 0.75:
        w.append(f"轮毂比 ν={r.nu:.2f} > 0.70，近似离心风机")
    if r.c_a < 5 or r.c_a > 60:
        w.append(f"轴向流速 c_a={r.c_a:.1f} m/s 超出合理范围")
    if r.u_tip > 130:
        w.append(f"叶尖速度 u_t={r.u_tip:.1f} m/s 过高，噪音显著")
    if r.eta < 0.60:
        w.append(f"估算效率 {r.eta:.1%} 偏低")
    if r.ns < 60:
        w.append(f"比转速 n_s={r.ns:.1f} < 60，建议考虑离心风机")
    if r.ns > 350:
        w.append(f"比转速 n_s={r.ns:.1f} > 350，可考虑对旋方案")


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


def calc_tip_speed(D: float, n: float) -> float:
    """
    计算叶尖圆周速度

    Args:
        D: 叶轮直径 mm
        n: 转速 r/min

    Returns:
        叶尖速度 m/s
    """
    return math.pi * n * D / 60000.0


def estimate_diameter(Q: float, P: float, n: float) -> float:
    """
    快速估算所需叶轮直径

    用于初步选型。

    Args:
        Q: 流量 m³/h
        P: 全压 Pa
        n: 转速 r/min

    Returns:
        估算叶轮直径 mm
    """
    ns = calc_ns(Q, P, n)
    nu = _hub_ratio_from_ns(ns)
    c_a = _axial_velocity(ns)
    Q_s = Q / 3600.0
    D_m = math.sqrt(4.0 * Q_s / (math.pi * c_a * (1.0 - nu**2)))
    return round(D_m * 1000.0, -1)  # 按 10mm 取整


# ═══════════════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_cases = [
        AxialFanInput(Q=50000, P=300, n=960,   airfoil=AirfoilType.CLARK_Y),
        AxialFanInput(Q=20000, P=800, n=1450,  airfoil=AirfoilType.CLARK_Y),
        AxialFanInput(Q=5000,  P=2000, n=2900, airfoil=AirfoilType.RAF_38),
    ]

    for i, inp in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"  测试案例 {i}: Q={inp.Q}m³/h  P={inp.P}Pa  n={inp.n}r/min")
        print(f"{'='*60}")
        try:
            result = design_axial_fan(inp)
            print(result.summary)
        except Exception as e:
            print(f"  ❌ 设计失败: {e}")
