; ─────────────────────────────────────────────────────────────
;  MechForge 🏭 SolidWorks AI 插件 — 安装程序
;  Inno Setup 6 脚本
;  双击安装 → 自动注册 COM + 写入 SolidWorks AddIns 注册表
;  → 开机自启 API 服务 → SolidWorks 里直接勾选使用
; ─────────────────────────────────────────────────────────────

#define MyAppName "MechForge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MechForge"
#define MyAppURL "https://github.com/mxlyymyx-cmd/mech-forge"
#define MyAppExeName "MechForgeAddin.dll"
#define MyServerExeName "MechForgeServer.exe"

; 插件 COM GUID（必须与 MechForgeAddin.cs 中 [Guid] 一致）
#define PluginGUID "{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}"

[Setup]
AppId={{8F3B2A1C-4D5E-4F6A-9B7C-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=MechForge-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyServerExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription=MechForge SolidWorks AI Plugin

[Languages]
Name: "chinesesimplified"; MessagesFile: "langs\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式:"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动 MechForge AI 服务"; GroupDescription: "服务:"

[Files]
; 预编译的插件 DLL（由 GitHub Actions 编译）
Source: "bin\x64\Release\MechForgeAddin.dll"; DestDir: "{app}"; Flags: ignoreversion
; PyInstaller 打包的 Python API 服务（用户无需安装 Python）
Source: "..\dist\MechForgeServer.exe"; DestDir: "{app}"; Flags: ignoreversion
; 说明文档
Source: "README-install.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Registry]
; ── SolidWorks 插件注册表（SolidWorks 靠这个识别插件）──
Root: HKLM; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: "LoadAtStartup"; ValueData: 1; Flags: uninsdeletekey
; 64 位视图注册（SolidWorks 2022+ 是 64 位）
Root: HKLM64; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM64; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: "LoadAtStartup"; ValueData: 1; Flags: uninsdeletekey

; ── 开机自启 API 服务 ──
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MechForgeServer"; ValueData: """{app}\{#MyServerExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; ── 注册 COM（regasm /codebase）──
Filename: "{dotnet4064}\RegAsm.exe"; Parameters: "/codebase ""{app}\{#MyAppExeName}"""; Flags: runhidden; StatusMsg: "正在注册 COM 组件..."; Check: IsWin64
Filename: "{dotnet4032}\RegAsm.exe"; Parameters: "/codebase ""{app}\{#MyAppExeName}"""; Flags: runhidden; StatusMsg: "正在注册 COM 组件..."; Check: not IsWin64

; ── 立即启动 API 服务 ──
Filename: "{app}\{#MyServerExeName}"; Description: "启动 MechForge AI 服务"; Flags: nowait postinstall skipifsilent

; ── 打开说明文档 ──
Filename: "{app}\README-install.md"; Description: "查看使用说明"; Flags: postinstall nowait skipifsilent shellexec

[Icons]
Name: "{group}\启动 MechForge AI 服务"; Filename: "{app}\{#MyServerExeName}"
Name: "{group}\使用说明"; Filename: "{app}\README-install.md"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyServerExeName}"; Tasks: desktopicon

[UninstallRun]
; 注销 COM
Filename: "{dotnet4064}\RegAsm.exe"; Parameters: "/unregister ""{app}\{#MyAppExeName}"""; Flags: runhidden; Check: IsWin64
Filename: "{dotnet4032}\RegAsm.exe"; Parameters: "/unregister ""{app}\{#MyAppExeName}"""; Flags: runhidden; Check: not IsWin64

[UninstallDelete]
; 清理服务运行时产生的日志/配置（含 %APPDATA% 下的 config.json，里面有用户 API Key）
Type: filesandordirs; Name: "{localappdata}\MechForge"
Type: filesandordirs; Name: "{userappdata}\MechForge"
Type: filesandordirs; Name: "{app}"

[Code]
{ 安装前检查 SolidWorks 是否安装（仅警告，不阻止） }
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
end;

{ 安装完成后提示用户 }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if MsgBox('MechForge 安装完成！' #13#13 +
              '请重启 SolidWorks，然后：' #13#13 +
              '  工具 → 插件 → 勾选 "MechForge Addin"' #13#13 +
              '现在打开 SolidWorks 试试？',
              mbInformation, MB_YESNO) = IDYES then
    begin
    end;
  end;
end;
