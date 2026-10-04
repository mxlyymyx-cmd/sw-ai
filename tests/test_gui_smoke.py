"""GUI 层冒烟测试：app/chat_gui.py 可导入、结构完整（无头环境，不实例化 Tk 窗口）。

真实窗口交互需人工在桌面环境验证，这里只守住"模块能加载、入口在"。
"""

import tkinter as tk

import app.chat_gui as gui


def test_module_imports_and_entry_exists():
    assert callable(gui.main)
    assert hasattr(gui, "ChatWindow")


def test_chat_window_is_a_tk_root():
    assert issubclass(gui.ChatWindow, tk.Tk)


def test_server_probe_and_boot_helpers_exist():
    assert callable(gui.server_alive)
    assert callable(gui.start_server_thread)


def test_api_base_targets_local_service():
    assert gui.API_BASE.startswith("http://127.0.0.1")
    assert gui.CONFIG_PATH.endswith("config.json")
