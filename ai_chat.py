#!/usr/bin/env python3
"""
SWAI AI 聊天引擎
=====================
真正的多轮对话能力：
- 用户说需求 → LLM 意图识别 + 参数提取（一次调用）
- 参数齐全 → 调用设计引擎 → 生成宏 → 返回建模指令
- 参数缺失 → AI 追问
- 闲聊/设计咨询 → AI 直接回答

LLM 配置（优先级：环境变量 > config.json）：
    MECHFORGE_LLM_API_KEY  /  config.json  "llm_api_key"
    MECHFORGE_LLM_API_URL  /  config.json  "llm_api_url"   (默认 DeepSeek)
    MECHFORGE_LLM_MODEL    /  config.json  "llm_model"     (默认 deepseek-chat)

无 API Key 时自动降级为正则提取 + 模板回复（功能可用，但对话能力有限）。
"""

import json
import logging
import os
import re
import sys
from typing import Optional

# 确保可导入引擎包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flange.params import FlangeType, SealType
from flange.gb_standards import lookup, is_supported
from flange.generator import generate_sw_macro as gen_flange_macro
from flange.ai_extractor import extract as flange_extract

from impeller.params import ImpellerDesignInput
from impeller.design import design_impeller as design_impeller_engine
from impeller.generator import generate_vba_macro as gen_impeller_macro
from impeller.volute import match_impeller, volute_profile
from impeller.volute import generate_vba_macro as gen_volute_macro

from axial.params import AxialFanInput
from axial.design import design_axial_fan as design_axial_engine
from axial.generator import generate_vba_macro as gen_axial_macro

from fan_selector import select_fan

log = logging.getLogger("swai.chat")

# ═══════════════════════════════════════════════════════════════
# 配置管理
# ═══════════════════════════════════════════════════════════════

DEFAULT_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


def _config_path() -> str:
    """config.json 路径：%APPDATA%/SWAI/config.json（Windows），
    回退到脚本同目录 config.json。"""
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        path = os.path.join(appdata, "SWAI", "config.json")
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    return path


def _load_config() -> dict:
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def get_llm_settings() -> dict:
    """获取 LLM 配置（环境变量优先，其次 config.json）。"""
    cfg = _load_config()
    return {
        "api_key": os.environ.get("MECHFORGE_LLM_API_KEY") or cfg.get("llm_api_key", ""),
        "api_url": os.environ.get("MECHFORGE_LLM_API_URL") or cfg.get("llm_api_url", DEFAULT_API_URL),
        "model": os.environ.get("MECHFORGE_LLM_MODEL") or cfg.get("llm_model", DEFAULT_MODEL),
    }


def is_llm_configured() -> bool:
    return bool(get_llm_settings()["api_key"])


# ═══════════════════════════════════════════════════════════════
# LLM 客户端
# ═══════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """你是 SW-AI 机械设计 AI 助手，集成在 SolidWorks 插件中。你帮机械工程师把需求变成 3D 模型。

你可以设计以下零件（通过调用设计引擎完成精确计算）：
1. flange（法兰盘）：必填 dn(公称通径 mm)、pn(公称压力 bar)。可选 flange_type(plate板式平焊/slip_on带颈平焊/weld_neck对焊/blind盲板)、seal_type(rf突面/mfm凹凸面/tg榫槽面)、material(如 Q235B/304/316L/20#)、n(螺栓孔数量)。
2. impeller（离心风机叶轮）：必填 Q(流量 m³/h)、P(全压 Pa)。n(转速 r/min)可选——用户没给就不要追问，系统会自动选型推荐转速。可选 blade_type(backward后向/forward前向/radial径向/airfoil机翼型)、material、volute(是否含蜗壳,默认true)。
3. axial（轴流风机）：必填 Q、P。n 同上可选。可选 airfoil(clark_y/ls_0413/ls_0409/raf_30/raf_38/naca_4412/naca_2412)、material、sections、circulation(equal/linear/variable)、nu(轮毂比)。
4. select（风机选型）：用户说"设计一台风机/帮我选风机"且未指定离心或轴流时使用。必填 Q、P。n 可选。系统会自动比较离心/轴流方案并推荐最优。

## 你的行为规则
1. 用户给出设计需求 → 提取参数。必填参数齐全 → intent="design"，把参数填进 params（用户没给的 n 不要编造，直接省略）。
2. 必填参数不全 → intent="ask"，reply 用中文礼貌追问缺什么，missing 列出缺失参数名。
3. 纯闲聊或设计知识问答 → intent="chat"，用你的机械专业知识简短回答（中文，可给设计建议）。
4. 数值换算要细心：注意单位（如 5000m³/h、2500Pa、1450r/min；转速说 "2900转" 就是 n=2900）。
5. 用户没说的参数给默认值：材料 Q235B、叶型后向 backward、翼型 clark_y、法兰类型 plate、密封面 rf。
6. 用户没给转速 n 时：不要追问，intent 直接设为 "design" 且 params 不含 n，系统自动选型。

## 输出格式（严格只输出一个 JSON 对象，不要任何其他文字）
{"intent": "design|ask|chat", "type": "flange|impeller|axial|select", "params": {...}, "missing": [...], "reply": "你对用户说的话"}
"""


def call_llm(messages: list, settings: dict) -> Optional[str]:
    """调用 LLM，返回回复文本。失败返回 None。"""
    try:
        import requests
    except ImportError:
        log.warning("requests 未安装")
        return None

    if not settings.get("api_key"):
        return None

    headers = {
        "Authorization": f"Bearer {settings['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings["model"],
        "messages": [{"role": "system", "content": CHAT_SYSTEM_PROMPT}] + messages,
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    try:
        resp = requests.post(settings["api_url"], headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return content
    except Exception as e:
        log.error(f"LLM 调用失败: {e}")
        return None


def parse_llm_json(content: str) -> dict:
    """从 LLM 输出中提取 JSON 对象（容忍 markdown 代码块/前后杂质）。"""
    if not content:
        return {}
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    json_str = m.group(1) if m else content.strip()
    # 截取第一个 { 到最后一个 }
    s, e = json_str.find("{"), json_str.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return {}
    try:
        return json.loads(json_str[s:e + 1])
    except json.JSONDecodeError:
        log.error(f"JSON 解析失败: {json_str[s:e+1][:300]}")
        return {}


# ═══════════════════════════════════════════════════════════════
# 正则降级提取（无 LLM 时使用）
# ═══════════════════════════════════════════════════════════════

def _regex_intent(messages: list) -> dict:
    """正则模式：识别类型 + 提取参数。返回与 LLM 相同结构。"""
    text = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
    text_lower = text.lower()

    # 闲聊/知识问答检测
    if not any(kw in text for kw in ["设计", "画", "建模", "生成", "做个", "法兰", "风机", "叶轮",
                                     "dn", "pn", "流量", "全压", "转速"]):
        return {"intent": "chat", "type": "", "params": {}, "missing": [],
                "reply": "我是 SWAI 机械设计助手，可以帮你设计法兰、离心风机叶轮、轴流风机。"
                         "例如：\"设计一台离心风机 Q=5000 P=2500 n=1450\" 或 \"DN100 PN16 平焊法兰\"。"}

    is_axial = any(kw in text_lower for kw in ["轴流", "axial"])
    is_impeller = any(kw in text_lower for kw in ["离心", "叶轮", "impeller", "蜗壳"]) and not is_axial
    is_fan_generic = any(kw in text_lower for kw in ["风机", "选型", "fan"]) and not is_axial and not is_impeller
    is_flange = any(kw in text_lower for kw in ["法兰", "flange", "dn", "pn"]) or \
        (not is_axial and not is_impeller and not is_fan_generic)

    params = {}
    missing = []

    def _extract_num(pattern: str, key: str):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            params[key] = float(m.group(1))

    if is_flange:
        m = re.search(r"(?:DN|dn|公称通径)\s*[:=]?\s*(\d{2,4})", text)
        if m:
            params["dn"] = int(m.group(1))
        else:
            missing.append("dn")
        m = re.search(r"(?:PN|pn|公称压力)\s*[:=]?\s*(\d{1,3})", text)
        if m:
            params["pn"] = int(m.group(1))
        else:
            missing.append("pn")
        # 长词优先，避免"带颈平焊"被"平焊"抢先命中
        type_map = {"带颈对焊": "weld_neck", "对焊": "weld_neck",
                    "带颈平焊": "slip_on", "带颈": "slip_on",
                    "盲板": "blind", "法兰盖": "blind",
                    "平焊": "plate", "板式": "plate"}
        for kw, v in type_map.items():
            if kw in text:
                params["flange_type"] = v
                break
        return {"intent": "design" if not missing else "ask", "type": "flange",
                "params": params, "missing": missing,
                "reply": "请提供公称通径和压力，例如：DN100 PN16 平焊法兰" if missing else ""}
    else:
        # 风机类（impeller/axial/select）：n 可选，缺省自动选型
        _extract_num(r"(?:Q|q|流量)\s*[:=]?\s*(\d+[\.\d]*)", "Q")
        _extract_num(r"(?:P|p|全压|风压)\s*[:=]?\s*(\d+[\.\d]*)", "P")
        _extract_num(r"(?:n|转速|rpm|转)\s*[:=]?\s*(\d+[\.\d]*)", "n")
        for k in ("Q", "P"):
            if k not in params:
                missing.append(k)
        type_name = "axial" if is_axial else ("impeller" if is_impeller else "select")
        return {"intent": "design" if not missing else "ask", "type": type_name,
                "params": params, "missing": missing,
                "reply": "请提供流量 Q(m³/h) 和全压 P(Pa)，例如：Q=5000 P=2500（转速可不填，自动选型）" if missing else ""}


# ═══════════════════════════════════════════════════════════════
# 设计执行
# ═══════════════════════════════════════════════════════════════

def _auto_speed(part_type: str, Q: float, P: float):
    """转速缺省时自动选型。返回 (n, note) 或 (0, error)。"""
    prefer = "centrifugal" if part_type == "impeller" else "axial"
    try:
        sel = select_fan(Q=Q, P=P, prefer=prefer)
    except ValueError as e:
        return 0, f"选型失败: {e}"
    if sel.best is None:
        return 0, f"Q={Q:.0f}m³/h P={P:.0f}Pa 无可行{('离心' if part_type=='impeller' else '轴流')}方案，请指定转速或改换机型"
    n = sel.best.n
    note = f"⚙️ 转速自动选型 → {n:.0f} r/min（n_s={sel.best.ns:.1f}，共 {len(sel.candidates)} 个候选）"
    return n, note


def _design_and_macro(part_type: str, params: dict) -> dict:
    """
    执行设计计算 + 生成建模宏。
    返回 {"ok": bool, "error": str, "summary": str, "macro": str, "name": str,
          "extra_macro": str, "extra_name": str}
    """
    try:
        if part_type == "flange":
            dn = int(params.get("dn", 0))
            pn = int(params.get("pn", 0))
            if dn <= 0 or pn <= 0:
                return {"ok": False, "error": "法兰需要 DN 和 PN 参数"}
            if not is_supported(dn, pn):
                return {"ok": False, "error": f"DN{dn} PN{pn} 不在国标数据库中，支持范围见 /api/models"}
            fp = lookup(dn, pn, params.get("flange_type", "plate"))
            if params.get("seal_type"):
                fp.seal_type = SealType(params["seal_type"])
            if params.get("material"):
                fp.material = params["material"]
            if params.get("n"):
                fp.n = int(params["n"])
            macro = gen_flange_macro(fp)
            return {"ok": True, "summary": fp.summary,
                    "macro": macro, "name": f"Flange_DN{dn}_PN{pn}_{fp.flange_type.value}"}

        if part_type == "select":
            # 风机选型：自动比较离心/轴流，推荐最优方案后走对应引擎
            Q = float(params.get("Q", 0))
            P = float(params.get("P", 0))
            if Q <= 0 or P <= 0:
                return {"ok": False, "error": "风机选型需要 Q, P（且都为正数）"}
            try:
                sel = select_fan(Q=Q, P=P, prefer="auto")
            except ValueError as e:
                return {"ok": False, "error": f"选型失败: {e}"}
            if sel.best is None:
                return {"ok": False, "error": f"Q={Q:.0f}m³/h P={P:.0f}Pa 无可行方案，"
                                              f"请确认工况或指定机型（离心/轴流）"}
            best = sel.best
            sub_type = "impeller" if best.machine == "centrifugal" else "axial"
            sub_params = dict(params)
            sub_params["n"] = best.n
            result = _design_and_macro(sub_type, sub_params)
            if result.get("ok"):
                machine_name = "离心风机" if best.machine == "centrifugal" else "轴流风机"
                sel_note = (f"\n\n⚙️ 风机选型 → {machine_name} @ {best.n:.0f} r/min"
                            f"（n_s={best.ns:.1f}，候选 {len(sel.candidates)} 个）")
                result["summary"] = sel.summary + sel_note + "\n\n" + result["summary"]
                result["type"] = sub_type
            return result

        if part_type == "impeller":
            Q = float(params.get("Q", 0))
            P = float(params.get("P", 0))
            n = float(params.get("n", 0))
            if Q <= 0 or P <= 0:
                return {"ok": False, "error": "叶轮需要 Q, P（且都为正数）"}
            auto_note = ""
            if n <= 0:
                n, auto_note = _auto_speed("impeller", Q, P)
                if n <= 0:
                    return {"ok": False, "error": auto_note}
            blade_type = params.get("blade_type", "backward")
            material = params.get("material", "Q235B")
            inp = ImpellerDesignInput(Q=Q, P=P, n=n, blade_type=blade_type, material=material)
            design = design_impeller_engine(inp)
            macro = gen_impeller_macro(design)
            result = {"ok": True, "summary": (auto_note + "\n\n" if auto_note else "") + design.summary,
                      "macro": macro, "name": f"Impeller_Q{Q:.0f}_P{P:.0f}_n{n:.0f}"}
            # 蜗壳宏
            if params.get("volute", True):
                try:
                    vol = match_impeller(design)
                    profile = volute_profile(vol)
                    vm = gen_volute_macro(vol, profile)
                    result["extra_macro"] = vm
                    result["extra_name"] = result["name"] + "_volute"
                    result["summary"] += "\n\n" + vol.summary
                except Exception as e:
                    log.warning(f"蜗壳设计失败: {e}")
            return result

        if part_type == "axial":
            Q = float(params.get("Q", 0))
            P = float(params.get("P", 0))
            n = float(params.get("n", 0))
            if Q <= 0 or P <= 0:
                return {"ok": False, "error": "轴流风机需要 Q, P（且都为正数）"}
            auto_note = ""
            if n <= 0:
                n, auto_note = _auto_speed("axial", Q, P)
                if n <= 0:
                    return {"ok": False, "error": auto_note}
            airfoil = params.get("airfoil", "clark_y")
            material = params.get("material", "Q235B")
            sections = int(params.get("sections", 5))
            circulation = params.get("circulation", "equal")
            nu = float(params.get("nu", 0))
            inp = AxialFanInput(Q=Q, P=P, n=n, airfoil=airfoil, material=material,
                                sections=sections, circulation=circulation, nu=nu)
            design = design_axial_engine(inp)
            macro = gen_axial_macro(design)
            return {"ok": True, "summary": (auto_note + "\n\n" if auto_note else "") + design.summary,
                    "macro": macro, "name": f"Axial_Q{Q:.0f}_P{P:.0f}_n{n:.0f}"}

        return {"ok": False, "error": f"不支持的零件类型: {part_type}"}
    except Exception as e:
        log.error(f"设计执行失败: {e}")
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# 主入口：chat
# ═══════════════════════════════════════════════════════════════

def chat(messages: list, use_llm: bool = True) -> dict:
    """
    处理一轮对话。

    Args:
        messages: [{"role": "user|assistant", "content": "..."}, ...]
        use_llm: 是否尝试 LLM（False 强制正则模式）

    Returns:
        {"reply": str, "action": "build|ask|chat", "type": str,
         "params": dict, "summary": str, "macro": str, "name": str,
         "extra_macro": str, "extra_name": str, "llm": bool}
    """
    if not messages:
        return {"reply": "请描述你的设计需求。", "action": "chat", "type": "", "params": {},
                "summary": "", "macro": "", "name": "", "extra_macro": "", "extra_name": "", "llm": False}

    # ── 1. 意图识别 + 参数提取 ──
    intent = None
    params = {}
    part_type = ""
    missing = []
    llm_used = False

    settings = get_llm_settings()
    if use_llm and settings.get("api_key"):
        content = call_llm(messages, settings)
        if content:
            parsed = parse_llm_json(content)
            if parsed.get("intent"):
                intent = parsed
                llm_used = True

    if not intent:
        intent = _regex_intent(messages)

    reply = intent.get("reply", "")
    part_type = intent.get("type", "")
    params = intent.get("params", {}) or {}
    missing = intent.get("missing", []) or []
    intent_kind = intent.get("intent", "chat")

    # ── 2. 按意图处理 ──
    if intent_kind == "chat":
        return {"reply": reply or "我是 SWAI 机械设计助手，告诉我你的设计需求吧。",
                "action": "chat", "type": "", "params": {}, "summary": "",
                "macro": "", "name": "", "extra_macro": "", "extra_name": "", "llm": llm_used}

    if intent_kind == "ask" or missing:
        missing_names = {"dn": "公称通径 DN", "pn": "公称压力 PN", "Q": "流量 Q(m³/h)",
                         "P": "全压 P(Pa)", "n": "转速 n(r/min)"}
        ask_list = "、".join(missing_names.get(m, m) for m in missing)
        if not reply:
            reply = f"还缺几个参数：{ask_list}。请补充一下，我马上给你建模。"
        return {"reply": reply, "action": "ask", "type": part_type, "params": params,
                "summary": "", "macro": "", "name": "", "extra_macro": "", "extra_name": "", "llm": llm_used}

    # ── 3. intent == design：执行设计 ──
    result = _design_and_macro(part_type, params)
    if not result["ok"]:
        return {"reply": f"设计失败：{result['error']}", "action": "ask", "type": part_type,
                "params": params, "summary": "", "macro": "", "name": "",
                "extra_macro": "", "extra_name": "", "llm": llm_used}

    # 组装自然语言回复
    type_names = {"flange": "法兰", "impeller": "离心风机叶轮", "axial": "轴流风机", "select": "风机"}
    display_type = result.get("type") or part_type
    header = (f"✅ {type_names.get(display_type, display_type)}设计完成！\n"
              f"{result['summary']}\n\n"
              f"📜 建模宏已生成（{result['name']}），正在为你自动建模…")
    if result.get("extra_macro"):
        header += f"\n（含蜗壳宏 {result['extra_name']}）"

    return {"reply": header, "action": "build", "type": display_type, "params": params,
            "summary": result["summary"], "macro": result["macro"], "name": result["name"],
            "extra_macro": result.get("extra_macro", ""), "extra_name": result.get("extra_name", ""),
            "llm": llm_used}


# ═══════════════════════════════════════════════════════════════
# 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tests = [
        [{"role": "user", "content": "设计一台离心风机 Q=5000 P=2500 n=1450"}],
        [{"role": "user", "content": "DN100 PN16 平焊法兰"}],
        [{"role": "user", "content": "你好"}],
        [{"role": "user", "content": "做个轴流风机"}],
        [{"role": "user", "content": "设计一台离心风机 Q=5000 P=2500"}],       # 无 n → 自动选型
        [{"role": "user", "content": "帮我设计一台风机 Q=20000 P=800"}],        # 泛指 → 自动选机型
        [{"role": "user", "content": "轴流风机 Q=30000 P=400"}],                # 无 n 轴流
    ]
    for t in tests:
        r = chat(t, use_llm=False)
        print(f"\n用户: {t[0]['content']}")
        print(f"意图: {r['action']}  type={r['type']}  macro={len(r['macro'])}字符")
        print(f"回复: {r['reply'][:150]}")
