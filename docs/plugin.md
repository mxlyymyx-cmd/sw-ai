# SolidWorks 插件与分发

> C# SolidWorks Add-in（1,918 行）+ PyInstaller 打包的 AI 服务/聊天窗口 + Inno Setup 一键安装包。

---

## 组成

| 组件 | 说明 |
|---|---|
| `plugin/SWAIAddin.cs` 等任务窗格插件 | C# Add-in，工具栏快捷按钮 + 任务窗格，支持 **AI 模式**（自然语言输入）和 **手动模式**（参数面板） |
| `SWAIServer.exe` | Flask API 服务打包为独立 exe（静默后台，无黑窗口，监听 127.0.0.1:5757） |
| `SWAIChat.exe` | 桌面聊天窗口，双击即用，自动拉起本地 AI 服务 |
| `SWAI-Setup-*.exe` | Inno Setup 安装包：注册插件（直接写注册表 32/64 位视图，无 RegAsm 依赖）+ 装服务 + 装聊天窗口 |

- 插件自动连接本地 API 服务（127.0.0.1:5757）
- Interop DLL：CI 从 NuGet 自动下载（`plugin-build.yml`）；本地构建用 `plugin/libs/` 内入库的 DLL
- 详细安装步骤：[plugin/README-install.md](../plugin/README-install.md)

## LLM 配置（三种方式任选）

1. **聊天窗口 ⚙ 设置**：填 API Key 即存
2. **配置文件** `%APPDATA%\SWAI\config.json`：
   ```json
   {"llm_api_key": "sk-...", "llm_api_url": "https://api.deepseek.com/v1/chat/completions", "llm_model": "deepseek-chat"}
   ```
3. **环境变量**：`SWAI_LLM_API_KEY`（旧前缀 `MECHFORGE_LLM_*` 仍兼容读取）

支持任意 OpenAI 兼容接口（DeepSeek / OpenAI / Qwen / 豆包 / Kimi 等）。**不配置也能用**：自动降级为正则解析模式（能识别标准参数格式，多轮对话体验弱）。

## 打包与发布

- 本地一键打包：`build_installer.bat`（MSBuild 编译插件 → PyInstaller 打包服务 → Inno Setup 生成安装包）
- CI：`.github/workflows/plugin-build.yml`（NuGet 拉 Interop DLL → msbuild → pytest 门禁 → PyInstaller → ISCC）
- **Release 仅在打 tag 时发布**（分支 push 只出构建产物，防止重发旧版）

## 已知踩坑史（勿重复交学费）

- 插件不显示：根因是普通电脑没有 .NET SDK，RegAsm.exe 不存在导致 COM 注册静默失败 → 安装包直接手写注册表（32 位 + 64 位视图全写），插件 DLL 用 AnyCPU（32/64 位 SolidWorks 通吃）
- Inno Setup 中文：语言文件按 ANSI 读，需单 BOM UTF-8；Registry GUID 双大括号转义
- 宏执行通道演进：见 [macro-channel.md](macro-channel.md)
