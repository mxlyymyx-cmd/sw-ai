"""pytest 配置 — 仓库根目录加入 sys.path（swai/ 与 app/ 包在仓库根下）+ 测试离线隔离"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    """强制所有测试走离线正则模式。

    清掉一切 LLM key 来源（三个环境变量 + 用户本机可能存在的
    %APPDATA%/SWAI/config.json），保证测试不发起任何网络请求、结果确定。
    """
    for var in ("SWAI_LLM_API_KEY", "MECHFORGE_LLM_API_KEY", "LLM_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    import app.ai_chat as ai_chat
    monkeypatch.setattr(ai_chat, "_load_config", lambda: {})
