@echo off
REM ─────────────────────────────────────────────────────────────
REM  SWAI 🏭 SolidWorks AI 插件 — 一键打包安装包
REM  在 Windows 上双击运行，自动完成：
REM    1. 编译 C# 插件 DLL
REM    2. PyInstaller 打包 Python API 服务为独立 exe
REM    3. Inno Setup 生成 SWAI-Setup-1.0.0.exe
REM  前提：已安装 Python 3.10+、VS Build Tools（或 VS 2022）、Inno Setup 6
REM ─────────────────────────────────────────────────────────────
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d %~dp0..

echo ============================================
echo   SWAI 一键打包安装包
echo ============================================
echo.

REM ── 1. 找 MSBuild ──
set MSBUILD=
for /f "usebackq delims=" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.Component.MSBuild -property installationPath 2^>nul`) do set VSROOT=%%i
if defined VSROOT (
    if exist "%VSROOT%\MSBuild\Current\Bin\MSBuild.exe" set MSBUILD=%VSROOT%\MSBuild\Current\Bin\MSBuild.exe
)
if not defined MSBUILD if exist "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe" set MSBUILD=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe
if not defined MSBUILD (
    echo [❌] 未找到 MSBuild，请安装 VS Build Tools 2022
    echo      下载: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
    pause & exit /b 1
)
echo [1/4] MSBuild: %MSBUILD%

REM ── 2. 编译 C# 插件 ──
echo [2/4] 编译 SolidWorks 插件...
"%MSBUILD%" plugin\SWAIAddin.csproj /p:Configuration=Release /p:Platform=x64 /t:Clean,Build /nologo /verbosity:minimal
if errorlevel 1 (
    echo [❌] 插件编译失败
    pause & exit /b 1
)
if not exist "plugin\bin\x64\Release\SWAIAddin.dll" (
    echo [❌] 未找到编译产物 plugin\bin\x64\Release\SWAIAddin.dll
    echo     请确认 plugin\libs\ 下有 SolidWorks Interop DLL
    pause & exit /b 1
)
echo [✅] 插件编译成功

REM ── 3. PyInstaller 打包后端 ──
echo [3/4] 打包 Python API 服务...
pip install -r requirements-plugin.txt -q 2>nul
pip install pyinstaller -q 2>nul
if not exist dist mkdir dist
pyinstaller --onefile --name SWAIServer --clean --noconfirm ^
    --hidden-import flask --hidden-import flask_cors --hidden-import requests ^
    api.py
if errorlevel 1 (
    echo [❌] PyInstaller 打包失败
    pause & exit /b 1
)
echo [✅] SWAIServer.exe 就绪

REM ── 4. Inno Setup 生成安装包 ──
echo [4/4] 构建安装程序...
set ISCC=
for /d %%d in ("C:\Program Files*\Inno Setup*") do (
    if exist "%%d\ISCC.exe" set ISCC=%%d\ISCC.exe
)
if not defined ISCC (
    echo [❌] 未找到 Inno Setup 6
    echo      下载: https://jrsoftware.org/isdl.php
    pause & exit /b 1
)
"%ISCC%" plugin\installer.iss
if errorlevel 1 (
    echo [❌] 安装包构建失败
    pause & exit /b 1
)

echo.
echo ============================================
echo   ✅ 全部完成！
echo   安装包: dist\SWAI-Setup-1.0.0.exe
echo ============================================
echo.
echo 把这个 exe 发给同事，双击就能装：
echo   1. 双击安装包 → 下一步下一步
echo   2. 打开 SolidWorks → 工具 → 插件 → 勾选 SWAI Addin
echo   3. AI 服务已开机自启，直接对话建模
echo.
pause
