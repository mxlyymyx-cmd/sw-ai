# SWAI SolidWorks 插件安装脚本
#
# 用法: 以管理员身份运行 PowerShell
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#   .\install.ps1
#
# 前提条件:
#   - SolidWorks 2022+ 已安装
#   - .NET Framework 4.8 SDK 或 Build Tools 已安装
#   - Python 3.10+ 已安装
#   - Python API 服务器依赖: pip install flask flask-cors requests

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SWAI 🏭 插件安装向导" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ──────────── 1. 检查 Python 后端 ────────────
Write-Host "[1/4] 检查 Python API 服务器..." -ForegroundColor Yellow

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:5757/api/health" -TimeoutSec 3
    if ($health.status -eq "ok") {
        Write-Host "  ✅ Python API 服务器运行中 (v$($health.version))" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠️  Python API 服务器未运行" -ForegroundColor Yellow
    Write-Host "  启动方式:" -ForegroundColor Gray
    Write-Host "    cd projects\solidworks-parametric" -ForegroundColor Gray
    Write-Host "    pip install -r requirements-plugin.txt" -ForegroundColor Gray
    Write-Host "    python api.py --port 5757" -ForegroundColor Gray

    $answer = Read-Host "  是否继续安装插件? (y/n, 默认 y)"
    if ($answer -eq "n") {
        Write-Host "  ❌ 安装已取消" -ForegroundColor Red
        exit 1
    }
}

# ──────────── 2. 编译插件 ────────────
Write-Host ""
Write-Host "[2/4] 编译 SolidWorks 插件..." -ForegroundColor Yellow

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$csprojPath = Join-Path $projectDir "SWAIAddin.csproj"
$outputPath = Join-Path $projectDir "bin\x86\Release"

# 检查 MSBuild
$msbuildPaths = @(
    "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe",
    "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe",
    "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe",
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\MSBuild\Current\Bin\MSBuild.exe",
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe"
)

$msbuild = $null
foreach ($path in $msbuildPaths) {
    if (Test-Path $path) {
        $msbuild = $path
        break
    }
}

if ($msbuild -eq $null -or !(Test-Path $msbuild)) {
    Write-Host "  ❌ 未找到 MSBuild，请安装 Visual Studio 或 Build Tools" -ForegroundColor Red
    Write-Host "  下载: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor Gray
    exit 1
}

Write-Host "  使用 MSBuild: $msbuild" -ForegroundColor Gray

# 编译
& $msbuild $csprojPath /p:Configuration=Release /p:Platform=x86 /t:Clean,Build

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ 编译失败，请检查错误信息" -ForegroundColor Red
    exit 1
}

$dllPath = Join-Path $outputPath "SWAIAddin.dll"
if (!(Test-Path $dllPath)) {
    Write-Host "  ❌ 编译产物未找到: $dllPath" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ 编译成功: $dllPath" -ForegroundColor Green

# ──────────── 3. 注册 COM ────────────
Write-Host ""
Write-Host "[3/4] 注册 COM (regasm)..." -ForegroundColor Yellow

# 检查 regasm（x86 DLL 必须用 32 位 RegAsm —— SolidWorks 是 32 位进程）
$regasmPaths = @(
    "C:\Windows\Microsoft.NET\Framework\v4.0.30319\RegAsm.exe",
    "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe"
)

$regasm = $null
foreach ($path in $regasmPaths) {
    if (Test-Path $path) {
        $regasm = $path
        break
    }
}

if ($regasm -eq $null) {
    Write-Host "  ❌ 未找到 RegAsm.exe (.NET Framework 4.x)" -ForegroundColor Red
    exit 1
}

Write-Host "  注册 DLL..." -ForegroundColor Gray
& $regasm $dllPath /codebase

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ RegAsm 注册失败" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ COM 注册成功" -ForegroundColor Green

# ──────────── 4. 验证 ────────────
Write-Host ""
Write-Host "[4/4] 验证安装..." -ForegroundColor Yellow

$regKey = "HKLM:\SOFTWARE\WOW6432Node\SolidWorks\AddIns\{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}"
if (Test-Path $regKey) {
    Write-Host "  ✅ 注册表项存在: $regKey" -ForegroundColor Green
} else {
    $regKey = "HKLM:\SOFTWARE\SolidWorks\AddIns\{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}"
    if (Test-Path $regKey) {
        Write-Host "  ✅ 注册表项存在(64位视图): $regKey" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  注册表项不存在，请在 SolidWorks 中手动加载插件" -ForegroundColor Yellow
        Write-Host "     SolidWorks → 工具 → 插件 → 勾选 SWAI" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ SWAI 安装完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor White
Write-Host "  1. 启动 Python API 服务器:" -ForegroundColor Gray
Write-Host "     python api.py --port 5757" -ForegroundColor Gray
Write-Host "  2. 启动/重启 SolidWorks" -ForegroundColor Gray
Write-Host "  3. 工具 → 插件 → 勾选 SWAI Addin" -ForegroundColor Gray
Write-Host "  4. 点击 SWAI 工具栏按钮打开面板" -ForegroundColor Gray
Write-Host ""
Write-Host "或手动注册 (以管理员身份):" -ForegroundColor Gray
Write-Host "  regasm /codebase bin\x86\Release\SWAIAddin.dll" -ForegroundColor Gray
