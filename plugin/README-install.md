# SWAI 🏭 SolidWorks AI 插件安装说明

SWAI 是一个带 **AI 对话能力**的 SolidWorks 参数化设计插件：
- 💬 **AI 对话 Tab**：打开 SolidWorks 任务面板，直接和 AI 对话
  - "设计一台离心风机 Q=5000 P=2500 n=1450"
  - "DN100 PN16 平焊法兰"
  - "做个轴流风机 Q=20000 P=800 n=1450"
- 🤖 AI 自动理解需求 → 设计计算 → **自动在 SolidWorks 里建模**（无需手动运行宏）
- 🛠 手动模式：填参数直接生成

架构：
```
SolidWorks 任务面板 (C# 插件)
    │  HTTP (localhost:5757)
    ▼
Python API 服务器 (api.py)
    │  LLM (默认 DeepSeek，可换任意 OpenAI 兼容模型)
    ▼
设计引擎（法兰 / 离心叶轮 / 轴流风机 + 蜗壳）
    │  生成 VBA 宏
    ▼
插件自动执行宏 → 模型直接出现在 SolidWorks ✅
```

## 系统要求

| 组件 | 要求 |
|------|------|
| SolidWorks | 2022+ (x64) |
| .NET Framework | 4.8 Runtime + SDK (或 VS 2022 Build Tools) |
| Python | 3.10+ |
| 操作系统 | Windows 10/11 x64 |

## 快速安装

### Step 1: 安装 Python 依赖并启动 API 服务器

```bash
cd projects/solidworks-parametric
pip install -r requirements-plugin.txt

# 启动 API 服务器（保持运行）
python api.py --port 5757
```

终端应显示：
```
SWAI API Server 🏭
=======================================================
API Base:  http://127.0.0.1:5757/api
```

### Step 2: 配置 AI 对话（可选，推荐）

**方式一：插件内配置（推荐）**
1. SolidWorks 里打开 SWAI 面板 → 「AI 对话」Tab → 点「⚙ 设置」
2. 填入 DeepSeek API Key（[platform.deepseek.com](https://platform.deepseek.com) 获取）
3. 保存即可，无需重启

**方式二：手动配置文件**
创建 `%APPDATA%\SWAI\config.json`：
```json
{"llm_api_key": "sk-你的key", "llm_api_url": "https://api.deepseek.com/v1/chat/completions", "llm_model": "deepseek-chat"}
```

**方式三：环境变量**
```cmd
set MECHFORGE_LLM_API_KEY=sk-你的key
```

> 💡 不配置也能用：自动降级为正则解析模式（能识别标准参数格式，但多轮对话体验弱）。
> 💡 支持任意 OpenAI 兼容接口：改 `llm_api_url` + `llm_model` 即可（OpenAI / Qwen / 豆包 / Kimi 等）。

### Step 3: 编译并注册插件

**方法 A：使用安装脚本 (推荐)**

以 **管理员身份** 打开 PowerShell：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd projects\solidworks-parametric\plugin
.\install.ps1
```

脚本将自动：
1. 检查 Python 后端健康状态
2. 使用 MSBuild 编译 C# 项目
3. 通过 RegAsm 注册 COM

**方法 B：手动编译注册**

以 **管理员身份** 打开 Developer Command Prompt for VS 2022：

```cmd
cd projects\solidworks-parametric\plugin
msbuild SWAIAddin.csproj /p:Configuration=Release /p:Platform=x64
regasm /codebase bin\x64\Release\SWAIAddin.dll
```

### Step 4: 在 SolidWorks 中加载插件

1. 启动/重启 SolidWorks
2. 菜单栏 → **工具** → **插件**
3. 弹出窗口中勾选 **SWAI Addin**
4. SolidWorks 工具栏出现 **SWAI** 菜单

### Step 5: 使用 — 和 AI 对话

1. 点击菜单栏 **SWAI** → **打开 SWAI 面板**
2. 默认打开「AI 对话 💬」Tab
3. 直接输入需求，例如：
   - `设计一台离心风机 Q=5000 P=2500 n=1450` → 自动建模叶轮 + 蜗壳
   - `DN100 PN16 平焊法兰` → 自动建模法兰
   - `做个轴流风机` → AI 会追问缺的参数
   - `帮我设计一个压力5kPa、流量8000m³/h、转速2900的风机` → AI 自动换算单位
4. AI 回复设计摘要后，**自动在 SolidWorks 中生成 3D 模型**

## 卸载

### 注销 COM

以管理员身份运行：

```cmd
regasm /unregister bin\x64\Release\SWAIAddin.dll
```

### 清理 SolidWorks 注册项

```cmd
reg delete "HKLM\SOFTWARE\SolidWorks\AddIns\{A1B2C3D4-E5F6-7890-ABCD-EF1234567891}" /f
```

### 删除文件

直接删除 `plugin/` 目录即可。

## 常见问题

### Q: 面板显示 "后端未响应"

确保 Python API 服务器正在运行：

```bash
# 检查
curl http://127.0.0.1:5757/api/health
# 预期: {"success":true,"data":{"status":"ok","version":"1.0.0"}}
```

### Q: 自动建模失败 / 宏执行失败

1. SolidWorks → **工具** → **宏** → **安全性**
2. 将安全级别设为 **中** 或 **低**
3. 如果已有数字签名，可设为 **高** 并添加受信任发布者

### Q: 对话返回的内容是灰色（不是绿色）

灰色表示当前用的是**正则降级模式**（未配置 LLM API Key）。
点「⚙ 设置」填入 DeepSeek API Key 后，回复会变绿色（AI 模式）。

### Q: AI 说设计失败 "不在国标数据库中"

法兰有标准范围（GB/T 911X-2010），DN/PN 组合超出范围会提示。
风机（Q/P/n）没有此限制。

### Q: RegAsm 权限不足

确保以 **管理员身份** 运行命令行。

### Q: 编译错误 "SolidWorks.Interop 引用找不到"

检查 SolidWorks Interop DLL 路径：

```
C:\Program Files\SolidWorks Corp\SolidWorks\api\redist\
```

如果路径不同，编辑 `SWAIAddin.csproj` 中的 HintPath。

### Q: 任务面板内容滚动/显示不全

面板高度默认 494px，可拖拽 SolidWorks 任务窗格边框调整宽度（≥320px）。

## 调试

查看 SolidWorks 输出日志：

```csharp
// 在代码中:
System.Diagnostics.Debug.WriteLine("[SWAI] 调试信息");
// 用 DebugView (Sysinternals) 查看
```

查看 API 服务器日志：

```bash
python api.py --port 5757 --debug
```

## 文件结构

```
plugin/
├── SWAIAddin.csproj          # C# 项目文件 (.NET 4.8)
├── SWAIAddin.cs              # 插件主入口 (ISwAddin)
├── TaskPaneControl.cs             # 任务面板逻辑（AI 对话 + 手动模式）
├── TaskPaneControl.Designer.cs    # 任务面板布局
├── SettingsDialog.cs              # AI 设置对话框（API Key 配置）
├── ApiClient.cs                   # HTTP API 客户端（含 ChatAsync）
├── SwApiHelper.cs                 # SolidWorks API 辅助（自动执行宏）
├── install.ps1                    # 安装脚本
└── README-install.md              # 本文件

后端：
├── api.py                         # Flask API 服务器 (localhost:5757)
├── ai_chat.py                     # AI 对话引擎（意图识别 + 设计 + 宏生成）
├── flange/  impeller/  axial/     # 设计引擎
└── config.json                    # LLM 配置（可选，或放 %APPDATA%\SWAI\）
```
