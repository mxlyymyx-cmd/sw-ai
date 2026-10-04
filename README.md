# SW-AI 🏭

> SolidWorks 参数化设计引擎 — 机械行业 AI 自动化基座
>
> 「你说规格，AI 画图」

SWAI 是一个面向机械设计的 AI 参数化建模工具集，支持从自然语言规格到 SolidWorks 3D 模型的完整自动化流程。涵盖法兰、离心风机叶轮、轴流风机、风机选型、性能曲线五个模块，每个设计模块都包含独立的设计计算引擎（含闭环验证）和 SolidWorks COM API 建模能力。全仓库 417 项离线单元测试，CI 打包前强制通过。

> 📦 v2 起仓库分层：**`swai/` 引擎**（可 `pip install`）/ **`app/` 应用**（服务/聊天/CLI）/ **`cad/` 真机脚本**。引擎计算代码与 v1.0.2 逐字节一致，由测试守护。

---

## 仓库结构

```
swai/          引擎包（pip install swai-engine）
  ├── flange/     法兰：GB/T 查表 + 参数化建模（4 类型 × 240 规格）
  ├── impeller/   离心叶轮：11 步设计计算 + 蜗壳（设计闭环验证）
  └── axial/      轴流风机：10 步设计计算（Lieblein 扩散因子校验）
app/           应用层
  ├── api.py      Flask API 服务（127.0.0.1:5757，CORS 仅本机来源）
  ├── ai_chat.py  LLM 对话（DeepSeek 等 OpenAI 兼容接口，无 key 自动降级正则）
  ├── chat_gui.py 桌面聊天窗口（双击即用，自动拉起服务）
  ├── main.py     CLI
  ├── fan_selector.py  风机选型（离心 vs 轴流 + 转速推荐）
  └── perf.py     性能曲线（P-Q / η-Q，实测样本标定）
cad/           SolidWorks 真机脚本（E2E 体积校验、宏工具）
plugin/        C# SolidWorks 插件 + Inno Setup 安装包
tests/         344 项离线单元测试（不需要 SolidWorks / LLM / 网络）
docs/          详细文档（engine / plugin / macro-channel）
```

---

## ⌨️ CLI 用法

```bash
# 法兰
python app/main.py query DN100 PN16                   # 查询法兰参数（离线）
python app/main.py extract "DN100 PN16 平焊法兰"      # AI 提取参数
python app/main.py generate DN100 PN16                # 生成 SW 3D 模型（默认板式平焊）
python app/main.py generate DN100 PN16 --type weld_neck   # 对焊法兰（锥颈）

# 离心风机叶轮
python app/main.py fan -Q 5000 -P 2500 -n 1450                   # 整机设计
python app/main.py fan -Q 5000 -P 2500 --type airfoil --volute   # 机翼型 + 蜗壳
python app/main.py fan -Q 5000 -P 2500 --curve                   # 附性能曲线 CSV+SVG

# 轴流风机
python app/main.py axial -Q 30000 -P 800 -n 1450                 # 轴流设计
python app/main.py axial -Q 50000 -P 300 --airfoil ls_0413       # 低压轴流

# 风机选型（不知道用离心还是轴流？）
python app/main.py select -Q 20000 -P 800            # 机型 + 转速推荐 + 候选对比表
```

---

## 🌐 API 服务

```bash
pip install -r requirements-plugin.txt
python app/api.py --port 5757
# → http://127.0.0.1:5757/api
```

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/models` | GET | 支持的零件类型与参数 |
| `/api/chat` | POST | AI 多轮对话（意图→设计→宏） |
| `/api/nlp` | POST | 自然语言 → 结构化参数 |
| `/api/design/flange` | POST | 法兰设计计算 |
| `/api/design/impeller` | POST | 离心叶轮设计（n 可缺省自动选型） |
| `/api/design/axial` | POST | 轴流风机设计（n 可缺省自动选型） |
| `/api/design/select` | POST | 风机选型（离心 vs 轴流 + 转速推荐） |
| `/api/design/curve` | POST | 性能曲线（P-Q + η-Q + 失速边界） |
| `/api/macro` | POST | 生成 VBA 宏代码 |

---

## 📦 引擎作为库使用

```bash
pip install -e .            # 仓库根目录执行
pip install -e .[com]       # 连同 SolidWorks COM 驱动（pywin32）一起装
```

```python
from swai.impeller.design import design_impeller
from swai.flange.gb_standards import lookup

result = design_impeller(ImpellerDesignInput(Q=5000, P=2500, n=1450))
flange = lookup(dn=100, pn=16)
```

> 引擎不装 pywin32 也能完成全部设计计算与测试（COM 延迟导入），只有真机生成 3D 模型需要 `.[com]`。

---

## 🔌 SolidWorks 插件与安装包

C# Add-in（任务窗格 + AI/手动双模式）+ 一键安装包，详见 [docs/plugin.md](docs/plugin.md) 与 [plugin/README-install.md](plugin/README-install.md)。

1. 下载 `SWAI-Setup-*.exe` 双击安装（自动注册插件 + 安装 AI 服务）
2. 聊天窗口 ⚙ 设置填入 DeepSeek API Key（可选，不填走降级模式）
3. SolidWorks 中：工具 → 插件 → 勾选 SWAI Addin

---

## 架构

```
用户输入（自然语言 / CLI / API）
        │
        ▼
┌────────────────────┐
│  AI 意图识别         │   ← LLM + 正则双模式（app/ai_chat）
│  （缺转速→自动选型）   │
└────┬───────────────┘
     ▼
┌────────────────────┐
│  风机选型            │   ← app/fan_selector（机型 + 转速多方案评分）
└────┬───────────────┘
     ▼
┌────────────────────┐
│  设计计算引擎 swai/   │   ← 欧拉方程闭环 + Stodola 滑移
│  （含闭环验证）       │      + Lieblein 扩散因子 + DeHaller 数
└────┬───────────────┘
     ▼
┌────────────────────┐
│  性能曲线 app/perf   │   ← P-Q/η-Q 曲线 + 失速边界（实测标定）
└────┬───────────────┘
     ▼
┌────────────────────┐
│  SolidWorks 生成器   │   ← COM API 自动建模 / cscript+VBS 宏通道
└────────────────────┘
     ▼
   3D 模型 + 工程图
```

---

## 🧪 开发与测试

```bash
pip install pytest
python -m pytest tests/ -q          # 全量运行，约 0.5s
```

**417 项单元测试，纯离线**（不需要 SolidWorks / LLM / 网络）。测试覆盖明细与引擎各模块的验证方法（欧拉闭环 / E2E 体积基准 / 实测标定）见 [docs/engine.md](docs/engine.md)；SolidWorks 宏通道的演进史与真机实测记录见 [docs/macro-channel.md](docs/macro-channel.md)。

**CI**：`.github/workflows/build.yml`（SWAI.exe 打包）与 `plugin-build.yml`（插件安装包）在打包前强制跑 `pytest`，测试不过不放行；安装包 Release 仅在打 tag 时发布。

---

## 📄 许可证

MIT License
