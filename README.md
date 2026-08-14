# SW-AI 🏭

> SolidWorks 参数化设计引擎 — 机械行业 AI 自动化基座
>
> 「你说规格，AI 画图」

SWAI 是一个面向机械设计的 AI 参数化建模工具集，支持从自然语言规格到 SolidWorks 3D 模型的完整自动化流程。目前涵盖法兰、离心风机叶轮、轴流风机三个模块，每个模块都包含独立的设计计算引擎和 SolidWorks COM API 建模能力。

---

## 模块

### 🔧 法兰参数化 (`flange/`)
- GB/T 9119-2010（PN10/16/25/40 × DN10-300，共 60 规格）
- 支持 GB/T 9116-2010 带颈平焊法兰、GB/T 9115-2010 对焊法兰
- AI 自然语言→参数提取（LLM + 正则双模式）
  - `"DN100 PN16 平焊法兰，4个螺栓孔"` → 结构化参数
- SolidWorks COM API 自动建模
- 完整 Pipeline：自然语言 → 参数提取 → 模型生成

### 🌀 离心风机叶轮 (`impeller/`)
- **11 步设计计算引擎**：输入 Q(流量) / P(全压) / n(转速) → 全部设计参数
- **5 种叶型**：
  - 前向 (FORWARD) — 低压大流量，高效区窄
  - 径向 (RADIAL) — 中压，结构简单，耐磨
  - 径向出口 (RADIAL_TIP) — 介于径向与后向之间
  - 后向 (BACKWARD) — 高效率，宽工况，低噪音【最常用】
  - 机翼型 (AIRFOIL) — 最高效率，制造复杂
- **叶片型线生成器**：微分步进法，β₁/β₂ 精确匹配
- **蜗壳设计**：等边基元法，72 点外壁型线
- VBA 宏输出：叶片 3D 样条 + 放样 + 阵列

### 🌪️ 轴流风机 (`axial/`)
- **10 步设计计算引擎**：输入 Q / P / n → 全部设计参数
- **5 种翼型**支持：
  - CLARK-Y — 通用翼型，升力特性好，制造容易【最常用】
  - LS-0413 — 薄翼型，适合低压轴流
  - LS-0409 — 超薄翼型，适合高速轴流
  - RAF-30 — 经典厚翼型，高升力
  - RAF-38 — 厚翼型，适合高压轴流
- **全三维叶片坐标生成**：沿叶高多个截面计算弦长、安装角、扭角
- 涡流分布模式可选：等环量 (Free Vortex) / 强制涡 (Forced Vortex)
- VBA 宏输出：截面放样 + 阵列

---

## ⌨️ CLI 用法

```bash
# 法兰
python main.py query DN100 PN16                   # 查询法兰参数（离线）
python main.py extract "DN100 PN16 平焊法兰"      # AI 提取参数
python main.py generate DN100 PN16                # 生成 SW 3D 模型
python main.py generate DN100 PN16 --type neck    # 带颈法兰

# 离心风机叶轮
python main.py fan -Q 5000 -P 2500 -n 1450                   # 整机设计
python main.py fan -Q 5000 -P 2500 -n 1450 --blade backward  # 指定叶型
python main.py fan -Q 3000 -P 1500 -n 2900 --blade airfoil   # 机翼型叶轮

# 轴流风机
python main.py axial -Q 30000 -P 800 -n 1450                 # 轴流设计
python main.py axial -Q 30000 -P 800 -n 1450 --airfoil clark_y  # CLARK-Y 翼型
python main.py axial -Q 50000 -P 500 -n 960 --airfoil ls_0413   # 低压轴流
```

---

## 🌐 API 服务

```bash
pip install -r requirements-plugin.txt
python api.py --port 5757
# → http://127.0.0.1:5757/api
```

API 端点：

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/flange/query` | POST | 查询法兰标准参数 |
| `/api/flange/generate` | POST | 生成法兰 SW 模型 |
| `/api/impeller/design` | POST | 离心叶轮设计计算 |
| `/api/axial/design` | POST | 轴流风机设计计算 |
| `/api/health` | GET | 健康检查 |

---

## 🔌 SolidWorks 插件

C# SolidWorks Add-in，与 API 服务通信：

- 见 `plugin/` 目录
- 安装：以管理员身份运行 `plugin/install.ps1`
- 支持 **AI 模式**（自然语言输入）和 **手动模式**（参数面板）
- 任务窗格集成，工具栏快捷按钮
- 自动连接本地 API 服务（127.0.0.1:5757）

---

## 安装

1. 下载 `SWAI-Setup-1.0.0.exe` 双击安装（自动注册插件 + 安装 AI 服务）
2. 安装完自动打开 **SWAI 聊天窗口**（或双击桌面"SWAI"图标）
3. 在聊天窗口点 **⚙ 设置** 填入 DeepSeek API Key（可选，不填也能用降级模式）
4. 在 SolidWorks 中：**工具 → 插件 → 勾选 SWAI Addin**，右侧任务面板同样可以对话

> 聊天窗口会自动启动后台 AI 服务（无黑窗口），SolidWorks 插件与聊天窗口共用同一个服务。

## 架构

```
用户输入（自然语言 / CLI / API）
        │
        ▼
┌────────────────────┐
│  AI 参数提取 Pipeline │   ← LLM + 正则双模式
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  参数模型 & 标准库    │   ← dataclass 标准化
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  设计计算引擎        │   ← 叶轮/轴流 专业计算
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  SolidWorks 生成器   │   ← COM API 自动建模
└────────────────────┘
     │
     ▼
   3D 模型 + 工程图
```

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总代码行数 | 7,905 |
| Python | 6,153 行 |
| C# | 1,533 行 |
| 模块数 | 3（法兰 / 叶轮 / 轴流） |
| 法兰规格 | 60（GB/T 9119-2010, PN10/16/25/40, DN10-300） |
| 叶轮叶型 | 5（前向/径向/径向出口/后向/机翼型） |
| 轴流翼型 | 5（CLARK-Y/LS/RAF/自定义） |
| 协议 | MIT |

---

## 📄 许可证

MIT License
