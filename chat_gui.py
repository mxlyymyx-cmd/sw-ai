#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SWAI Chat — 桌面 AI 机械设计助手（聊天窗口）
=================================================
双击即用：
  1. 自动检测本地 AI 服务（127.0.0.1:5757），未运行则内嵌自动启动
  2. 打开聊天窗口，直接对话设计需求（如"设计离心风机 Q=5000 P=2500 n=1450"）
  3. ⚙ 设置里可填 DeepSeek API Key（可选；不填走降级模式也能识别标准格式）

打包：pyinstaller --onefile --noconsole --name SWAIChat chat_gui.py
"""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

import requests

# 确保 PyInstaller 打包时收集到服务模块（api.py 会连带收集 flange/impeller/axial）
import api  # noqa: F401
import ai_chat  # noqa: F401

API_BASE = "http://127.0.0.1:5757"
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SWAI")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

# ── 浅色主题（白/淡黄，用户偏好）──
BG      = "#F5F2EA"   # 窗口背景 暖米白
PANEL   = "#FFFFFF"
USER_BG = "#D6E4FF"   # 用户气泡 淡蓝
AI_BG   = "#FFFFFF"   # AI 气泡 白
INPUT_BG= "#FFFFFF"
TEXT    = "#2B2B2B"
ACCENT  = "#4A7DDB"
ACCENT_DARK = "#3A66B8"
OK      = "#2E8B57"
ERR     = "#C0392B"
FONT    = ("Microsoft YaHei UI", 10)
FONT_B  = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 13, "bold")


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def server_alive() -> bool:
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_server_thread():
    """内嵌启动 Flask AI 服务（仅当端口未被占用时）。"""
    def _run():
        try:
            import api
            api.app.run(host="127.0.0.1", port=5757, debug=False, use_reloader=False)
        except Exception as e:
            sys.stderr.write(f"[SWAI] 服务启动失败: {e}\n")
    t = threading.Thread(target=_run, daemon=True, name="swai-server")
    t.start()


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# 设置对话框
# ═══════════════════════════════════════════════════════════

class SettingsDialog(tk.Toplevel):
    def __init__(self, master, on_saved=None):
        super().__init__(master)
        self.title("SWAI 设置")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.on_saved = on_saved
        self._build()
        self._load_current()
        self.grab_set()
        self.update_idletasks()
        w, h = 460, 330
        x = self.master.winfo_rootx() + (self.master.winfo_width() - w) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        pad = {"padx": 18, "pady": 6}
        ttk.Label(self, text="🧠 AI 模型配置", font=FONT_B, background=BG).pack(anchor="w", **pad)

        frame = tk.Frame(self, bg=BG)
        frame.pack(fill="x", padx=18)
        tk.Label(frame, text="API Key", font=FONT, bg=BG).pack(anchor="w")
        self.key_var = tk.StringVar()
        self.key_entry = tk.Entry(frame, textvariable=self.key_var, show="•",
                                  font=FONT, bg=INPUT_BG, relief="solid", bd=1)
        self.key_entry.pack(fill="x", pady=(2, 4), ipady=3)
        tk.Label(frame, text="DeepSeek API Key（platform.deepseek.com 申请，sk- 开头）",
                 font=("Microsoft YaHei UI", 8), bg=BG, fg="#888").pack(anchor="w")

        tk.Label(frame, text="模型", font=FONT, bg=BG).pack(anchor="w", pady=(8, 0))
        self.model_var = tk.StringVar(value="deepseek-chat")
        combo = ttk.Combobox(frame, textvariable=self.model_var, state="readonly",
                             values=["deepseek-chat", "deepseek-reasoner"],
                             font=FONT)
        combo.pack(fill="x", pady=(2, 4), ipady=1)

        tk.Label(frame, text="API 地址", font=FONT, bg=BG).pack(anchor="w")
        self.url_var = tk.StringVar(value="https://api.deepseek.com/v1/chat/completions")
        tk.Entry(frame, textvariable=self.url_var, font=FONT,
                 bg=INPUT_BG, relief="solid", bd=1).pack(fill="x", pady=(2, 4), ipady=3)

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=18, pady=(10, 14))
        tk.Button(btns, text="测试连接", font=FONT, bg=BG, relief="solid", bd=1,
                  command=self._test).pack(side="left")
        self.test_lbl = tk.Label(btns, text="", font=FONT, bg=BG)
        self.test_lbl.pack(side="left", padx=8)
        tk.Button(btns, text="保存", font=FONT_B, bg=ACCENT, fg="white",
                  relief="flat", padx=20, pady=4, command=self._save).pack(side="right")

    def _load_current(self):
        cfg = load_config()
        self.key_var.set(cfg.get("llm_api_key", ""))
        self.model_var.set(cfg.get("llm_model", "deepseek-chat"))
        self.url_var.set(cfg.get("llm_api_url", "https://api.deepseek.com/v1/chat/completions"))

    def _test(self):
        key = self.key_var.get().strip()
        if not key:
            self.test_lbl.config(text="⚠️ 先填 Key", fg=ERR)
            return
        self.test_lbl.config(text="检测中…", fg="#888")
        self.update_idletasks()
        def run():
            try:
                r = requests.post(
                    self.url_var.get().strip() or "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": self.model_var.get(), "messages": [{"role": "user", "content": "hi"}],
                          "max_tokens": 5},
                    timeout=20,
                )
                ok = r.status_code == 200
                self.after(0, lambda: self.test_lbl.config(
                    text="✅ 连接成功" if ok else f"❌ {r.status_code} {r.text[:60]}",
                    fg=OK if ok else ERR))
            except Exception as e:
                self.after(0, lambda: self.test_lbl.config(text=f"❌ {str(e)[:40]}", fg=ERR))
        threading.Thread(target=run, daemon=True).start()

    def _save(self):
        cfg = load_config()
        cfg["llm_api_key"] = self.key_var.get().strip()
        cfg["llm_model"] = self.model_var.get()
        cfg["llm_api_url"] = self.url_var.get().strip()
        save_config(cfg)
        if self.on_saved:
            self.on_saved(bool(cfg["llm_api_key"]))
        self.destroy()


# ═══════════════════════════════════════════════════════════
# 主聊天窗口
# ═══════════════════════════════════════════════════════════

class ChatWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SW-AI 机械设计助手")
        self.configure(bg=BG)
        self.geometry("880x620")
        self.minsize(640, 480)

        self.history = []          # 传给后端的完整对话历史
        self.last_macro = None     # 最近一次生成的宏
        self._build_ui()
        self._refresh_status()

        # 欢迎语
        self._append("🤖 我是 SW-AI 机械设计助手！", "ai")
        self._append('直接说需求，比如：\n"设计一台离心风机 Q=5000 P=2500 n=1450"\n"DN100 PN16 平焊法兰"',
                     "ai")

        # 服务自检：没起就内嵌启动
        if not server_alive():
            self._append("⏳ 正在启动本地 AI 服务…", "ai")
            start_server_thread()
            self.after(1500, self._refresh_status)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI ──
    def _build_ui(self):
        # 顶栏
        top = tk.Frame(self, bg=ACCENT, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="SW-AI 🏭", font=FONT_TITLE, bg=ACCENT, fg="white").pack(side="left", padx=14)
        self.status_lbl = tk.Label(top, text="● 检测中…", font=FONT, bg=ACCENT, fg="white")
        self.status_lbl.pack(side="left", padx=8)
        tk.Button(top, text="⚙ 设置", font=FONT, bg=ACCENT_DARK, fg="white",
                  relief="flat", padx=12, command=self._open_settings).pack(side="right", padx=12)

        # 聊天区
        chat_wrap = tk.Frame(self, bg=BG)
        chat_wrap.pack(fill="both", expand=True, padx=12, pady=(10, 4))
        self.chat = scrolledtext.ScrolledText(
            chat_wrap, wrap="word", font=FONT, bg=AI_BG, fg=TEXT,
            relief="flat", borderwidth=0, padx=12, pady=10, state="disabled")
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("user", background=USER_BG, foreground="#1a3a6e",
                                lmargin1=40, lmargin2=40, spacing1=6, spacing3=6,
                                font=FONT_B)
        self.chat.tag_configure("ai", background=AI_BG, foreground=TEXT,
                                lmargin1=8, lmargin2=8, spacing1=6, spacing3=6)
        self.chat.tag_configure("sys", background=BG, foreground="#888",
                                lmargin1=8, lmargin2=8, spacing1=2, spacing3=2,
                                font=("Microsoft YaHei UI", 9))

        # 底部操作条
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=12, pady=(0, 4))
        self.macro_btn = tk.Button(bar, text="📜 保存宏", font=FONT, bg=BG,
                                   relief="solid", bd=1, state="disabled",
                                   command=self._save_macro)
        self.macro_btn.pack(side="left")

        # 输入区
        bottom = tk.Frame(self, bg=BG)
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        self.input = tk.Text(bottom, height=3, font=FONT, bg=INPUT_BG, fg=TEXT,
                             relief="solid", bd=1, padx=8, pady=6)
        self.input.pack(side="left", fill="both", expand=True)
        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<Shift-Return>", lambda e: None)  # Shift+Enter 换行
        self.send_btn = tk.Button(bottom, text="发送 ➤", font=FONT_B, bg=ACCENT,
                                  fg="white", relief="flat", padx=22, pady=8,
                                  command=self.send)
        self.send_btn.pack(side="right", padx=(8, 0))

    # ── 状态 ──
    def _refresh_status(self):
        alive = server_alive()
        cfg = load_config()
        if alive:
            if cfg.get("llm_api_key"):
                self.status_lbl.config(text=f"● 服务在线 · AI 已配置 · {cfg.get('llm_model','deepseek-chat')}",
                                       fg="white")
            else:
                self.status_lbl.config(text="● 服务在线 · 未配置 Key（降级模式）", fg="white")
        else:
            self.status_lbl.config(text="● 服务未启动", fg="#FFD2D2")

    def _open_settings(self):
        SettingsDialog(self, on_saved=lambda ok: (self._refresh_status(),
                       self._append("✅ API Key 已保存，AI 完全体解锁！" if ok
                                    else "已保存（未填 Key，继续用降级模式）", "sys")))

    # ── 聊天 ──
    def _append(self, text, kind):
        self.chat.config(state="normal")
        self.chat.insert("end", text + "\n\n", kind)
        self.chat.config(state="disabled")
        self.chat.see("end")

    def _on_enter(self, event):
        # Enter 发送，Shift+Enter 换行
        if not (event.state & 0x0001):
            self.send()
            return "break"
        return None

    def send(self, event=None):
        text = self.input.get("1.0", "end").strip()
        if not text:
            return
        self.input.delete("1.0", "end")
        self._append(f"🧑 {text}", "user")
        self.history.append({"role": "user", "content": text})
        self.macro_btn.config(state="disabled")
        threading.Thread(target=self._call_chat, daemon=True).start()

    def _call_chat(self):
        try:
            r = requests.post(f"{API_BASE}/api/chat", json={"messages": self.history}, timeout=180)
            data = r.json().get("data", {})
            reply = data.get("reply") or "（没有回复）"
            action = data.get("action", "chat")
            macro = data.get("macro") or ""
            name = data.get("name") or ""
            llm = data.get("llm", False)

            if macro:
                self.last_macro = macro
                extra = f"\n\n📜 已生成 VBA 宏（{name}）→ 点下方「保存宏」导出到文件，到 SolidWorks 里运行即可建模。"
            else:
                self.last_macro = None
                extra = ""

            self.after(0, lambda: (
                self._append(f"🤖 {reply}{extra}", "ai"),
                self.macro_btn.config(state="normal" if macro else "disabled"),
                self._refresh_status(),
            ))
            # 保留后端上下文（assistant 消息）
            if action in ("build", "ask"):
                self.history.append({"role": "assistant", "content": reply})
        except requests.ConnectionError:
            self.after(0, lambda: self._append("⚠️ 连不上本地 AI 服务，请稍等几秒再试", "ai"))
        except Exception as e:
            self.after(0, lambda: self._append(f"⚠️ 出错了：{str(e)[:100]}", "ai"))

    def _save_macro(self):
        if not self.last_macro:
            return
        default = os.path.join(os.path.expanduser("~"), "Desktop", "SWAI_macro.swp")
        path = filedialog.asksaveasfilename(
            title="保存 VBA 宏", defaultextension=".swp",
            initialfile=os.path.basename(default), initialdir=os.path.dirname(default),
            filetypes=[("SolidWorks 宏", "*.swp"), ("VBA 宏", "*.bas"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.last_macro)
            self._append(f"✅ 宏已保存：{path}", "sys")
        except Exception as e:
            self._append(f"❌ 保存失败：{e}", "sys")

    def _on_close(self):
        # 只关窗口，不杀服务（SolidWorks 插件还要用）
        self.destroy()


# ═══════════════════════════════════════════════════════════

def main():
    app = ChatWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
