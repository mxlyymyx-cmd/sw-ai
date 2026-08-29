"""
法兰参数数据模型

定义法兰的标准化参数结构，贯穿整个 Pipeline 的输入输出。
"""

from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class FlangeType(str, Enum):
    """法兰类型"""
    PLATE = "plate"          # 板式平焊（GB/T 9119）
    SLIP_ON = "slip_on"      # 带颈平焊（GB/T 9116）
    WELD_NECK = "weld_neck"  # 对焊（GB/T 9115）
    THREADED = "threaded"    # 螺纹（GB/T 9114）
    BLIND = "blind"          # 法兰盖（GB/T 9123）


class SealType(str, Enum):
    """密封面类型"""
    RF = "rf"          # 突面
    FF = "ff"          # 全平面
    MFM = "mfm"        # 凹凸面
    TG = "tg"          # 榫槽面
    RJ = "rj"          # 环连接面


SEAL_DESCRIPTIONS = {
    SealType.RF: "突面（RF）— 最常用，适用于 PN ≤ 40 的各种工况",
    SealType.FF: "全平面（FF）— 阀门、铸铁法兰常用",
    SealType.MFM: "凹凸面（MFM）— 密封要求较高，PN ≥ 16",
    SealType.TG: "榫槽面（TG）— 剧毒/易燃易爆介质",
    SealType.RJ: "环连接面（RJ）— 高压高温，PN ≥ 63",
}


@dataclass
class FlangeParams:
    """
    法兰盘全部参数
    
    核心尺寸遵循 GB/T 9112-2010 体系。
    最小单位：mm
    """
    # ── 必填参数（无默认值） ──
    dn: int                     # 公称通径 (DN10 ~ DN2000)
    pn: int                     # 公称压力 (PN10, PN16, PN25, PN40, ...)
    d: float                    # 法兰外径
    k: float                    # 螺栓孔中心圆直径
    l: float                    # 螺栓孔直径
    n: int                      # 螺栓孔数量
    c: float                    # 法兰厚度

    # ── 识别信息 ──
    flange_type: FlangeType = FlangeType.PLATE  # 法兰类型
    seal_type: SealType = SealType.RF           # 密封面类型

    # ── 密封面尺寸（RF） ──
    f: float = 0.0              # 密封面凸出高度（RF 面常用 2mm）
    d1: float = 0.0             # 密封面外径（RF 面直径）
    
    # ── 内径 / 接管尺寸 ──
    inner_d: float = 0.0        # 法兰内径（≈接管外径）
    
    # ── 对焊法兰专属 ──
    neck_d: float = 0.0         # 颈部小端外径
    neck_h: float = 0.0         # 颈部高度
    neck_thk: float = 0.0       # 颈部壁厚
    hub_len: float = 0.0        # 锥颈长度
    
    # ── 材料 ──
    material: str = "Q235B"     # 默认碳钢
    standard: str = "GB/T 9119-2010"  # 执行标准

    # ── 加工信息 ──
    roughness: float = 6.3      # 密封面粗糙度 Ra
    coating: str = ""           # 表面处理

    def __post_init__(self):
        """类型自动转换"""
        if isinstance(self.flange_type, str):
            self.flange_type = FlangeType(self.flange_type)
        if isinstance(self.seal_type, str):
            self.seal_type = SealType(self.seal_type)
        self.d = float(self.d)
        self.k = float(self.k)
        self.l = float(self.l)
        self.n = int(self.n)
        self.c = float(self.c)

    @property
    def bolt_hole_pattern(self) -> dict:
        """螺栓孔分布信息"""
        return {
            "pcd": self.k,
            "hole_dia": self.l,
            "count": self.n,
            "angle_offset": 0.0 if self.n % 2 == 0 else 45.0,
        }

    @property
    def summary(self) -> str:
        """人类可读的参数摘要"""
        return (
            f"{self.flange_type.value.upper()} 法兰 {self.standard}\n"
            f"  DN{self.dn}  PN{self.pn}  {self.seal_type.value.upper()} 面\n"
            f"  外径 ø{self.d} × 厚 {self.c}mm  |  内径 ø{self.inner_d or '?'}\n"
            f"  螺栓孔: {self.n}×ø{self.l}  PCD={self.k}\n"
            f"  材料: {self.material}"
        )

    def to_dict(self) -> dict:
        # 只过滤 None 和空值，保留 0（0 是合法计算结果）
        return {
            k: v for k, v in asdict(self).items()
            if v is not None and v != ""
        }


@dataclass
class ExtractionResult:
    """AI 提取结果"""
    success: bool
    params: Optional[FlangeParams] = None
    raw_input: str = ""
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)
    error: Optional[str] = None
