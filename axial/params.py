"""
轴流风机参数数据模型

覆盖设计输入 → 计算输出 → 3D建模的全链路数据。
参考标准: GB/T 1236-2017 《工业通风机性能试验》
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import math


class AirfoilType(str, Enum):
    """叶片翼型类型"""
    CLARK_Y = "clark_y"            # CLARK-Y 通用翼型
    LS_0413 = "ls_0413"            # LS 系列 (LS-0413)
    LS_0409 = "ls_0409"            # LS 系列 (LS-0409)
    RAF_30 = "raf_30"              # RAF 系列 (RAF-30)
    RAF_38 = "raf_38"              # RAF 系列 (RAF-38)
    NACA_4412 = "naca_4412"        # NACA 4412
    NACA_2412 = "naca_2412"        # NACA 2412
    CUSTOM = "custom"              # 自定义

    @property
    def description(self) -> str:
        return {
            "clark_y": "CLARK-Y — 通用翼型，升力特性好，制造容易【最常用】",
            "ls_0413": "LS-0413 — 薄翼型，适合低压轴流",
            "ls_0409": "LS-0409 — 超薄翼型，适合高速轴流",
            "raf_30": "RAF-30 — 经典翼型，厚翼型，高升力",
            "raf_38": "RAF-38 — 厚翼型，适合高压轴流",
            "naca_4412": "NACA 4412 — 低速通用，后加载",
            "naca_2412": "NACA 2412 — 低速通用，对称偏置",
            "custom": "自定义翼型 — 用户提供坐标",
        }[self.value]

    @property
    def max_thickness_pct(self) -> float:
        """最大相对厚度（%弦长）"""
        return {
            "clark_y": 11.7,
            "ls_0413": 4.0,
            "ls_0409": 3.0,
            "raf_30": 12.0,
            "raf_38": 15.0,
            "naca_4412": 12.0,
            "naca_2412": 12.0,
            "custom": 10.0,
        }[self.value]

    @property
    def design_cl(self) -> float:
        """设计升力系数"""
        return {
            "clark_y": 0.80,
            "ls_0413": 0.65,
            "ls_0409": 0.55,
            "raf_30": 0.90,
            "raf_38": 0.85,
            "naca_4412": 0.75,
            "naca_2412": 0.70,
            "custom": 0.70,
        }[self.value]

    @property
    def design_aoa(self) -> float:
        """设计攻角 (°)"""
        return {
            "clark_y": 4.0,
            "ls_0413": 3.0,
            "ls_0409": 2.5,
            "raf_30": 5.0,
            "raf_38": 4.5,
            "naca_4412": 4.0,
            "naca_2412": 3.5,
            "custom": 4.0,
        }[self.value]


class CirculationType(str, Enum):
    """环量分布类型"""
    EQUAL = "equal"              # 等环量（自由旋涡）— 径向平衡
    VARIABLE = "variable"        # 变环量 — 可优化效率/噪声
    LINEAR = "linear"            # 线性变化环量

    @property
    def description(self) -> str:
        return {
            "equal": "等环量（自由旋涡）— 理论简单，径向速度均匀",
            "variable": "变环量 — 可优化效率或噪声特性",
            "linear": "线性变化 — 介于等环量与变环量之间",
        }[self.value]


@dataclass
class AxialFanInput:
    """
    轴流风机设计输入参数

    用户（或客户）提供的基础设计条件。
    """
    # ── 设计工况（必填） ──
    Q: float              # 流量 (m³/h)
    P: float              # 全压 (Pa)
    n: float              # 转速 (r/min)

    # ── 介质（有默认值） ──
    rho: float = 1.2      # 介质密度 (kg/m³)，标准空气 ≈ 1.2

    # ── 可选 ──
    nu: float = 0.0       # 轮毂比 ν = d/D（0 = 根据 ns 自动选择）
    airfoil: AirfoilType = AirfoilType.CLARK_Y  # 翼型类型
    circulation: CirculationType = CirculationType.EQUAL  # 环量分布
    Z: int = 0            # 叶片数（0 = 自动计算）
    D_override: float = 0.0   # 叶轮直径限制 (mm)，0=自动计算
    delta_clearance: float = 0.0  # 叶顶间隙 (mm)，0=自动算
    material: str = "Q235B"  # 材料
    sections: int = 5      # 径向截面数（沿叶高）

    def __post_init__(self):
        if isinstance(self.airfoil, str):
            self.airfoil = AirfoilType(self.airfoil)
        if isinstance(self.circulation, str):
            self.circulation = CirculationType(self.circulation)


@dataclass
class BladeSection:
    """
    叶片径向截面参数

    每个截面是叶片沿径向的一个"切面"，
    包含了该截面处的翼型、弦长、安装角、扭角等信息。
    """
    # ── 径向位置 ──
    r: float              # 截面半径 mm
    r_pct: float          # 相对径向位置 0=叶根 1=叶尖
    r_star: float         # 无量纲半径 r/R

    # ── 运动参数 ──
    u: float              # 圆周速度 m/s
    w1: float             # 进口相对速度 m/s
    w2: float             # 出口相对速度 m/s
    v1: float             # 进口绝对速度 m/s
    v2: float             # 出口绝对速度 m/s

    # ── 角度参数 ──
    beta1: float          # 进口相对气流角 (°)
    beta2: float          # 出口相对气流角 (°)
    alpha1: float         # 进口绝对气流角 (°)
    alpha2: float         # 出口绝对气流角 (°)
    theta: float          # 叶片扭角 β₂ - β₁ (°)
    chi: float            # 安装角 (°) = (β₁ + β₂) / 2

    # ── 翼型参数 ──
    c: float              # 弦长 mm
    t: float              # 最大厚度 mm (= c * max_thickness_pct)
    cl: float             # 升力系数
    aoa: float            # 攻角 (°)

    # ── 环量 ──
    Gamma: float          # 环量 m²/s
    Z: int = 0            # 叶片数（0 = 未指定，solidity 返回 0）

    # ── 闭环校验字段 ──
    c_u2: float = 0.0     # 出口旋绕分速 m/s
    w_m: float = 0.0      # 平均相对速度 m/s
    Df: float = 0.0       # Lieblein 扩散因子（限值 0.60，超限叶背分离）
    cl_req: float = 0.0   # 实际弦长下的需用升力系数（限值 1.1）

    @property
    def solidity(self) -> float:
        """实度 σ = c / t_pitch（栅距 t = 2πr/Z）"""
        if self.Z <= 0 or self.r <= 0:
            return 0.0
        return self.c * self.Z / (2.0 * math.pi * self.r)

    def to_dict(self) -> dict:
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, float):
                v = round(v, 4)
            result[k] = v
        result["solidity"] = round(self.solidity, 4)
        return result


@dataclass
class AxialFanResult:
    """
    轴流风机设计计算结果

    每一步计算都有注释标名是公式计算还是经验取值。
    单位统一：mm, °, m/s, Pa, kW
    """
    # ── 设计输入（备份） ──
    input_params: AxialFanInput = field(default_factory=AxialFanInput)

    # ═══ 定型参数 ═══
    ns: float = 0.0             # 比转速（中国标准）
    n_y: float = 0.0            # 比直径

    # ═══ 主要尺寸 (mm) ═══
    D: float = 0.0              # 叶轮外径
    d: float = 0.0              # 轮毂直径
    nu: float = 0.0             # 轮毂比 ν = d/D
    R: float = 0.0              # 叶轮半径
    r_hub: float = 0.0          # 轮毂半径
    L: float = 0.0              # 叶高 (R - r_hub)

    # ═══ 速度参数 ═══
    u_tip: float = 0.0          # 叶尖圆周速度 m/s
    u_hub: float = 0.0          # 轮毂圆周速度 m/s
    c_a: float = 0.0            # 轴向流速 m/s
    c_u2_avg: float = 0.0       # 圆周分速平均值 m/s

    # ═══ 无量纲系数 ═══
    phi: float = 0.0            # 流量系数 φ = c_a/u_t
    psi: float = 0.0            # 压力系数 ψ = 2P/(ρ·u_t²)

    # ═══ 设计闭环验证（欧拉 + Lieblein + DeHaller） ═══
    P_th: float = 0.0           # 欧拉理论全压（面积加权）Pa
    P_dev: float = 0.0          # 闭环偏差 (η·P_th − P)/P，±15% 内可接受
    Df_max: float = 0.0         # 最大 Lieblein 扩散因子（限值 0.60）
    dehaller_min: float = 0.0   # 最小 DeHaller 数 w₂/w₁（限值 0.72）
    cl_req_max: float = 0.0     # 最大需用升力系数（限值 1.1）

    # ═══ 叶片参数 ═══
    Z: int = 0                  # 叶片数
    airfoil: AirfoilType = AirfoilType.CLARK_Y
    circulation_type: CirculationType = CirculationType.EQUAL

    # ═══ 叶顶间隙 ═══
    delta: float = 0.0          # 叶顶间隙 mm
    Dc: float = 0.0             # 集流器直径 mm

    # ═══ 径向截面分布 ═══
    sections: list[BladeSection] = field(default_factory=list)

    # ═══ 平均参数（供整体性能用） ═══
    beta1_avg: float = 0.0      # 平均进口角 (°)
    beta2_avg: float = 0.0      # 平均出口角 (°)
    c_avg: float = 0.0          # 平均弦长 mm
    chi_avg: float = 0.0        # 平均安装角 (°)

    # ═══ 性能估算 ═══
    eta: float = 0.0            # 估算效率
    N_shaft: float = 0.0        # 轴功率 (kW)
    N_motor: float = 0.0        # 电机功率 (kW)

    # ═══ 强度校核（初步） ═══
    sigma_max: float = 0.0      # 最大离心应力 MPa
    safety_factor: float = 0.0  # 安全系数

    # ═══ 元数据 ═══
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """人类可读的设计结果摘要"""
        lines = [
            f"{'='*55}",
            f"  轴流风机设计结果",
            f"  翼型: {self.airfoil.value.upper()}",
            f"  工况: Q={self.input_params.Q:.0f}m³/h  P={self.input_params.P:.0f}Pa  "
            f"n={self.input_params.n:.0f}r/min",
            f"{'='*55}",
            f"",
            f"  定型参数",
            f"    比转速    n_s = {self.ns:.1f}",
            f"    比直径    D_y = {self.n_y:.1f}",
            f"    估算效率  η   = {self.eta:.1%}",
            f"",
            f"  主要尺寸 (mm)",
            f"    叶轮直径  D   = {self.D:.1f}",
            f"    轮毂直径  d   = {self.d:.1f}",
            f"    轮毂比    ν   = {self.nu:.3f}",
            f"    叶顶间隙  δ   = {self.delta:.2f}",
            f"    集流器直径 Dc = {self.Dc:.1f}",
            f"",
            f"  速度参数",
            f"    叶尖速度  u_t = {self.u_tip:.1f} m/s",
            f"    轮毂速度  u_h = {self.u_hub:.1f} m/s",
            f"    轴向流速  c_a = {self.c_a:.1f} m/s",
            f"",
            f"  叶片",
            f"    叶片数    Z   = {self.Z}",
            f"    翼型      {self.airfoil.value} (t/c={self.airfoil.max_thickness_pct:.1f}%)",
            f"    环量分布  {self.circulation_type.value}",
            f"    截面数    N   = {len(self.sections)}",
        ]

        # 各截面参数
        if self.sections:
            lines.append(f"")
            lines.append(f"  截面分布（叶根 → 叶尖）:")
            lines.append(f"  {'r(mm)':>8} {'r*':>6} {'c(mm)':>8} {'σ':>6} {'chi(°)':>7} "
                         f"{'β1(°)':>7} {'β2(°)':>7} {'θ(°)':>6} {'Df':>6}")
            lines.append(f"  {'─'*8} {'─'*6} {'─'*8} {'─'*6} {'─'*7} "
                         f"{'─'*7} {'─'*7} {'─'*6} {'─'*6}")
            for sec in self.sections:
                lines.append(f"  {sec.r:>8.1f} {sec.r_star:>6.3f} {sec.c:>8.1f} "
                             f"{sec.solidity:>6.2f} {sec.chi:>7.2f} {sec.beta1:>7.2f} "
                             f"{sec.beta2:>7.2f} {sec.theta:>6.2f} {sec.Df:>6.2f}")

        lines.append(f"")
        lines.append(f"  功率")
        lines.append(f"    轴功率    Nₛ = {self.N_shaft:.2f} kW")
        lines.append(f"    电机功率  Nₘ = {self.N_motor:.2f} kW")

        if self.P_th > 0:
            lines += [
                f"",
                f"  设计闭环验证（欧拉方程 + Lieblein）",
                f"    流量系数  φ     = {self.phi:.3f}",
                f"    压力系数  ψ     = {self.psi:.3f}",
                f"    理论全压  P_th  = {self.P_th:.0f} Pa（面积加权）",
                f"    闭环偏差        = {self.P_dev:+.1%}（±15%内可接受）",
                f"    Lieblein  Df_max = {self.Df_max:.2f}  (限值 0.60)",
                f"    DeHaller  w₂/w₁_min = {self.dehaller_min:.2f}  (限值 0.72)",
                f"    需用升力  cl_max = {self.cl_req_max:.2f}  (限值 1.1)",
            ]

        if self.safety_factor > 0:
            lines.append(f"")
            lines.append(f"  强度校核")
            lines.append(f"    最大应力  σ_max = {self.sigma_max:.1f} MPa")
            lines.append(f"    安全系数  n_safe = {self.safety_factor:.2f}")

        if self.warnings:
            lines.append(f"")
            lines.append(f"  ⚠️  警告:")
            for w in self.warnings:
                lines.append(f"    • {w}")
        if self.notes:
            lines.append(f"")
            lines.append(f"  💡  说明:")
            for n in self.notes:
                lines.append(f"    • {n}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为字典（保留 0 值：0 是合法计算结果，不能丢弃）"""
        sections_data = [s.to_dict() for s in self.sections]
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, (AirfoilType, CirculationType)):
                v = v.value
            elif isinstance(v, AxialFanInput):
                continue
            elif k == "sections":
                v = sections_data
            if v is None or v == "" or (isinstance(v, (list, dict)) and not v):
                continue
            result[k] = round(v, 4) if isinstance(v, float) else v
        return result
