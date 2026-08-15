# SWAI 🏭 C# 插件一键编译打包脚本
#
# 用法：
#   以管理员身份运行 PowerShell，然后：
#     .\plugin\build_plugin.ps1
#
# 功能：
#   1. 从 SolidWorks 安装目录复制 Interop DLL 到 plugin/libs/
#   2. 用 MSBuild 编译 C# 插件
#   3. 打包为 ZIP（可直接分发给其他人）
#   4. 可选：提交到 GitHub 让 CI 以后自动构建
#
# 前提条件：
#   - SolidWorks 2022+ 已安装
#   - Visual Studio Build Tools 2022 或 VS 2022 已安装
#   - Git 已安装

param(
    [switch]$SkipGitPush  # 加 -SkipGitPush 跳过提交到 GitHub
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PluginDir = Join-Path $ProjectRoot "plugin"
$LibsDir = Join-Path $PluginDir "libs"
$OutputZip = Join-Path $ProjectRoot "SWAI-Plugin-win32.zip"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SWAI 🏭  C# 插件编译打包" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ──── 步骤 1: 复制 SolidWorks Interop DLL ────
Write-Host "[1/5] 复制 SolidWorks Interop DLL → plugin/libs/" -ForegroundColor Yellow

$swInteropDir = "C:\Program Files\SolidWorks Corp\SolidWorks\api\redist"
$neededDlls = @(
    "SolidWorks.Interop.sldworks.dll",
    "SolidWorks.Interop.swcommands.dll",
    "SolidWorks.Interop.swconst.dll",
    "SolidWorks.Interop.swpublished.dll"
)

# 先检查 libs/ 里是否已经有了
$allFound = $true
foreach ($dll in $neededDlls) {
    $libPath = Join-Path $LibsDir $dll
    if (Test-Path $libPath) {
        Write-Host "  ✅ $dll 已存在" -ForegroundColor Green
    } else {
        $allFound = $false
        $swPath = Join-Path $swInteropDir $dll
        if (Test-Path $swPath) {
            New-Item -ItemType Directory -Force -Path $LibsDir | Out-Null
            Copy-Item $swPath -Destination $LibsDir
            Write-Host "  ✅ 已复制: $dll" -ForegroundColor Green
        } else {
            Write-Host "  ❌ 找不到: $dll" -ForegroundColor Red
            Write-Host "     请确认 SolidWorks 安装在默认路径" -ForegroundColor Gray
            exit 1
        }
    }
}

Write-Host "  ✅ Interop DLL 已就绪" -ForegroundColor Green

# ──── 步骤 2: 找 MSBuild ────
Write-Host ""
Write-Host "[2/5] 查找 MSBuild..." -ForegroundColor Yellow

# 用 vswhere 找 MSBuild（VS 2019+ 自带）
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$msbuild = $null

if (Test-Path $vswhere) {
    $vsPath = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath
    if ($vsPath) {
        $msbuild = Join-Path $vsPath "MSBuild\Current\Bin\MSBuild.exe"
        if (!(Test-Path $msbuild)) {
            $msbuild = Join-Path $vsPath "MSBuild\15.0\Bin\MSBuild.exe"
        }
    }
}

# 兜底：.NET Framework 自带的
if (!$msbuild -or !(Test-Path $msbuild)) {
    $msbuild = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\MSBuild.exe"
}

if (!(Test-Path $msbuild)) {
    Write-Host "  ❌ 找不到 MSBuild，请安装 Visual Studio Build Tools" -ForegroundColor Red
    Write-Host "     https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor Gray
    exit 1
}

Write-Host "  ✅ MSBuild: $msbuild" -ForegroundColor Green

# ──── 步骤 3: 编译 ────
Write-Host ""
Write-Host "[3/5] 编译 C# 插件..." -ForegroundColor Yellow

$csproj = Join-Path $PluginDir "SWAIAddin.csproj"
& $msbuild $csproj /p:Configuration=Release /p:Platform=x86 /t:Clean,Build /nologo /verbosity:minimal

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ 编译失败，错误码: $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

$dllPath = Join-Path $PluginDir "bin\x86\Release\SWAIAddin.dll"
if (!(Test-Path $dllPath)) {
    Write-Host "  ❌ 未找到编译产物" -ForegroundColor Red
    exit 1
}

Write-Host "  ✅ 编译成功: $dllPath" -ForegroundColor Green

# ──── 步骤 4: 打包 ZIP ────
Write-Host ""
Write-Host "[4/5] 打包为 ZIP..." -ForegroundColor Yellow

$zipDir = Join-Path $ProjectRoot "SWAI-Plugin-v1.0"
New-Item -ItemType Directory -Force -Path $zipDir | Out-Null

Copy-Item $dllPath -Destination $zipDir
Copy-Item (Join-Path $PluginDir "install.ps1") -Destination $zipDir
Copy-Item (Join-Path $PluginDir "README-install.md") -Destination $zipDir

if (Test-Path $OutputZip) {
    Remove-Item $OutputZip -Force
}
Compress-Archive -Path "$zipDir\*" -DestinationPath $OutputZip -Force
Remove-Item $zipDir -Recurse -Force

Write-Host "  ✅ 打包完成: $OutputZip" -ForegroundColor Green
Write-Host "     大小: $((Get-Item $OutputZip).Length / 1KB) KB" -ForegroundColor Gray

# ──── 步骤 5: 提交到 GitHub（让 CI 以后自动构建） ────
Write-Host ""
Write-Host "[5/5] 提交到 GitHub..." -ForegroundColor Yellow

if (!$SkipGitPush) {
    try {
        # 把 libs/ 里的 DLL 加到版本控制
        git -C $ProjectRoot add plugin/libs/*.dll
        git -C $ProjectRoot commit -m "📦 Add SolidWorks Interop DLLs for CI build"
        
        Write-Host "  ⏳ 推送到 GitHub（可能需要几秒钟）..." -ForegroundColor Gray
        git -C $ProjectRoot push origin main
        
        Write-Host "  ✅ 已推送到 GitHub，CI 下次会自动编译" -ForegroundColor Green
        Write-Host "     去查看: https://github.com/mxlyymyx-cmd/sw-ai/actions" -ForegroundColor Gray
    } catch {
        Write-Host "  ⚠️  提交失败: $_" -ForegroundColor Yellow
        Write-Host "     下次推代码时会自动触发 CI 编译" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⏭️  跳过 GitHub 提交（你加了 -SkipGitPush）" -ForegroundColor Yellow
    Write-Host "     要手动推送: git push origin main" -ForegroundColor Gray
    Write-Host "     以后 CI 会自动编译插件" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ✅ 全部完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "产物：" -ForegroundColor White
Write-Host "  ZIP 包: $OutputZip" -ForegroundColor Green
Write-Host "  编译的 DLL: $dllPath" -ForegroundColor Gray
Write-Host ""
Write-Host "使用方式：" -ForegroundColor White
Write-Host "  其他电脑想装这个插件，直接解压 ZIP，然后：" -ForegroundColor Gray
Write-Host "    管理员 PowerShell → .\install.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "现在去 SolidWorks 试试：" -ForegroundColor White
Write-Host "  1. 确保 Python API 在跑：python api.py --port 5757" -ForegroundColor Gray
Write-Host "  2. 启动 SolidWorks" -ForegroundColor Gray
Write-Host "  3. 工具 → 插件 → 勾选 SWAI Addin" -ForegroundColor Gray
