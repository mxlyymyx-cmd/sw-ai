"""
AI 自然语言 → 法兰参数提取 Pipeline

从用户自然语言描述（如 "DN100 PN16 平焊法兰，4个螺栓孔"）中，
用 LLM 提取结构化 FlangeParams。
"""

import json
import os
import re
from typing import Optional

from .params import FlangeParams, FlangeType, SealType, ExtractionResult
from .gb_standards import lookup, is_supported, list_available


# ── LLM 提取提示词 ──

EXTRACT_SYSTEM_PROMPT = """你是一个专业机械设计工程师，擅长从自然语言描述中提取法兰参数。

## 你的任务
从用户的自然语言描述中，提取法兰盘的规格参数。

## 必填参数
- dn (int): 公称通径，如 DN100 → 100, DN50 → 50
- pn (int): 公称压力，如 PN16 → 16, PN25 → 25

## 可选参数
- flange_type (str): 法兰类型 - "plate"(板式平焊) / "slip_on"(带颈平焊) / "weld_neck"(对焊) / "blind"(盲板)
- seal_type (str): 密封面类型 - "rf"(突面) / "mfm"(凹凸面) / "tg"(榫槽面)
- material (str): 材料，如 "Q235B", "304", "316L", "20#"
- n (int): 螺栓孔数量
- coating (str): 表面处理

## 交互常识（用于推算未明确给出的参数）
- 默认法兰类型为 plate（板式平焊法兰）
- 默认密封面为 rf（突面）
- 默认材料为 Q235B（碳钢，常温低压）
- PN ≤ 16 时材料通常是碳钢，PN ≥ 25 可能需要合金钢
- "国标" → GB/T 9119-2010
- "化工部标准" → HG/T 20592-2009
- "美标" → ASME B16.5

## 输出格式
只输出一个 JSON 对象，不要任何额外文字。
```json
{
  "dn": 100,
  "pn": 16,
  "flange_type": "plate",
  "seal_type": "rf",
  "material": "Q235B",
  "n": 8,
  "notes": ["默认RF密封面", "默认碳钢材料"]
}
```
"""


def extract_with_llm(text: str, api_key: Optional[str] = None) -> dict:
    """
    用 LLM 从自然语言提取法兰参数

    支持两种模式：
    1. 如果配置了 LLM_API_KEY → 调用 LLM API
    2. 未配置 → 降级用正则提取

    Args:
        text: 用户输入的自然语言
        api_key: LLM API key (默认从环境变量 LLM_API_KEY 读取)

    Returns:
        提取到的参数 dict
    """
    api_key = api_key or os.environ.get("LLM_API_KEY", "")

    if api_key:
        return _call_llm_api(text, api_key)
    else:
        print("[AI 提取器] 未配置 LLM_API_KEY，使用正则模式降级提取")
        return _regex_extract(text)


def _call_llm_api(text: str, api_key: str) -> dict:
    """调用 LLM API 提取参数"""
    try:
        import requests as req
    except ImportError:
        print("[AI 提取器] requests 未安装，降级到正则")
        return _regex_extract(text)

    # 可配置的 API endpoint（默认兼容 OpenAI 格式）
    api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    try:
        resp = req.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # 从 markdown 代码块中提取 JSON
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        json_str = json_match.group(1) if json_match else content.strip()
        return json.loads(json_str)

    except Exception as e:
        print(f"[AI 提取器] LLM API 调用失败: {e}，降级到正则")
        return _regex_extract(text)


def _regex_extract(text: str) -> dict:
    """正则表达式降级提取"""
    text = text.strip()
    result = {}
    notes = []

    # DN: DN100, Dn100, dn 100, 公称通径100
    dn_match = re.search(r"(?:DN|Dn|dn|公称通径|直径)\s*(\d{2,4})", text)
    if dn_match:
        result["dn"] = int(dn_match.group(1))

    # PN: PN16, Pn16, pn 16, 公称压力16
    pn_match = re.search(r"(?:PN|Pn|pn|公称压力)\s*(\d{2,3})", text)
    if pn_match:
        result["pn"] = int(pn_match.group(1))

    # 螺栓孔数量: "4个螺栓孔", "8孔", "12个孔"
    hole_match = re.search(r"(\d+)\s*[个只]?\s*(?:螺栓孔|螺孔|螺栓|孔)", text)
    if hole_match:
        result["n"] = int(hole_match.group(1))

    # 法兰类型（长词优先，避免"带颈平焊"被"平焊"抢先命中）
    type_map = {
        "带颈对焊": "weld_neck",
        "对焊": "weld_neck",
        "带颈平焊": "slip_on",
        "带颈": "slip_on",
        "盲板": "blind",
        "法兰盖": "blind",
        "平焊": "plate",
        "板式": "plate",
    }
    for keyword, ftype in type_map.items():
        if keyword in text:
            result["flange_type"] = ftype
            break
    else:
        text_l = text.lower()
        for kw in ("weld_neck", "weld neck", "slip_on", "slip-on", "blind", "plate"):
            if kw in text_l:
                result["flange_type"] = kw.replace("-", "_").replace(" ", "_")
                break

    # 密封面
    seal_map = {
        "突面": "rf",
        "凹凸": "mfm",
        "榫槽": "tg",
    }
    for keyword, stype in seal_map.items():
        if keyword in text:
            result["seal_type"] = stype
            break

    # 材料
    material_map = {
        "304": "304", "316": "316L", "碳钢": "Q235B",
        "不锈钢": "304", "合金钢": "15CrMo", "20#": "20#",
    }
    for keyword, mat in material_map.items():
        if keyword in text:
            result["material"] = mat
            break

    # 补充默认值
    if "flange_type" not in result:
        result["flange_type"] = "plate"
        notes.append("默认法兰类型：板式平焊")
    if "seal_type" not in result:
        result["seal_type"] = "rf"
        notes.append("默认密封面：突面 RF")
    if "material" not in result:
        result["material"] = "Q235B"
        notes.append("默认材料：Q235B")

    result["notes"] = notes
    return result


def extract(text: str) -> ExtractionResult:
    """
    完整提取流程：
    1. LLM 提取（或正则降级）
    2. 查国标数据库补全尺寸
    3. 验证参数合理性

    Args:
        text: 用户输入

    Returns:
        ExtractionResult
    """
    raw = extract_with_llm(text)
    notes = raw.get("notes", [])
    error = None
    params = None

    # 验证 DN/PN
    dn = raw.get("dn")
    pn = raw.get("pn")
    if not dn:
        error = "未能提取公称通径 (DN)，请输入如 DN100"
    elif not pn:
        error = "未能提取公称压力 (PN)，请输入如 PN16"
    elif dn < 6 or dn > 2000:
        error = f"公称通径 DN{dn} 超出合理范围 (DN6~DN2000)"
    elif pn not in (10, 16, 25, 40, 63, 100, 160):
        error = f"公称压力 PN{pn} 不常见，支持: 10, 16, 25, 40, 63, 100, 160"

    if error:
        return ExtractionResult(
            success=False,
            raw_input=text,
            error=error,
            notes=notes,
        )

    # 查国标
    try:
        if is_supported(dn, pn):
            params = lookup(dn, pn, raw.get("flange_type", "plate"))
        else:
            # 自定义尺寸 — 不查国标，用 raw 中提取的值
            params = FlangeParams(
                dn=dn,
                pn=pn,
                d=raw.get("d", 0),
                k=raw.get("k", 0),
                l=raw.get("l", 0),
                n=raw.get("n", 8),
                c=raw.get("c", 0),
                flange_type=FlangeType(raw.get("flange_type", "plate")),
                seal_type=SealType(raw.get("seal_type", "rf")),
                material=raw.get("material", "Q235B"),
            )
            notes.append(f"DN{dn} PN{pn} 不在国标数据库中，使用自定义尺寸")

        # 覆盖用户指定的额外参数
        if raw.get("n"):
            params.n = int(raw["n"])
        if raw.get("material"):
            params.material = raw["material"]

        return ExtractionResult(
            success=True,
            params=params,
            raw_input=text,
            confidence=0.85,
            notes=notes,
        )

    except ValueError as e:
        return ExtractionResult(
            success=False,
            raw_input=text,
            error=str(e),
            notes=notes,
        )


if __name__ == "__main__":
    # 测试
    test_cases = [
        "DN100 PN16 平焊法兰",
        "50 DN 1.6MPa 突面法兰 碳钢",
        "DN200 PN25 对焊法兰 304不锈钢",
        "给我一个DN80 PN40的法兰，要4个螺栓孔",
        "DIN2501 PN10 DN150",
    ]
    for case in test_cases:
        result = extract(case)
        status = "✅" if result.success else "❌"
        print(f"\n{status} 输入: {case}")
        print(f"   置信度: {result.confidence}")
        if result.success:
            print(f"   DN{result.params.dn} PN{result.params.pn}")
            print(f"   外径 {result.params.d} | 螺栓 {result.params.n}×ø{result.params.l} PCD={result.params.k}")
        if result.error:
            print(f"   错误: {result.error}")
        for note in result.notes:
            print(f"   提示: {note}")
