"""
SolidWorks 参数化法兰盘生成器

支持四种法兰类型（GB/T 911X-2010，颈部数据源 HG/T 20592-2009）：
  - plate     板式平焊（GB/T 9119）
  - slip_on   带颈平焊（GB/T 9116）— 直颈
  - weld_neck 对焊（GB/T 9115）— 锥颈 + 焊端直段 H1
  - blind     法兰盖（GB/T 9123）— 无内孔

建模策略（已在 SolidWorks 2022 实测验证）：
  1. 前视基准面绘制半剖面封闭轮廓（X=半径，Y=轴向，原点在密封面顶端）
  2. 轮廓 + 轴心线 → 360° 旋转凸台（含 RF 密封面、法兰盘、颈部）
  3. 密封面顶选面 → 螺栓孔草图（n 个圆均布于 PCD）→ 切除（ThroughAll/ThroughNext）

依赖: pywin32 (Windows only, SolidWorks 需安装)
运行环境: Windows + SolidWorks 2022+
"""

import os
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
# 几何：半剖面轮廓（mm）
# ═══════════════════════════════════════════════════════════════


def _flange_profile(params: FlangeParams) -> list[tuple[float, float]]:
    """
    生成旋转半剖面轮廓点（mm）。

    坐标系：X=半径（≥0），Y=轴向（密封面顶端 y=0，向法兰背面为负）。
    旋转轴为 X=0 的轴心线。点序沿轮廓闭合。

    Raises:
        ValueError: 参数不完整或几何矛盾
    """
    t = params.flange_type
    rb = params.inner_d / 2.0                    # 内孔半径（BL 为 0）
    r1 = (params.d1 or params.d * 0.85) / 2.0    # 密封面半径
    R = params.d / 2.0                           # 法兰外圆半径
    f = params.f
    C = params.c
    yB = -f                # 密封面凸台底（= 法兰盘正面）
    yD = -(f + C)          # 法兰背面

    if R <= r1 or r1 <= 0 or R <= 0:
        raise ValueError(f"几何矛盾: 外径 D={params.d} / 密封面 d1={params.d1}")

    if t in (FlangeType.SLIP_ON, FlangeType.WELD_NECK):
        if params.neck_d <= 0 or params.neck_h <= 0:
            raise ValueError(
                f"{t.value} 法兰缺少颈部参数（neck_d/neck_h），请使用国标 DN×PN 规格"
            )
        nr = params.neck_d / 2.0
        yT = yD - params.neck_h
        if t == FlangeType.SLIP_ON:
            pts = [
                (rb, 0.0), (r1, 0.0), (r1, yB), (R, yB),
                (R, yD), (nr, yD), (nr, yT), (rb, yT),
            ]
        else:
            a1 = (params.neck_tip_d or params.inner_d + 2 * params.neck_thk) / 2.0
            h1 = min(params.neck_straight_h, params.neck_h)
            yS = yT + h1  # 焊端直段上端
            if not (rb < a1 <= nr < r1):
                raise ValueError(
                    f"对焊法兰颈部几何矛盾: 内径={params.inner_d} "
                    f"小端={a1 * 2:.1f} 根径={params.neck_d} 密封面={params.d1}"
                )
            pts = [
                (rb, 0.0), (r1, 0.0), (r1, yB), (R, yB),
                (R, yD), (nr, yD), (a1, yS), (a1, yT), (rb, yT),
            ]
    elif t == FlangeType.BLIND:
        pts = [(0.0, 0.0), (r1, 0.0), (r1, yB), (R, yB), (R, yD), (0.0, yD)]
    else:  # plate
        if not (0 < rb < r1):
            raise ValueError(f"板式法兰几何矛盾: 内径={params.inner_d} 密封面={params.d1}")
        pts = [(rb, 0.0), (r1, 0.0), (r1, yB), (R, yB), (R, yD), (rb, yD)]

    return pts


def _bolt_hole_geometry(params: FlangeParams) -> tuple[float, float, int, float]:
    """螺栓孔几何: (选面参考半径 rPick, PCD 半径, 孔数, 孔半径)"""
    rb = params.inner_d / 2.0
    r1 = (params.d1 or params.d * 0.85) / 2.0
    r_pick = (rb + r1) / 2.0  # 密封面顶环形区域中点（BL 为圆心到密封面中点）
    return r_pick, params.k / 2.0, params.n, params.l / 2.0


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
# 特征创建 ── 法兰盘建模步骤（4 类通用）
# ═══════════════════════════════════════════════════════════════


def create_flange_solid(part, params: FlangeParams) -> bool:
    """
    创建法兰实体（plate / slip_on / weld_neck / blind 通用）

    步骤:
      1. 半剖面轮廓 + 轴心线 → 旋转凸台（法兰主体 + RF 密封面 + 颈部）
      2. 密封面顶选面 → n 个螺栓孔草图（均布 PCD）→ 切除

    Args:
        part: SolidWorks Part 对象
        params: 法兰参数

    Returns:
        True 表示成功
    """
    pts = _flange_profile(params)
    r_pick, k_r, n_bolts, bolt_r = _bolt_hole_geometry(params)

    m = 1000.0  # mm → m
    sk = part.SketchManager
    fm = part.FeatureManager

    try:
        # ═══ Step 1: 旋转主体（实测配方：轴心线对象引用 + mark=1 + 8 参数 FeatureRevolve） ═══
        sk.InsertSketch(True)
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            part.CreateLine2(x1 / m, y1 / m, 0.0, x2 / m, y2 / m, 0.0)
        y_min = min(p[1] for p in pts)
        seg_axis = part.CreateLine2(0.0, 0.02, 0.0, 0.0, (y_min - 20.0) / m, 0.0)
        seg_axis.ConstructionGeometry = True
        sk.InsertSketch(True)
        part.ClearSelection2(True)
        seg_axis.Select2(True, 1)

        feat_revolve = fm.FeatureRevolve(
            6.2831853071796, False, 0, 0, 0, True, True, True
        )
        if feat_revolve is None:
            print("[SW Generator] 旋转特征创建失败")
            return False

        # ═══ Step 2: 螺栓孔（上视基准面草图 → 26 参数 FeatureCut3 ThroughAll，实测配方） ═══
        if n_bolts > 0 and bolt_r > 0:
            part.ClearSelection2(True)
            plane2 = _find_second_ref_plane(part)
            if plane2 is None or not plane2.Select2(False, 0):
                print("[SW Generator] 螺栓孔草图基准面选择失败")
                return False

            sk.InsertSketch(True)
            import math
            for i in range(n_bolts):
                th = 2.0 * math.pi * i / n_bolts
                cx = k_r / m * math.cos(th)
                cy = k_r / m * math.sin(th)
                sk.CreateCircle(cx, cy, 0.0, cx + bolt_r / m, cy, 0.0)
            sk.InsertSketch(True)

            cut = None
            try:
                cut = fm.FeatureCut3(
                    True, False, False, 1, 1, 0, 0, False, False, False, False,
                    0, 0, False, False, False, False, False, True, True, True, True,
                    False, 0, 0, False,
                )
            except Exception:
                cut = None
            if cut is None:
                try:
                    cut = fm.FeatureCut3(
                        True, False, False, 0, 0, 0.06, 0.06, False, False,
                        False, False, 0, 0, False, False, False, False, False,
                        True, True, True, True, False, 0, 0, False,
                    )
                except Exception:
                    cut = None
            if cut is None:
                print("[SW Generator] 螺栓孔切除失败")
                return False

        part.ClearSelection2(True)
        part.ViewZoomtofit2()
        return True

    except Exception as e:
        print(f"[SW Generator] 建模失败: {e}")
        return False


def _find_second_ref_plane(part):
    """遍历特征树返回第 2 个基准面（上视基准面，法向 = 法兰轴向）"""
    feat = part.FirstFeature
    idx = 0
    while feat is not None:
        if feat.GetTypeName2() == "RefPlane":
            idx += 1
            if idx == 2:
                return feat
        feat = feat.GetNextFeature()
    return None


def generate_flange(params: FlangeParams, output_path: Optional[str] = None) -> str:
    """
    生成法兰盘模型（pywin32 COM 直连 SolidWorks）

    Args:
        params: 法兰参数
        output_path: 保存路径 (.SLDPRT)，默认自动生成

    Returns:
        模型保存路径
    """
    session = connect_sw(visible=True)

    try:
        if not create_flange_solid(session.part, params):
            raise RuntimeError("法兰建模失败，详见控制台输出")

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
# VBA 宏生成（跨平台 / 生产主路径：C# 插件 RunMacro 执行）
# ═══════════════════════════════════════════════════════════════


def generate_sw_macro(params: FlangeParams) -> str:
    """
    生成 SolidWorks VBA 宏代码（4 类法兰通用）

    可以直接在 SolidWorks 中运行（工具 → 宏 → 运行）

    Returns:
        VBA 宏代码字符串
    """
    import math

    pts = _flange_profile(params)
    r_pick, k_r, n_bolts, bolt_r = _bolt_hole_geometry(params)

    t = params.flange_type
    type_names = {
        FlangeType.PLATE: "板式平焊",
        FlangeType.SLIP_ON: "带颈平焊",
        FlangeType.WELD_NECK: "对焊",
        FlangeType.BLIND: "法兰盖",
    }

    m = 1000.0

    def d(v: float) -> str:
        """mm → m 的 VBA Double 字面量"""
        return f"{v / m:.6f}#"

    # 轮廓线段（含闭合边）
    y_min = min(p[1] for p in pts)
    lines = []
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        lines.append(
            f"    Part.CreateLine2 {d(x1)}, {d(y1)}, 0#, {d(x2)}, {d(y2)}, 0#"
        )

    # 螺栓孔圆（VB 数组预计算，避免循环内三角函数的精度差异）
    bolt_lines = []
    for i in range(n_bolts):
        th = 2.0 * math.pi * i / n_bolts
        cx = k_r * math.cos(th)
        cy = k_r * math.sin(th)
        bolt_lines.append(
            f"        skMgr.CreateCircle {d(cx)}, {d(cy)}, 0#, {d(cx + bolt_r)}, {d(cy)}, 0#"
        )

    neck_comment = ""
    if t == FlangeType.WELD_NECK:
        neck_comment = (
            f"    ' 颈部: 根径 N={params.neck_d} → 小端 A1={params.neck_tip_d}，"
            f"锥颈+直段 H1={params.neck_straight_h}，总长 {params.neck_h}\n"
        )
    elif t == FlangeType.SLIP_ON:
        neck_comment = f"    ' 颈部: 直颈 N={params.neck_d}，长 {params.neck_h}\n"

    macro = f"""' SolidWorks 宏 — 参数化法兰 DN{params.dn} PN{params.pn} {type_names.get(t, t.value)}
' 标准 {params.standard} | 自动生成 by sw-ai
' 在 SW 中: 工具 → 宏 → 运行

Dim swApp As Object
Dim Part As Object
Dim skMgr As Object
Dim featMgr As Object

Sub main()
    Set swApp = Application.SldWorks
    Set Part = swApp.NewDocument("", 0, 0, 0)
    swApp.Visible = True
    Set skMgr = Part.SketchManager
    Set featMgr = Part.FeatureManager

    ' === 1. 半剖面轮廓 + 轴心线 → 旋转成型 ===
    ' X=半径 Y=轴向（密封面顶 y=0），法兰总高 {f'{-y_min:.1f}'}mm
{neck_comment}    skMgr.InsertSketch True
{chr(10).join(lines)}
    ' 轴心线（X=0，超出轮廓两端）— 对象引用 + mark=1 选择 + 8 参数 FeatureRevolve（实测配方）
    Dim segAxis As Object
    Set segAxis = Part.CreateLine2(0#, 0.02#, 0#, 0#, {d(y_min - 20.0)}, 0#)
    segAxis.ConstructionGeometry = True
    skMgr.InsertSketch True
    Part.ClearSelection2 True
    segAxis.Select2 True, 1
    Dim revFeat As Object
    Set revFeat = featMgr.FeatureRevolve(6.2831853071796, False, 0, 0, 0, True, True, True)
    If revFeat Is Nothing Then
        MsgBox "旋转特征创建失败", vbCritical, "sw-ai"
        Exit Sub
    End If

    ' === 2. 螺栓孔 {n_bolts}×ø{params.l} PCD={params.k} ===
    ' 上视基准面（特征树第 2 个基准面）画孔圆 → ThroughAll 切除（实测配方）
    Dim feat0 As Object
    Dim idx As Integer
    Set feat0 = Part.FirstFeature
    idx = 0
    Do While Not feat0 Is Nothing
        If feat0.GetTypeName2 = "RefPlane" Then
            idx = idx + 1
            If idx = 2 Then Exit Do
        End If
        Set feat0 = feat0.GetNextFeature
    Loop
    If feat0 Is Nothing Then
        MsgBox "未找到上视基准面", vbCritical, "sw-ai"
        Exit Sub
    End If
    feat0.Select2 False, 0
    skMgr.InsertSketch True
{chr(10).join(bolt_lines)}
    skMgr.InsertSketch True

    Dim cutFeat As Object
    Set cutFeat = Nothing
    On Error Resume Next
    Set cutFeat = featMgr.FeatureCut3(True, False, False, 1, 1, 0#, 0#, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)
    If cutFeat Is Nothing Then
        Err.Clear
        Set cutFeat = featMgr.FeatureCut3(True, False, False, 0, 0, 0.06#, 0.06#, False, False, False, False, 0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0, False)
    End If
    On Error Goto 0

    If cutFeat Is Nothing Then
        MsgBox "螺栓孔切除失败", vbCritical, "sw-ai"
    Else
        Part.ViewZoomtofit2
        MsgBox "{type_names.get(t, t.value)}法兰 DN{params.dn} PN{params.pn} 生成完成", vbInformation, "sw-ai"
    End If
End Sub
"""
    return macro
