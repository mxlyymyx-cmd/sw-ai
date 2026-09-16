#!/usr/bin/env python3
"""
SWAI API Server — Flask 包装现有设计引擎

插件开发调试时可通过浏览器访问 API。
生产环境：插件通过 localhost:5757 调用。

启动:
    python api.py
"""

import os
import sys
import json
import logging
import traceback
from typing import Optional

# 确保可以导入本包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from flask_cors import CORS

# ── 设计引擎导入 ──
from flange.params import FlangeParams, FlangeType, SealType
from flange.gb_standards import lookup, list_available, is_supported
from flange.ai_extractor import extract as flange_extract
from flange.generator import generate_sw_macro as gen_flange_macro

from impeller.params import ImpellerDesignInput, BladeType
from impeller.design import design_impeller as design_impeller_engine
from impeller.generator import (
    generate_vba_macro as gen_impeller_macro,
    design_and_generate as impeller_design_and_generate,
)
from impeller.volute import match_impeller, volute_profile

from axial.params import AxialFanInput, AirfoilType
from axial.design import design_axial_fan as design_axial_engine
from axial.generator import (
    generate_vba_macro as gen_axial_macro,
    design_and_generate as axial_design_and_generate,
)

# ── AI 聊天引擎 ──
from ai_chat import chat as ai_chat, is_llm_configured, get_llm_settings

# ── 选型 + 性能曲线 ──
from fan_selector import select_fan
from perf import perf_curve

# ═══════════════════════════════════════════════════════════════
# Flask App
# ═══════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)  # 跨域支持

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("swai")


# ═══════════════════════════════════════════════════════════════
# 通用响应格式
# ═══════════════════════════════════════════════════════════════


def ok(data: dict, status: int = 200):
    """成功响应"""
    return jsonify({"success": True, "data": data}), status


def fail(error: str, code: str = "ERROR", status: int = 400):
    """错误响应"""
    return jsonify({"success": False, "error": error, "code": code}), status


def server_error(e: Exception):
    """服务器内部错误"""
    log.error(f"Internal error: {e}\n{traceback.format_exc()}")
    return jsonify({
        "success": False,
        "error": str(e),
        "code": "INTERNAL_ERROR",
    }), 500


# ═══════════════════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════════════════


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    log.info("GET /api/health")
    return ok({
        "status": "ok",
        "version": "1.1.0",
        "engines": ["flange", "impeller", "axial", "select", "curve"],
    })


@app.route("/api/models", methods=["GET"])
def list_models():
    """列出支持的零件类型和参数说明"""
    log.info("GET /api/models")
    return ok({
        "models": [
            {
                "id": "flange",
                "name": "法兰盘",
                "description": "板式平焊/带颈平焊/对焊法兰，国标GB/T 911X-2010系列",
                "params": {
                    "dn": {"type": "int", "required": True, "description": "公称通径 (DN10~DN300)"},
                    "pn": {"type": "int", "required": True, "description": "公称压力 (PN10, PN16, PN25, PN40)"},
                    "flange_type": {"type": "str", "default": "plate", "choices": ["plate", "slip_on", "weld_neck", "blind"]},
                    "seal_type": {"type": "str", "default": "rf", "choices": ["rf", "mfm", "tg"]},
                    "material": {"type": "str", "default": "Q235B"},
                    "n": {"type": "int", "default": 0, "description": "螺栓孔数量（0=自动）"},
                },
            },
            {
                "id": "impeller",
                "name": "离心风机叶轮",
                "description": "前向/后向/径向离心风机叶轮设计，含蜗壳匹配",
                "params": {
                    "Q": {"type": "float", "required": True, "description": "流量 (m³/h)"},
                    "P": {"type": "float", "required": True, "description": "全压 (Pa)"},
                    "n": {"type": "float", "default": 0, "description": "转速 (r/min，缺省=自动选型推荐)"},
                    "blade_type": {"type": "str", "default": "backward", "choices": ["forward", "backward", "radial", "radial_tip", "airfoil"]},
                    "material": {"type": "str", "default": "Q235B"},
                    "volute": {"type": "bool", "default": True, "description": "是否包含蜗壳设计"},
                },
            },
            {
                "id": "axial",
                "name": "轴流风机",
                "description": "轴流风机叶轮设计，支持多种翼型",
                "params": {
                    "Q": {"type": "float", "required": True, "description": "流量 (m³/h)"},
                    "P": {"type": "float", "required": True, "description": "全压 (Pa)"},
                    "n": {"type": "float", "default": 0, "description": "转速 (r/min，缺省=自动选型推荐)"},
                    "airfoil": {"type": "str", "default": "clark_y", "choices": ["clark_y", "ls_0413", "ls_0409", "raf_30", "raf_38", "naca_4412", "naca_2412"]},
                    "material": {"type": "str", "default": "Q235B"},
                    "sections": {"type": "int", "default": 5},
                    "circulation": {"type": "str", "default": "equal", "choices": ["equal", "linear", "variable"]},
                    "nu": {"type": "float", "default": 0, "description": "轮毂比 ν（0=自动）"},
                },
            },
            {
                "id": "select",
                "name": "风机选型",
                "description": "给定 Q/P 自动比较离心与轴流方案，推荐机型和转速",
                "params": {
                    "Q": {"type": "float", "required": True, "description": "流量 (m³/h)"},
                    "P": {"type": "float", "required": True, "description": "全压 (Pa)"},
                    "prefer": {"type": "str", "default": "auto", "choices": ["auto", "centrifugal", "axial"]},
                },
            },
        ],
    })


# ═══════════════════════════════════════════════════════════════
# NLP — 自然语言 → 结构化参数
# ═══════════════════════════════════════════════════════════════


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    """
    AI 多轮对话 — 意图识别 + 参数提取 + 设计计算 + 生成宏

    请求体:
        {"messages": [{"role": "user", "content": "设计一台离心风机 Q=5000 P=2500 n=1450"}, ...]}

    返回:
        {"success": true, "data": {
            "reply": "...", "action": "build|ask|chat", "type": "...",
            "params": {...}, "summary": "...",
            "macro": "...", "name": "...",
            "extra_macro": "...", "extra_name": "...",
            "llm": true/false
        }}
    """
    data = request.get_json(force=True)
    messages = data.get("messages", [])

    if not messages:
        return fail("messages 不能为空", "EMPTY_INPUT")

    log.info(f"POST /api/chat  msgs={len(messages)}  last={messages[-1].get('content', '')[:80]}")

    try:
        result = ai_chat(messages)
        return ok(result)
    except Exception as e:
        return server_error(e)


@app.route("/api/chat/config", methods=["GET"])
def chat_config():
    """查询 LLM 配置状态（不返回 key 本身）"""
    settings = get_llm_settings()
    return ok({
        "configured": bool(settings["api_key"]),
        "model": settings["model"],
        "api_url": settings["api_url"],
    })


@app.route("/api/nlp", methods=["POST"])
def nlp_parse():
    """
    自然语言解析

    请求体:
        {"text": "DN100 PN16 平焊法兰"}
        {"text": "设计一个离心风机，流量5000m³/h，全压2500Pa，转速1450rpm"}
        {"text": "轴流风机 Q=20000 P=800 n=1450"}

    返回:
        {"success": true, "data": {"type": "flange|impeller|axial", "params": {...}}}
    """
    data = request.get_json(force=True)
    text = data.get("text", "").strip()

    if not text:
        return fail("输入文本不能为空", "EMPTY_INPUT")

    log.info(f"POST /api/nlp  text={text[:100]}")

    # 尝试识别类型
    text_lower = text.lower()

    # 离心风机关键字
    is_impeller = any(kw in text_lower for kw in [
        "离心风机", "叶轮", "fan", "impeller", "离心", "蜗壳",
    ])
    # 轴流风机关键字
    is_axial = any(kw in text_lower for kw in [
        "轴流", "axial", "轴流风机",
    ])
    # 默认视为法兰
    is_flange = not is_impeller and not is_axial

    try:
        if is_axial:
            # 轴流风机 — 用正则提取 Q, P, n
            params = _extract_fan_params(text)
            params["type"] = "axial"
            return ok({
                "type": "axial",
                "params": params,
                "confidence": 0.85,
            })
        elif is_impeller:
            # 离心风机
            params = _extract_fan_params(text)
            params["type"] = "impeller"
            return ok({
                "type": "impeller",
                "params": params,
                "confidence": 0.85,
            })
        else:
            # 法兰 — 用现有 AI 提取器
            result = flange_extract(text)
            if not result.success:
                return fail(result.error, "EXTRACTION_FAILED", 400)

            return ok({
                "type": "flange",
                "params": result.params.to_dict(),
                "confidence": result.confidence,
                "notes": result.notes,
            })
    except Exception as e:
        return server_error(e)


def _extract_fan_params(text: str) -> dict:
    """
    从自然语言提取风机参数 Q, P, n

    支持格式:
        - Q=5000 P=2500 n=1450
        - 流量5000m³/h 全压2500Pa 转速1450rpm
        - 5000 m3h 2500 Pa 1450 rpm
    """
    import re

    params = {}
    patterns = [
        # key=value 格式
        (r'(?:Q|q|流量)\s*[:=]?\s*(\d+[\.\d]*)', 'Q'),
        (r'(?:P|p|全压)\s*[:=]?\s*(\d+[\.\d]*)', 'P'),
        (r'(?:n|转速|rpm)\s*[:=]?\s*(\d+[\.\d]*)', 'n'),
        # 无 key 纯数字（按 Q,P,n 顺序猜测）
    ]

    for pattern, key in patterns:
        m = re.search(pattern, text)
        if m:
            params[key] = float(m.group(1))

    # 类型
    type_match = re.search(r'(前向|forward)', text, re.IGNORECASE)
    if type_match:
        params["blade_type"] = "forward"
    type_match = re.search(r'(后向|backward)', text, re.IGNORECASE)
    if type_match:
        params["blade_type"] = "backward"
    type_match = re.search(r'(径向|radial)', text, re.IGNORECASE)
    if type_match:
        params["blade_type"] = "radial"

    # 翼型
    airfoil_match = re.search(r'(clark.y|clark_y)', text, re.IGNORECASE)
    if airfoil_match:
        params["airfoil"] = "clark_y"

    return params


# ═══════════════════════════════════════════════════════════════
# 法兰设计
# ═══════════════════════════════════════════════════════════════


@app.route("/api/design/flange", methods=["POST"])
def design_flange():
    """
    法兰设计计算

    请求体:
        {"dn": 100, "pn": 16, "flange_type": "plate", "material": "Q235B", "seal_type": "rf"}

    返回:
        {"success": true, "data": {
            "params": {...},
            "summary": "...",
            "bolt_hole_pattern": {...},
            "standard": "GB/T 9119-2010"
        }}
    """
    data = request.get_json(force=True)
    log.info(f"POST /api/design/flange  data={data}")

    try:
        dn = int(data.get("dn", 0))
        pn = int(data.get("pn", 0))

        if dn <= 0 or pn <= 0:
            return fail("DN 和 PN 必须为正整数", "INVALID_PARAMS")

        # 查国标（按类型返回对应尺寸，含带颈法兰颈部数据）
        if is_supported(dn, pn):
            params = lookup(dn, pn, data.get("flange_type", "plate"))
        else:
            return fail(f"DN{dn} PN{pn} 不在国标数据库中", "NOT_SUPPORTED")

        # 覆盖用户参数
        if data.get("seal_type"):
            params.seal_type = SealType(data["seal_type"])
        if data.get("material"):
            params.material = data["material"]
        if data.get("n"):
            params.n = int(data["n"])

        return ok({
            "params": params.to_dict(),
            "summary": params.summary,
            "bolt_hole_pattern": params.bolt_hole_pattern,
            "standard": params.standard,
        })
    except ValueError as e:
        return fail(str(e), "INVALID_PARAMS")
    except Exception as e:
        return server_error(e)


# ═══════════════════════════════════════════════════════════════
# 离心风机叶轮设计
# ═══════════════════════════════════════════════════════════════


@app.route("/api/design/impeller", methods=["POST"])
def design_impeller():
    """
    离心风机叶轮设计

    请求体:
        {"Q": 5000, "P": 2500, "n": 1450, "blade_type": "backward", "material": "Q235B", "volute": true}

    返回:
        {"success": true, "data": {
            "design": {...},
            "summary": "...",
            "volute": {...} | null
        }}
    """
    data = request.get_json(force=True)
    log.info(f"POST /api/design/impeller  data={data}")

    try:
        Q = float(data.get("Q", 0))
        P = float(data.get("P", 0))
        n = float(data.get("n", 0))

        if Q <= 0 or P <= 0:
            return fail("Q, P 必须为正数", "INVALID_PARAMS")

        # 转速缺省 → 自动选型推荐
        auto_note = ""
        if n <= 0:
            try:
                sel = select_fan(Q=Q, P=P, prefer="centrifugal")
            except ValueError as e:
                return fail(str(e), "DESIGN_ERROR")
            if sel.best is None:
                return fail(f"Q={Q:.0f} P={P:.0f} 无可行离心方案，请指定转速或改用轴流", "NO_SOLUTION")
            n = sel.best.n
            auto_note = f"转速自动选型 → {n:.0f} r/min（n_s={sel.best.ns:.1f}）"

        blade_type = data.get("blade_type", "backward")
        material = data.get("material", "Q235B")

        inp = ImpellerDesignInput(
            Q=Q, P=P, n=n,
            blade_type=blade_type,
            material=material,
        )
        design = design_impeller_engine(inp)

        result = {
            "design": design.to_dict(),
            "summary": (auto_note + "\n\n" if auto_note else "") + design.summary,
            "auto_speed": bool(auto_note),
            "volute": None,
        }

        # 蜗壳匹配
        if data.get("volute", True):
            try:
                vol = match_impeller(design)
                profile = volute_profile(vol)
                result["volute"] = {
                    "params": {
                        "D2": vol.D2, "b2": vol.b2, "B": vol.B, "A": vol.A,
                        "delta": vol.delta, "r_tongue": vol.r_tongue,
                        "outlet_w": vol.outlet_w, "outlet_h": vol.outlet_h,
                        "outlet_v": vol.outlet_v,
                    },
                    "summary": vol.summary,
                    "profile_points": profile[:10],  # 只返回前10个点示意
                }
            except Exception as ve:
                result["volute"] = {"error": str(ve)}

        return ok(result)

    except ValueError as e:
        return fail(str(e), "DESIGN_ERROR")
    except Exception as e:
        return server_error(e)


# ═══════════════════════════════════════════════════════════════
# 轴流风机设计
# ═══════════════════════════════════════════════════════════════


@app.route("/api/design/axial", methods=["POST"])
def design_axial():
    """
    轴流风机设计

    请求体:
        {"Q": 20000, "P": 800, "n": 1450, "airfoil": "clark_y", "material": "Q235B", "sections": 5}

    返回:
        {"success": true, "data": {
            "design": {...},
            "summary": "...",
            "sections": [...]
        }}
    """
    data = request.get_json(force=True)
    log.info(f"POST /api/design/axial  data={data}")

    try:
        Q = float(data.get("Q", 0))
        P = float(data.get("P", 0))
        n = float(data.get("n", 0))

        if Q <= 0 or P <= 0:
            return fail("Q, P 必须为正数", "INVALID_PARAMS")

        # 转速缺省 → 自动选型推荐
        auto_note = ""
        if n <= 0:
            try:
                sel = select_fan(Q=Q, P=P, prefer="axial")
            except ValueError as e:
                return fail(str(e), "DESIGN_ERROR")
            if sel.best is None:
                return fail(f"Q={Q:.0f} P={P:.0f} 无可行轴流方案，请指定转速或改用离心", "NO_SOLUTION")
            n = sel.best.n
            auto_note = f"转速自动选型 → {n:.0f} r/min（n_s={sel.best.ns:.1f}）"

        airfoil = data.get("airfoil", "clark_y")
        material = data.get("material", "Q235B")
        sections = int(data.get("sections", 5))
        circulation = data.get("circulation", "equal")
        nu = float(data.get("nu", 0))

        inp = AxialFanInput(
            Q=Q, P=P, n=n,
            airfoil=airfoil,
            material=material,
            sections=sections,
            circulation=circulation,
            nu=nu,
        )
        design = design_axial_engine(inp)

        result = {
            "design": design.to_dict(),
            "summary": (auto_note + "\n\n" if auto_note else "") + design.summary,
            "auto_speed": bool(auto_note),
            "sections": [s.to_dict() for s in design.sections],
        }

        return ok(result)

    except ValueError as e:
        return fail(str(e), "DESIGN_ERROR")
    except Exception as e:
        return server_error(e)


# ═══════════════════════════════════════════════════════════════
# 风机选型
# ═══════════════════════════════════════════════════════════════


@app.route("/api/design/select", methods=["POST"])
def design_select():
    """
    风机选型：自动比较离心/轴流 + 标准转速，推荐最优方案

    请求体:
        {"Q": 20000, "P": 800, "prefer": "auto"}

    返回:
        {"success": true, "data": {
            "Q": ..., "P": ...,
            "best": {"machine": "centrifugal|axial", "n": ..., "ns": ...},
            "candidates": [...],
            "summary": "..."
        }}
    """
    data = request.get_json(force=True)
    log.info(f"POST /api/design/select  data={data}")

    try:
        Q = float(data.get("Q", 0))
        P = float(data.get("P", 0))
        prefer = data.get("prefer", "auto")

        if Q <= 0 or P <= 0:
            return fail("Q, P 必须为正数", "INVALID_PARAMS")

        sel = select_fan(Q=Q, P=P, prefer=prefer)

        return ok({
            "Q": Q,
            "P": P,
            "prefer": prefer,
            "best": None if sel.best is None else {
                "machine": sel.best.machine,
                "machine_name": sel.best.machine_name,
                "n": sel.best.n,
                "ns": sel.best.ns,
                "score": sel.best.score,
                "design": sel.best.design.to_dict(),
            },
            "candidates": [
                {
                    "machine": c.machine,
                    "machine_name": c.machine_name,
                    "n": c.n,
                    "ns": c.ns,
                    "score": c.score,
                }
                for c in sel.candidates
            ],
            "summary": sel.summary,
        })

    except ValueError as e:
        return fail(str(e), "DESIGN_ERROR")
    except Exception as e:
        return server_error(e)


# ═══════════════════════════════════════════════════════════════
# 性能曲线
# ═══════════════════════════════════════════════════════════════


@app.route("/api/design/curve", methods=["POST"])
def design_curve():
    """
    生成整机性能曲线（P-Q + η-Q + N-Q）

    请求体:
        {"type": "impeller|axial", "Q": 5000, "P": 2500, "n": 1450}   # n 缺省自动选型

    返回:
        {"success": true, "data": {
            "machine": "...", "n": ..., "Q_d": ..., "P_d": ..., "eta_d": ..., "N_d": ...,
            "Q_stall": ...,
            "points": [{"Q": ..., "P": ..., "eta": ..., "N": ...}, ...]
        }}
    """
    data = request.get_json(force=True)
    log.info(f"POST /api/design/curve  data={data}")

    try:
        machine = data.get("type", "")
        Q = float(data.get("Q", 0))
        P = float(data.get("P", 0))
        n = float(data.get("n", 0))

        if Q <= 0 or P <= 0:
            return fail("Q, P 必须为正数", "INVALID_PARAMS")

        if machine == "impeller":
            prefer = "centrifugal"
        elif machine == "axial":
            prefer = "axial"
        else:
            return fail("type 必须为 impeller 或 axial", "INVALID_PARAMS")

        # 转速缺省 → 自动选型
        if n <= 0:
            try:
                sel = select_fan(Q=Q, P=P, prefer=prefer)
            except ValueError as e:
                return fail(str(e), "DESIGN_ERROR")
            if sel.best is None:
                return fail("无可行方案，请指定转速", "NO_SOLUTION")
            n = sel.best.n

        if machine == "impeller":
            inp = ImpellerDesignInput(Q=Q, P=P, n=n, blade_type=data.get("blade_type", "backward"))
            design = design_impeller_engine(inp)
        else:
            inp = AxialFanInput(Q=Q, P=P, n=n, airfoil=data.get("airfoil", "clark_y"))
            design = design_axial_engine(inp)

        curve = perf_curve(design)

        return ok({
            "machine": curve.machine,
            "n": curve.n,
            "Q_d": curve.Q_d,
            "P_d": curve.P_d,
            "eta_d": curve.eta_d,
            "N_d": curve.N_d,
            "Q_stall": curve.Q_stall,
            "points": [p.to_dict() for p in curve.points],
        })

    except ValueError as e:
        return fail(str(e), "DESIGN_ERROR")
    except Exception as e:
        return server_error(e)


# ═══════════════════════════════════════════════════════════════
# VBA 宏代码生成
# ═══════════════════════════════════════════════════════════════


# In-memory task store
_macro_tasks: dict = {}
_next_task_id: int = 0


@app.route("/api/macro", methods=["POST"])
def generate_macro():
    """
    生成 VBA 宏代码

    请求体:
        {"type": "flange", "params": {"dn": 100, "pn": 16, ...}}
        {"type": "impeller", "params": {"Q": 5000, "P": 2500, "n": 1450, ...}}
        {"type": "axial", "params": {"Q": 20000, "P": 800, "n": 1450, ...}}

    返回:
        {"success": true, "data": {"task_id": "1", "macro": "...", "name": "...", "lines": 123}}
    """
    global _next_task_id

    data = request.get_json(force=True)
    log.info(f"POST /api/macro  type={data.get('type')}")

    try:
        macro_type = data.get("type", "")
        params = data.get("params", {})

        if macro_type == "flange":
            dn = int(params.get("dn", 0))
            pn = int(params.get("pn", 0))
            if dn <= 0 or pn <= 0:
                return fail("法兰需要 dn 和 pn 参数", "INVALID_PARAMS")

            if is_supported(dn, pn):
                fp = lookup(dn, pn, params.get("flange_type", "plate"))
            else:
                return fail(f"DN{dn} PN{pn} 不在数据库中", "NOT_SUPPORTED")

            if params.get("material"):
                fp.material = params["material"]

            macro = gen_flange_macro(fp)
            name = f"Flange_DN{dn}_PN{pn}_{fp.flange_type.value}"

        elif macro_type == "impeller":
            Q = float(params.get("Q", 0))
            P = float(params.get("P", 0))
            n = float(params.get("n", 0))
            if Q <= 0 or P <= 0:
                return fail("叶轮需要 Q, P 参数（n 可缺省自动选型）", "INVALID_PARAMS")

            # 转速缺省 → 自动选型推荐
            if n <= 0:
                try:
                    sel = select_fan(Q=Q, P=P, prefer="centrifugal")
                except ValueError as e:
                    return fail(str(e), "DESIGN_ERROR")
                if sel.best is None:
                    return fail(f"Q={Q:.0f} P={P:.0f} 无可行离心方案，请指定转速", "NO_SOLUTION")
                n = sel.best.n

            blade_type = params.get("blade_type", "backward")
            material = params.get("material", "Q235B")
            inp = ImpellerDesignInput(Q=Q, P=P, n=n, blade_type=blade_type, material=material)
            design = design_impeller_engine(inp)
            macro = gen_impeller_macro(design)
            name = f"Impeller_Q{Q:.0f}_P{P:.0f}_n{n:.0f}"

            # 如需蜗壳宏，可额外生成
            volute_macro = None
            if params.get("volute", True):
                try:
                    vol = match_impeller(design)
                    profile = volute_profile(vol)
                    from impeller.volute import generate_vba_macro as gen_vol_macro
                    volute_macro = gen_vol_macro(vol, profile)
                except Exception:
                    volute_macro = None

        elif macro_type == "axial":
            Q = float(params.get("Q", 0))
            P = float(params.get("P", 0))
            n = float(params.get("n", 0))
            if Q <= 0 or P <= 0:
                return fail("轴流风机需要 Q, P 参数（n 可缺省自动选型）", "INVALID_PARAMS")

            # 转速缺省 → 自动选型推荐
            if n <= 0:
                try:
                    sel = select_fan(Q=Q, P=P, prefer="axial")
                except ValueError as e:
                    return fail(str(e), "DESIGN_ERROR")
                if sel.best is None:
                    return fail(f"Q={Q:.0f} P={P:.0f} 无可行轴流方案，请指定转速", "NO_SOLUTION")
                n = sel.best.n

            airfoil = params.get("airfoil", "clark_y")
            material = params.get("material", "Q235B")
            sections = int(params.get("sections", 5))
            circulation = params.get("circulation", "equal")
            nu = float(params.get("nu", 0))
            inp = AxialFanInput(Q=Q, P=P, n=n, airfoil=airfoil, material=material,
                                sections=sections, circulation=circulation, nu=nu)
            design = design_axial_engine(inp)
            macro = gen_axial_macro(design)
            name = f"Axial_Q{Q:.0f}_P{P:.0f}_n{n:.0f}"

        else:
            return fail(f"不支持的零件类型: {macro_type}", "UNSUPPORTED_TYPE")

        _next_task_id += 1
        task_id = str(_next_task_id)
        _macro_tasks[task_id] = {
            "name": name,
            "macro": macro,
            "type": macro_type,
        }

        resp_data = {
            "task_id": task_id,
            "name": name,
            "macro": macro,
            "lines": macro.count("\n") + 1,
        }

        # 附带蜗壳宏
        if macro_type == "impeller" and volute_macro:
            _next_task_id += 1
            vol_task_id = str(_next_task_id)
            vol_name = f"{name}_volute"
            _macro_tasks[vol_task_id] = {
                "name": vol_name,
                "macro": volute_macro,
                "type": "volute",
            }
            resp_data["volute_task_id"] = vol_task_id
            resp_data["volute_name"] = vol_name
            resp_data["volute_lines"] = volute_macro.count("\n") + 1

        return ok(resp_data)

    except ValueError as e:
        return fail(str(e), "INVALID_PARAMS")
    except Exception as e:
        return server_error(e)


@app.route("/api/macro/<task_id>", methods=["GET"])
def get_macro(task_id: str):
    """查看生成的宏"""
    task = _macro_tasks.get(task_id)
    if not task:
        return fail(f"任务 {task_id} 不存在", "NOT_FOUND", 404)

    return ok({
        "task_id": task_id,
        "name": task["name"],
        "type": task["type"],
        "macro": task["macro"],
        "lines": task["macro"].count("\n") + 1,
    })


# ═══════════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SWAI API Server")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址 (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5757, help="监听端口 (default: 5757)")
    parser.add_argument("--debug", action="store_true", help="Debug 模式")
    args = parser.parse_args()

    print(f"""
{'='*55}
  SWAI API Server 🏭
  {'='*55}

  API Base:  http://{args.host}:{args.port}/api

  Endpoints:
    GET  /api/health          — 健康检查
    GET  /api/models          — 支持的零件类型
    POST /api/chat            — AI 多轮对话（意图→设计→宏）
    GET  /api/chat/config     — LLM 配置状态
    POST /api/nlp             — 自然语言 → 结构化参数
    POST /api/design/flange   — 法兰设计计算
    POST /api/design/impeller — 离心风机叶轮设计（n 可缺省）
    POST /api/design/axial    — 轴流风机设计（n 可缺省）
    POST /api/design/select   — 风机选型（离心 vs 轴流 + 转速推荐）
    POST /api/design/curve    — 性能曲线（P-Q + η-Q + 失速边界）
    POST /api/macro           — 生成 VBA 宏代码
    GET  /api/macro/<id>      — 查看生成的宏

  Press Ctrl+C to stop.
{'='*55}
""")

    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=False,  # 避免热重载打扰 SolidWorks 插件
    )


if __name__ == "__main__":
    main()
