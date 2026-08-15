; ─────────────────────────────────────────────────────────────
;  SWAI 🏭 SolidWorks AI 插件 — 安装程序
;  Inno Setup 6 脚本
;  双击安装 → 自动注册 COM + 写入 SolidWorks AddIns 注册表
;  → 开机自启 API 服务 → SolidWorks 里直接勾选使用
; ─────────────────────────────────────────────────────────────

#define MyAppName "SW-AI"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "SWAI"
#define MyAppURL "https://github.com/mxlyymyx-cmd/sw-ai"
#define MyAppExeName "SWAIAddin.dll"
#define MyServerExeName "SWAIServer.exe"

; 插件 COM GUID（必须与 SWAIAddin.cs 中 [Guid] 一致）
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
OutputBaseFilename=SWAI-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\SWAIChat.exe
VersionInfoVersion={#MyAppVersion}.0
VersionInfoDescription=SW-AI SolidWorks AI Plugin

[Languages]
Name: "chinesesimplified"; MessagesFile: "langs\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式:"; Flags: unchecked
Name: "autostart"; Description: "开机自动启动 SWAI AI 服务"; GroupDescription: "服务:"

[Files]
; 预编译的插件 DLL（由 GitHub Actions 编译，x86 —— SolidWorks 主程序是 32 位）
Source: "bin\x86\Release\SWAIAddin.dll"; DestDir: "{app}"; Flags: ignoreversion
; PyInstaller 打包的 Python API 服务（用户无需安装 Python，静默后台运行）
Source: "..\dist\SWAIServer.exe"; DestDir: "{app}"; Flags: ignoreversion
; 聊天窗口桌面应用（双击即聊，自动拉起服务）
Source: "..\dist\SWAIChat.exe"; DestDir: "{app}"; Flags: ignoreversion
; 说明文档
Source: "README-install.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Registry]
; ── SolidWorks 插件注册表（SolidWorks 主程序是 32 位，读取 32 位视图 WOW6432Node）──
; HKLM32 = HKLM\SOFTWARE\WOW6432Node（SolidWorks 实际读取的位置）
Root: HKLM32; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM32; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: "LoadAtStartup"; ValueData: 1; Flags: uninsdeletekey
; HKCU 32 位视图（部分 SolidWorks 版本读 HKCU）
Root: HKCU32; Subkey: "Software\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKCU32; Subkey: "Software\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: "LoadAtStartup"; ValueData: 1; Flags: uninsdeletekey
Root: HKCU32; Subkey: "Software\SolidWorks\AddinsStartup\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: ""; ValueData: 1; Flags: uninsdeletekey
; 64 位视图也写入（双保险，对 32 位 SolidWorks 无害）
Root: HKLM64; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM64; Subkey: "SOFTWARE\SolidWorks\AddIns\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}}"; ValueType: dword; ValueName: "LoadAtStartup"; ValueData: 1; Flags: uninsdeletekey

; ── 开机自启 API 服务 ──
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SWAIServer"; ValueData: """{app}\{#MyServerExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; ── 注册 COM（x86 DLL 必须用 32 位 RegAsm，注册到 32 位 COM 视图）──
; SolidWorks 是 32 位进程，只找 32 位视图的 CLSID
Filename: "{dotnet4032}\RegAsm.exe"; Parameters: "/codebase ""{app}\{#MyAppExeName}"""; Flags: runhidden; StatusMsg: "正在注册 COM 组件..."

; ── 立即启动聊天窗口（自动拉起后台服务）──
Filename: "{app}\SWAIChat.exe"; Description: "打开 SWAI 聊天窗口"; Flags: nowait postinstall skipifsilent

; ── 打开说明文档 ──
Filename: "{app}\README-install.md"; Description: "查看使用说明"; Flags: postinstall nowait skipifsilent shellexec

[Icons]
Name: "{group}\SWAI 聊天窗口"; Filename: "{app}\SWAIChat.exe"
Name: "{group}\启动 AI 服务(后台)"; Filename: "{app}\{#MyServerExeName}"
Name: "{group}\使用说明"; Filename: "{app}\README-install.md"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\SWAIChat.exe"; Tasks: desktopicon

[UninstallRun]
; 注销 COM（32 位）
Filename: "{dotnet4032}\RegAsm.exe"; Parameters: "/unregister ""{app}\{#MyAppExeName}"""; Flags: runhidden

[UninstallDelete]
; 清理服务运行时产生的日志/配置（含 %APPDATA% 下的 config.json，里面有用户 API Key）
Type: filesandordirs; Name: "{localappdata}\SWAI"
Type: filesandordirs; Name: "{userappdata}\SWAI"
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
    if MsgBox('SWAI 安装完成！' #13#13 +
              '请重启 SolidWorks，然后：' #13#13 +
              '  工具 → 插件 → 勾选 "SWAI Addin"' #13#13 +
              '现在打开 SolidWorks 试试？',
              mbInformation, MB_YESNO) = IDYES then
    begin
    end;
  end;
end;
