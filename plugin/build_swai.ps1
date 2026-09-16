# SWAI 插件编译部署脚本（Roslyn 兜底方案，无需 VS Build Tools）
#
# 用法（管理员 PowerShell）:
#   powershell -ExecutionPolicy Bypass -File plugin\build_swai.ps1
#
# 步骤: 复制 Interop DLL → Roslyn 编译 → 部署到 Program Files → RegAsm 注册 → 写 AddIns 注册表
$ErrorActionPreference = 'Stop'
$proj = 'c:\Users\Administrator\Desktop\SOLO\sw-ai\plugin'
$csc = 'C:\ProgramData\SolidWorksAIPlugin\roslyn2\tools\csc.exe'
$libs = Join-Path $proj 'libs'
$outDir = Join-Path $proj 'bin\Release'
$deployDir = 'C:\Program Files\SWAIPlugin'

# ──── 1. Interop DLL（优先从 SolidWorks 安装目录取，其次复用 Pro 项目 libs） ────
$swRedist = 'C:\Program Files\SolidWorks Corp\SolidWorks\api\redist'
$proLibs = 'C:\Users\Administrator\Desktop\SOLO\SolidWorksAIPlugin\libs'
$needed = 'SolidWorks.Interop.sldworks.dll', 'SolidWorks.Interop.swconst.dll', 'SolidWorks.Interop.swpublished.dll'
New-Item -ItemType Directory -Force -Path $libs | Out-Null
foreach ($dll in $needed) {
    $dst = Join-Path $libs $dll
    if (Test-Path $dst) { Write-Output "  [ok] $dll (cached)" ; continue }
    $src = Join-Path $swRedist $dll
    if (!(Test-Path $src)) { $src = Join-Path $proLibs $dll }
    Copy-Item $src $dst
    Write-Output "  [ok] copied $dll"
}

# ──── 2. Roslyn 编译（AnyCPU：32/64 位 SolidWorks 均可加载） ────
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$fw = 'C:\Program Files (x86)\Reference Assemblies\Microsoft\Framework\.NETFramework\v4.8'
if (-not (Test-Path $fw)) { $fw = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319' }

$src = @(
    "$proj\SWAIAddin.cs",
    "$proj\TaskPaneControl.cs",
    "$proj\TaskPaneControl.Designer.cs",
    "$proj\ApiClient.cs",
    "$proj\SwApiHelper.cs",
    "$proj\SettingsDialog.cs"
)
$refs = @(
    "/r:`"$fw\System.dll`"",
    "/r:`"$fw\System.Core.dll`"",
    "/r:`"$fw\System.Drawing.dll`"",
    "/r:`"$fw\System.Net.Http.dll`"",
    "/r:`"$fw\System.Windows.Forms.dll`"",
    "/r:`"$fw\System.Runtime.Serialization.dll`"",
    "/r:`"$fw\System.Web.Extensions.dll`"",
    "/r:`"$fw\Microsoft.CSharp.dll`"",
    "/r:`"$libs\SolidWorks.Interop.sldworks.dll`"",
    "/r:`"$libs\SolidWorks.Interop.swconst.dll`"",
    "/r:`"$libs\SolidWorks.Interop.swpublished.dll`""
)
$argFile = "$proj\build_swai.rsp"
# 程序集名 = 输出文件基名。必须避开蓝色插件的程序集名 "SwAIAddin"：
# CLR 程序集名不区分大小写，同名同版本(PublicKeyToken=null)的两个 DLL 在同一进程/AppDomain 内互斥，
# 先加载者独占，后者 CoCreate 时抛 0x80131522 TypeLoadException —— 插件对话框勾选被弹回的根因
$asmName = 'SWAIPlugin.dll'
$lines = @(
    '/nologo',
    '/target:library',
    '/platform:anycpu',
    '/langversion:8.0',
    '/optimize+',
    '/debug:pdbonly',
    "/out:`"$outDir\$asmName`""
) + $refs + ($src | ForEach-Object { "`"$_`"" })
[System.IO.File]::WriteAllLines($argFile, $lines)

Write-Output '=== Compiling with Roslyn csc ==='
& $csc "@$argFile"
if ($LASTEXITCODE -ne 0) { throw "BUILD FAILED, exit $LASTEXITCODE" }
Write-Output '=== BUILD OK ==='
Get-Item "$outDir\$asmName" | Select-Object FullName, Length, LastWriteTime | Format-List

# ──── 3. 部署到 Program Files（独立目录，与另外两个插件共存互不干扰） ────
New-Item -ItemType Directory -Force -Path $deployDir | Out-Null
# 撤销旧程序集名（SwAIAddin→SWAIPlugin 改名前的遗留注册与文件）
$oldDll = Join-Path $deployDir 'SWAIAddin.dll'
if (Test-Path $oldDll) {
    & 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe' $oldDll /u 2>$null
    Remove-Item $oldDll -Force
    Write-Output '  [ok] old SWAIAddin.dll unregistered and removed'
}
Copy-Item "$outDir\$asmName" (Join-Path $deployDir $asmName) -Force
Write-Output "  [ok] deployed: $deployDir\$asmName"
# Interop DLL 必须与主 DLL 同目录，RegAsm 反射加载和 SolidWorks 运行时都需要
foreach ($dll in $needed) {
    Copy-Item (Join-Path $libs $dll) (Join-Path $deployDir $dll) -Force
}
Write-Output '  [ok] interop DLLs deployed alongside'

# ──── 4. RegAsm COM 注册（64 位视图，与其他插件一致） ────
$regasm = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe'
& $regasm (Join-Path $deployDir $asmName) /codebase
if ($LASTEXITCODE -ne 0) { throw "RegAsm FAILED, exit $LASTEXITCODE" }
Write-Output '  [ok] COM registered'

# ──── 5. SolidWorks AddIns 注册表（Title 与另外两个插件区分） ────
$guid = '{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}'
$key = "HKLM:\SOFTWARE\SolidWorks\AddIns\$guid"
New-Item -Path $key -Force | Out-Null
Set-ItemProperty -Path $key -Name 'Title' -Value 'SWAI 参数化建模（法兰/风机）'
Set-ItemProperty -Path $key -Name 'Description' -Value 'sw-ai 项目插件：AI 对话驱动法兰/叶轮/轴流风机参数化建模，连接本地 Python 设计引擎 (127.0.0.1:5757)'
Set-ItemProperty -Path $key -Name 'Startup' -Value 1 -Type DWord
Write-Output "  [ok] AddIns registry: $key (Startup=1)"
# HKCU 启动标志（双保险：用户级开机自动加载）
$hkcuKey = "HKCU:\SOFTWARE\SolidWorks\AddIns\$guid"
New-Item -Path $hkcuKey -Force | Out-Null
Set-ItemProperty -Path $hkcuKey -Name 'Startup' -Value 1 -Type DWord
Write-Output "  [ok] HKCU startup flag: $hkcuKey = 1"
Write-Output '=== INSTALL DONE ==='
