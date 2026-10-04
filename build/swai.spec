# -*- mode: python ; coding: utf-8 -*-
"""
SWAI — PyInstaller 打包配置

SWAI 是 CLI 工具（非 GUI），默认带命令行窗口。

使用说明：
  1. 在 Windows 上装好 Python 3.12+
  2. pip install -r requirements.txt
  3. pyinstaller --noconfirm build/swai.spec
  4. 成品在 dist/SWAI.exe
"""
import sys
import os
from pathlib import Path

try:
    _spec_dir = Path(__file__).resolve().parent
except NameError:
    _spec_dir = Path.cwd() / "build"
PROJECT_ROOT = _spec_dir.parent

# ── 数据文件（随 exe 打包） ──
DATAS = []

# ── 隐式导入 ──
HIDDEN_IMPORTS = [
    "swai.flange.params",
    "swai.flange.gb_standards",
    "swai.flange.ai_extractor",
    "swai.flange.generator",
    "swai.flange.pipeline",
    "swai.impeller.design",
    "swai.impeller.params",
    "swai.impeller.blades",
    "swai.impeller.generator",
    "swai.impeller.volute",
    "swai.axial.design",
    "swai.axial.params",
    "swai.axial.blades",
    "swai.axial.generator",
]

# ── 排除 ──
EXCLUDES = [
    "tkinter",
    "tkinter.test",
    "unittest",
    "pytest",
    "curses",
    "lib2to3",
    "pydoc",
    "test",
]

a = Analysis(
    [str(PROJECT_ROOT / "app" / "main.py")],
    pathex=[
        str(PROJECT_ROOT),
    ],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SWAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,       # CLI 工具：保留命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
