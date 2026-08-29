"""
SolidWorks 参数化法兰盘生成器

通过 SolidWorks COM API (OLE Automation) 自动创建法兰盘 3D 模型。

依赖: pywin32 (Windows only, SolidWorks 需安装)
运行环境: Windows + SolidWorks 2022+
"""

import os
import time
from typing import Optional
from dataclasses import dataclass

from .params import FlangeParams, FlangeType

# ── Windows only ──
try:
    import pythoncom
    import win32com.client as win32
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


# ═══════════════════════════════════════════════════════════════
# SolidWorks COM API 封装
# ═══════════════════════════════════════════════════════════════


@dataclass
class SldWorksSession:
    """SolidWorks 会话管理器"""
    app: Optional[object] = None
    doc: Optional[object] = None
    part: Optional[object] = None

    def __bool__(self):
        return self.app is not None


def connect_sw(visible: bool = True, new_doc: bool = True) -> SldWorksSession:
    """
    连接 SolidWorks 并创建新零件

    Args:
        visible: 是否显示 SW 窗口
        new_doc: 是否新建零件文档

    Returns:
        SldWorksSession
    """
    if not HAS_PYWIN32:
        raise RuntimeError(
            "需要 pywin32 和 Windows 环境\n"
            "  pip install pywin32\n"
            "  仅支持 Windows + SolidWorks"
        )

    pythoncom.CoInitialize()

    try:
        # 尝试连接已运行的实例
        app = win32.GetActiveObject("SldWorks.Application")
    except Exception:
        # 启动新实例
        app = win32.Dispatch("SldWorks.Application")

    app.Visible = visible

    session = SldWorksSession(app=app)

    if new_doc:
        # 创建新零件文档
        doc_type = 1  # swDocPART
        template = app.GetDocumentTemplate(doc_type, 0, 0, 0)
        if not template:
            template = os.path.expandvars(
                r"%PROGRAMFILES%\SolidWorks Corp\SolidWorks\lang\chinese-simplified\Templates\gb_part.prtdot"
            )
        doc = app.NewDocument(template, 0, 0.0, 0.0)
        session.doc = doc
        session.part = doc

    return session


def close_sw(session: SldWorksSession, save: bool = False, path: Optional[str] = None):
    """关闭 SolidWorks 文档"""
    if session.doc and save and path:
        session.doc.SaveAs(path)
    if session.doc:
        session.doc.Close()
    if session.app:
        pass


# ═══════════════════════════════════════════════════════════════
# 特征创建 ── 法兰盘建模步骤
# ═══════════════════════════════════════════════════════════════


def _ensure_sketch_edit(part, plan_ref: str = "前视基准面"):
    """进入草图编辑状态"""
    # 选择基准面
    selection = part.Extension.SelectByID2(
        plan_ref, "PLANE", 0, 0, 0, False, 0, None, 0
    )
    # 插入草图
    part.SketchManager.InsertSketch(True)


def _add_dimension(part, name: str, value: float):
    """添加标注并设置尺寸"""
    part.AddDimension2(0, 0, 0)
    # 获取最后添加的标注并设值
    params = part.Parameter(name)
    if params:
        params.SystemValue = value / 1000.0  # SW 使用米为单位


def create_plate_flange(part, params: FlangeParams) -> bool:
    """
    创建板式平焊法兰

    建模流程:
    1. 前视基准面 → 草图（法兰外圆 + 内孔）
    2. 拉伸凸台（法兰主体）
    3. 密封面凸台（RF 面）
    4. 螺栓孔（圆周阵列）

    Args:
        part: SolidWorks Part 对象
        params: 法兰参数

    Returns:
        True 表示成功
    """
    try:
        d_outer = params.d / 1000.0   # 转米
        d_inner = (params.inner_d or params.d * 0.6) / 1000.0
        thickness = params.c / 1000.0
        seal_h = params.f / 1000.0
        seal_d = (params.d1 or d_outer * 0.85) / 1000.0
        bolt_pcd = params.k / 1000.0
        bolt_dia = params.l / 1000.0
        bolt_count = params.n

        # ═══ Step 1: 法兰主体（外圆内孔的圆环） ═══
        part.SketchManager.InsertSketch(True)

        # 外圆
        circle_outer = part.SketchManager.CreateCircle(0, 0, 0, d_outer / 2, 0, 0)
        # 内孔
        circle_inner = part.SketchManager.CreateCircle(0, 0, 0, d_inner / 2, 0, 0)

        part.SketchManager.InsertSketch(True)
        part.ClearSelection2(True)

        # 拉伸凸台
        feature_mgr = part.FeatureManager
        feat_extrude = feature_mgr.FeatureExtrusion2(
            True,           # IsReverseDirection
            True,           # IsDefaultThickness
            False,          # IsDraft
            0,              # DraftAngle
            0,              # StartCondition (0=SketchPlane)
            1,              # EndCondition (1=Blind)
            thickness,       # Depth
            0,              # FlipSideToCut
            0,              # ReverseOffsetDir
            0,              # FlipInsideOut
            0,              # TranslateSurface
            0,              # MergeAuto
            False,          # UseFeatScope
            0,              # FeatScopeType
            0.0,            # WallThickness (thin feature)
            0.0,            # Gap
            0,              # Auto fillet edges
            0.0,            # Fillet radius
            0,              # check direction
            False,          # merge solids
        )

        # ═══ Step 2: 密封面凸台（RF 面） ═══
        if seal_h > 0.001:
            # 在法兰顶面画密封面圆
            part.SketchManager.InsertSketch(True)

            seal_circle = part.SketchManager.CreateCircle(
                0, 0, 0, seal_d / 2, 0, 0
            )
            part.SketchManager.InsertSketch(True)
            part.ClearSelection2(True)

            feat_seal = feature_mgr.FeatureExtrusion2(
                True, False, False, 0, 0, 1, seal_h,
                0, 0, 0, 0, True, 0, 0.0, 0.0, 0, False, False,
            )

        # ═══ Step 3: 螺栓孔 ═══
        # 创建一个螺栓孔
        if bolt_count > 0:
            part.SketchManager.InsertSketch(True)

            bolt_hole = part.SketchManager.CreateCircle(
                0, 0, 0, bolt_dia / 2, 0, 0
            )
            # 添加约束将孔定位到 PCD 上
            part.AddDimension2(bolt_pcd, 0, 0)

            part.SketchManager.InsertSketch(True)
            part.ClearSelection2(True)

            # 切除拉伸（通孔）— 深度按法兰总厚（主体 + 密封面）加余量，保证切穿
            cut_depth = (thickness + seal_h) * 1.2 + 0.002
            feat_cut = feature_mgr.FeatureCut(
                False, False, False, 0, 0, 1, cut_depth,
                0, False, False, False, False, 0, 0, False, False,
            )

            # 圆周阵列
            if bolt_count > 1:
                circle_pattern = feature_mgr.FeatureCircularPattern(
                    bolt_count,      # InstanceCount
                    360.0,           # TotalAngle (degrees)
                    False,           # EqualSpacing
                    False,           # ReverseDirection
                    False,           # KeepMark
                    f"{feat_cut.Name if feat_cut else 'Cut-Extrude1'}"
                )

        part.ClearSelection2(True)
        part.ViewZoomtofit2()

        return True

    except Exception as e:
        print(f"[SW Generator] 建模失败: {e}")
        return False


def generate_flange(params: FlangeParams, output_path: Optional[str] = None) -> str:
    """
    生成法兰盘模型

    Args:
        params: 法兰参数
        output_path: 保存路径 (.SLDPRT)，默认自动生成

    Returns:
        模型保存路径
    """
    session = connect_sw(visible=True)

    try:
        if params.flange_type == FlangeType.PLATE:
            create_plate_flange(session.part, params)
        else:
            raise NotImplementedError(f"暂不支持 {params.flange_type} 类型")

        # 自动命名
        if not output_path:
            output_path = (
                f"Flange_DN{params.dn}_PN{params.pn}_"
                f"{params.flange_type.value}_{params.seal_type.value}.SLDPRT"
            )

        # 保存
        session.doc.SaveAs(output_path)
        print(f"[SW Generator] 模型已保存: {output_path}")
        return output_path

    finally:
        # 不关闭窗口，让用户检查
        pass


# ═══════════════════════════════════════════════════════════════
# 离线预览（无 SW 环境时生成代码而非模型）
# ═══════════════════════════════════════════════════════════════


def generate_sw_macro(params: FlangeParams) -> str:
    """
    生成 SolidWorks VBA 宏代码（无 pywin32 时的替代方案）

    可以直接在 SolidWorks 中运行（工具 → 宏 → 运行）

    Returns:
        VBA 宏代码字符串
    """
    d = params.d
    inner_d = params.inner_d or params.d * 0.55
    c = params.c
    f = params.f
    d1_val = params.d1 or d * 0.8
    k = params.k
    l = params.l
    n = params.n
    dn = params.dn
    pn = params.pn

    # 预计算 VBA 表达式（避免 f-string 中 ! 被 Python 解释为格式转换）
    r_outer = f"{d / 2000}!"
    r_inner = f"{inner_d / 2000}!"
    depth_c = f"{c / 1000}!"
    r_seal = f"{d1_val / 2000}!"
    depth_f = f"{f / 1000}!"
    pcd_k = f"{k / 2000}!"
    r_bolt = f"{l / 2000}!"
    # 螺栓孔切穿深度：法兰总厚（主体 c + 密封面 f）加余量，不再硬编码
    depth_cut = f"{(c + f) * 1.2 / 1000 + 0.002}!"

    macro = f"""' SolidWorks 宏 — 参数化法兰盘 DN{dn} PN{pn}
' 自动生成 by solidworks-parametric v0.1.0
' 在 SW 中: 工具 → 宏 → 运行

Dim swApp As Object
Dim Part As Object
Dim boolStatus As Boolean

Sub main()
    Set swApp = Application.SldWorks
    Set Part = swApp.NewDocument("", 0, 0, 0)
    swApp.Visible = True

    ' === 法兰主体 ===
    Dim skSegment As Object
    
    Part.SketchManager.InsertSketch True
    ' 外圆 {d}mm
    Set skSegment = Part.SketchManager.CreateCircle(0#, 0#, 0#, {r_outer}, 0#, 0#)
    ' 内孔 {inner_d}mm
    Set skSegment = Part.SketchManager.CreateCircle(0#, 0#, 0#, {r_inner}, 0#, 0#)
    Part.SketchManager.InsertSketch True
    Part.ClearSelection2 True

    ' 拉伸 {c}mm
    Dim myFeature As Object
    Set myFeature = Part.FeatureManager.FeatureExtrusion2(True, True, False, 0#, 0, 1, {depth_c}, 0, 0, 0, 0, True, 0, 0#, 0#, 0, False, False)

    ' === 密封面 (RF) 凸台 {f}mm ===
    Part.SketchManager.InsertSketch True
    Set skSegment = Part.SketchManager.CreateCircle(0#, 0#, 0#, {r_seal}, 0#, 0#)
    Part.SketchManager.InsertSketch True
    Part.ClearSelection2 True
    Set myFeature = Part.FeatureManager.FeatureExtrusion2(True, True, False, 0#, 0, 1, {depth_f}, 0, 0, 0, 0, True, 0, 0#, 0#, 0, False, False)

    ' === 螺栓孔 {n}x\u00f8{l} PCD={k} ===
    Part.SketchManager.InsertSketch True
    Set skSegment = Part.SketchManager.CreateCircle({pcd_k}, 0#, 0#, {r_bolt}, 0#, 0#)
    Part.SketchManager.InsertSketch True
    Part.ClearSelection2 True
    Set myFeature = Part.FeatureManager.FeatureCut(False, False, False, 0#, 0, 1, {depth_cut}, 0, False, False, False, False, 0, 0, False, False)
    
    ' 圆周阵列
    Part.ClearSelection2 True
    Set myFeature = Part.FeatureManager.FeatureCircularPattern({n}, 360#, False, False, False, "Cut-Extrude1")

    Part.ViewZoomtofit2
    MsgBox "法兰盘 DN{dn} PN{pn} 生成完成", vbInformation, "solidworks-parametric"
End Sub
"""
    return macro
