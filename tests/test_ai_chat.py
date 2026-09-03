"""
AI 聊天引擎测试 — 正则降级模式（无 LLM / 无网络 / 无 SolidWorks）

覆盖：意图识别（design/ask/chat）、参数提取、4 类法兰、离心/轴流（含转速缺省自动选型）、
泛指风机选型、缺参追问、闲聊、LLM JSON 解析。
"""

import pytest

from ai_chat import chat, parse_llm_json


def _chat(text):
    return chat([{"role": "user", "content": text}], use_llm=False)


# ═══════════════════════════════════════════════════════════════
# 闲聊
# ═══════════════════════════════════════════════════════════════


def test_smalltalk_is_chat():
    r = _chat("你好")
    assert r["action"] == "chat"
    assert r["macro"] == ""
    assert "机械设计" in r["reply"]
    assert r["llm"] is False


def test_empty_messages():
    r = chat([], use_llm=False)
    assert r["action"] == "chat"
    assert r["reply"]


# ═══════════════════════════════════════════════════════════════
# 法兰（4 类型）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("text,ftype", [
    ("DN100 PN16 平焊法兰", "plate"),
    ("DN100 PN16 带颈平焊法兰", "slip_on"),
    ("DN100 PN16 对焊法兰", "weld_neck"),
    ("DN100 PN16 盲板法兰", "blind"),
])
def test_flange_design_all_types(text, ftype):
    r = _chat(text)
    assert r["action"] == "build"
    assert r["type"] == "flange"
    assert r["params"]["dn"] == 100
    assert r["params"]["pn"] == 16
    assert r["params"]["flange_type"] == ftype
    assert r["macro"]
    assert "FeatureRevolve" in r["macro"] or "FeatureCut" in r["macro"]


def test_flange_slip_on_keyword_priority():
    """带颈平焊不能被"平焊"抢先命中为 plate"""
    r = _chat("DN50 PN10 带颈平焊法兰")
    assert r["params"]["flange_type"] == "slip_on"


def test_flange_missing_pn_asks():
    r = _chat("设计一个法兰 DN100")
    assert r["action"] == "ask"
    assert r["type"] == "flange"
    assert r["macro"] == ""
    assert "PN" in r["reply"] or "公称压力" in r["reply"]


def test_flange_unsupported_spec_friendly_error():
    r = _chat("设计 DN700 PN16 平焊法兰")
    assert r["action"] == "ask"
    assert "失败" in r["reply"] or "不在" in r["reply"]


# ═══════════════════════════════════════════════════════════════
# 离心风机叶轮
# ═══════════════════════════════════════════════════════════════


def test_impeller_design_with_speed():
    r = _chat("设计一台离心风机 Q=5000 P=2500 n=1450")
    assert r["action"] == "build"
    assert r["type"] == "impeller"
    assert r["params"]["Q"] == 5000
    assert r["params"]["P"] == 2500
    assert r["params"]["n"] == 1450
    assert r["macro"]
    assert r["extra_macro"]  # 默认含蜗壳


def test_impeller_design_auto_speed():
    """转速缺省 → 自动选型且不追问"""
    r = _chat("设计一台离心风机 Q=5000 P=2500")
    assert r["action"] == "build"
    assert r["type"] == "impeller"
    assert "n" not in r["params"]
    assert "自动选型" in r["summary"]


# ═══════════════════════════════════════════════════════════════
# 轴流风机
# ═══════════════════════════════════════════════════════════════


def test_axial_design_with_speed():
    r = _chat("轴流风机 Q=30000 P=400 n=960")
    assert r["action"] == "build"
    assert r["type"] == "axial"
    assert r["params"]["Q"] == 30000
    assert r["params"]["n"] == 960
    assert r["macro"]


def test_axial_design_auto_speed():
    r = _chat("轴流风机 Q=30000 P=400")
    assert r["action"] == "build"
    assert r["type"] == "axial"
    assert "n" not in r["params"]
    assert "自动选型" in r["summary"]


# ═══════════════════════════════════════════════════════════════
# 泛指风机 → 选型
# ═══════════════════════════════════════════════════════════════


def test_generic_fan_selects_machine():
    r = _chat("帮我设计一台风机 Q=20000 P=800")
    assert r["action"] == "build"
    # 选型后落到具体机型
    assert r["type"] in ("impeller", "axial")
    assert "风机选型" in r["summary"]
    assert r["macro"]


def test_fan_missing_pressure_asks():
    r = _chat("做个风机 Q=5000")
    assert r["action"] == "ask"
    assert r["macro"] == ""
    assert "P" in r["reply"] or "全压" in r["reply"]


# ═══════════════════════════════════════════════════════════════
# LLM JSON 解析（纯函数，不联网）
# ═══════════════════════════════════════════════════════════════


def test_parse_llm_json_variants():
    assert parse_llm_json('{"intent": "chat"}') == {"intent": "chat"}
    assert parse_llm_json('好的，结果如下：\n```json\n{"intent": "design"}\n```') == {"intent": "design"}
    assert parse_llm_json("前后杂质 {\"a\": 1} 尾巴") == {"a": 1}
    assert parse_llm_json("") == {}
    assert parse_llm_json("没有大括号") == {}
    assert parse_llm_json("{坏的 json") == {}
