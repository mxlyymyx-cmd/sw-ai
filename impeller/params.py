"""
离心风机叶轮参数数据模型

覆盖设计输入 → 计算输出 → 3D建模的全链路数据。
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import math


class BladeType(str, Enum):
    """叶片型式"""
    FORWARD = "forward"        # 前向（β₂ > 90°）
    RADIAL = "radial"          # 径向（β₂ = 90°）
    RADIAL_TIP = "radial_tip"  # 径向出口（进口弯曲）
    BACKWARD = "backward"      # 后向（β₂ < 90°）
    AIRFOIL = "airfoil"        # 机翼型（后向）

    @property
    def description(self) -> str:
        return {
            "forward": "前向叶轮 — 低压大流量，结构紧凑，高效区窄",
            "radial": "径向叶轮 — 中压，结构简单，耐磨",
            "radial_tip": "径向出口叶轮 — 介于径向与后向之间",
            "backward": "后向叶轮 — 高效率，宽工况，低噪音【最常用】",
            "airfoil": "机翼型叶轮 — 最高效率，制造复杂",
        }[self.value]


class DriveType(str, Enum):
    """传动方式"""
    DIRECT = "direct"          # 直联
    BELT = "belt"              # 皮带传动
    COUPLING = "coupling"      # 联轴器


@dataclass
class ImpellerDesignInput:
    """
    叶轮设计输入参数
    
    用户（或客户）提供的基础设计条件。
    """
    # ── 设计工况（必填） ──
    Q: float              # 流量 (m³/h)
    P: float              # 全压 (Pa)
    n: float              # 转速 (r/min)
    
    # ── 介质（有默认值） ──
    rho: float = 1.2      # 介质密度 (kg/m³)，标准空气≈1.2
    temperature: float = 20.0  # 温度 (°C)
    
    # ── 叶型选择 ──
    blade_type: BladeType = BladeType.BACKWARD
    
    # ── 可选 ──
    drive_type: DriveType = DriveType.DIRECT
    eta_target: float = 0.0    # 目标效率（0=自动估算）
    noise_limit: float = 0.0   # 噪音限制 dB(A)
    max_diameter: float = 0.0  # 最大外径限制 (mm)
    material: str = "Q235B"    # 材料

    def __post_init__(self):
        if isinstance(self.blade_type, str):
            self.blade_type = BladeType(self.blade_type)
        if isinstance(self.drive_type, str):
            self.drive_type = DriveType(self.drive_type)


@dataclass
class ImpellerDesignResult:
    """
    叶轮设计计算结果

    每一步计算都会有注释，标注是公式计算还是经验取值。
    单位统一：mm, °, m/s
    """
    # ── 设计输入（备份） ──
    input_params: ImpellerDesignInput = field(default_factory=ImpellerDesignInput)

    # ═══ 定型参数 ═══
    ns: float = 0.0             # 比转速（中国标准，用 mmH₂O）
    blade_type: BladeType = BladeType.BACKWARD  # 最终叶型

    # ═══ 速度参数 ═══
    u2: float = 0.0             # 叶轮出口圆周速度 (m/s)
    u1: float = 0.0             # 叶轮进口圆周速度 (m/s)
    c0: float = 0.0             # 进口流速 (m/s)
    c2r: float = 0.0            # 出口径向速度 (m/s)

    # ═══ 主要尺寸 (mm) ═══
    D2: float = 0.0             # 叶轮外径
    D1: float = 0.0             # 叶片进口直径
    D0: float = 0.0             # 集流器进口直径
    dh: float = 0.0             # 轮毂直径
    b1: float = 0.0             # 叶片进口宽度
    b2: float = 0.0             # 叶片出口宽度
    nu: float = 0.0             # 轮径比 D₁/D₂

    # ═══ 叶片参数 ═══
    beta1: float = 0.0          # 叶片进口角 (°)
    beta2: float = 0.0          # 叶片出口角 (°)
    Z: int = 0                  # 叶片数
    delta: float = 0.0          # 叶片厚度 (mm)

    # ═══ 性能估算 ═══
    psi: float = 0.0            # 压力系数
    phi: float = 0.0            # 流量系数
    eta: float = 0.0            # 估算效率
    N_shaft: float = 0.0        # 轴功率 (kW)
    N_motor: float = 0.0        # 电机功率 (kW)
    
    # ═══ 强度校核 ═══
    sigma_r: float = 0.0        # 径向应力 (MPa)
    sigma_t: float = 0.0        # 切向应力 (MPa)
    safety_factor: float = 0.0  # 安全系数

    # ═══ 元数据 ═══
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """人类可读的设计结果摘要"""
        lines = [
            f"{'='*55}",
            f"  离心风机叶轮设计结果",
            f"  叶型: {self.blade_type.value.upper()}  β₂={self.beta2:.1f}°",
            f"{'='*55}",
            f"",
            f"  定型参数",
            f"    比转速    n_s = {self.ns:.1f}",
            f"    压力系数  ψ   = {self.psi:.3f}",
            f"    流量系数  φ   = {self.phi:.3f}",
            f"    估算效率  η   = {self.eta:.1%}",
            f"",
            f"  速度参数",
            f"    圆周速度  u₂  = {self.u2:.1f} m/s",
            f"    圆周速度  u₁  = {self.u1:.1f} m/s",
            f"    进口速度  c₀  = {self.c0:.1f} m/s",
            f"",
            f"  主要尺寸 (mm)",
            f"    外径      D₂  = {self.D2:.1f}",
            f"    进口直径  D₁  = {self.D1:.1f}",
            f"    轮毂直径  dₕ  = {self.dh:.1f}",
            f"    进口宽度  b₁  = {self.b1:.1f}",
            f"    出口宽度  b₂  = {self.b2:.1f}",
            f"    轮径比    ν   = {self.nu:.3f}",
            f"",
            f"  叶片",
            f"    进口角    β₁  = {self.beta1:.1f}°",
            f"    出口角    β₂  = {self.beta2:.1f}°",
            f"    叶片数    Z   = {self.Z}",
            f"    叶片厚    δ   = {self.delta:.1f} mm",
            f"",
            f"  功率",
            f"    轴功率    Nₛ = {self.N_shaft:.2f} kW",
            f"    电机功率  Nₘ = {self.N_motor:.2f} kW",
        ]
        if self.warnings:
            lines.append(f"")
            lines.append(f"  ⚠️  警告:")
            for w in self.warnings:
                lines.append(f"    • {w}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """序列化为字典"""
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, BladeType):
                v = v.value
            elif isinstance(v, ImpellerDesignInput):
                continue  # 不序列化输入对象
            if v is None or v == "":
                continue  # 只过滤空值，保留 0（0 是合法计算结果）
            result[k] = round(v, 4) if isinstance(v, float) else v
        return result
