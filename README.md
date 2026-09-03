# SW-AI 🏭

> SolidWorks 参数化设计引擎 — 机械行业 AI 自动化基座
>
> 「你说规格，AI 画图」

SWAI 是一个面向机械设计的 AI 参数化建模工具集，支持从自然语言规格到 SolidWorks 3D 模型的完整自动化流程。目前涵盖法兰、离心风机叶轮、轴流风机、风机选型、性能曲线五个模块，每个设计模块都包含独立的设计计算引擎（含闭环验证）和 SolidWorks COM API 建模能力。全仓库 344 项离线单元测试，CI 打包前强制通过。

---

## 模块

### 🔧 法兰参数化 (`flange/`)
- **4 种法兰类型 × 240 规格**（PN10/16/25/40 × DN10-300 全覆盖）：
  - `plate` 板式平焊 — GB/T 9119-2010
  - `slip_on` 带颈平焊 — GB/T 9116-2010 / HG/T 20592-2009（含颈部 N/H/S 尺寸）
  - `weld_neck` 对焊 — GB/T 9115-2010 / HG/T 20592-2009（锥颈过渡）
  - `blind` 法兰盖 — GB/T 9123-2010
- AI 自然语言→参数提取（LLM + 正则双模式）
  - `"DN100 PN16 带颈平焊法兰，8个螺栓孔"` → 结构化参数
- SolidWorks COM API 旋转建模：4 类型统一轮廓生成 + 螺栓孔圆周阵列切除
- **E2E 体积校验**：SolidWorks 实测体积 vs Pappus 旋转体解析解（含螺栓孔弓形重叠修正），7 组基准偏差 0.000%，基准值固化在单元测试中
- 完整 Pipeline：自然语言 → 参数提取 → 模型生成

### 🌀 离心风机叶轮 (`impeller/`)
- **11 步设计计算引擎**：输入 Q(流量) / P(全压) / n(转速，可缺省自动选型) → 全部设计参数
- **设计闭环验证**（不是拍脑袋给尺寸）：
  - 完整速度三角形：c₁u/c₂u/w₁/w₂ 全链条
  - 欧拉方程回代：理论全压 P_th vs 目标全压，偏差 ±20% 内报警
  - Stodola 滑移修正：μ = 1 − (π/Z)sinβ₂
  - DeHaller 抗分离检查：w₂/w₁ ≥ 0.72
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
- **10 步设计计算引擎**：输入 Q / P / n（可缺省自动选型）→ 全部设计参数
- **设计闭环验证**：
  - 环量归一化：r 加权平均环量 = 目标环量，欧拉全压闭环（±15%）
  - Lieblein 扩散因子：Df ≤ 0.60，超限叶背分离
  - 需用升力系数校验：cl_req ≤ 1.1
  - DeHaller 抗分离检查：w₂/w₁ ≥ 0.72
  - **叶根过载自动修正**：Df/cl_req 超限时自动增大轮毂比 ν 重算（最高 0.70）
- **7 种翼型**支持：
  - CLARK-Y — 通用翼型，升力特性好，制造容易【最常用】
  - LS-0413 / LS-0409 — 薄翼型，适合低压/高速轴流
  - RAF-30 / RAF-38 — 经典厚翼型，高升力/高压轴流
  - NACA 4412 / NACA 2412 — 低速通用
- **环量分布可选**：等环量 (equal) / 线性 (linear) / 变环量 (variable)
- **全三维叶片坐标生成**：沿叶高多个截面计算弦长、安装角、扭角
- VBA 宏输出：截面放样 + 阵列

### 🎯 风机选型 (`fan_selector.py`)
- 输入 Q / P，**自动推荐机型（离心 vs 轴流）和转速**
- 5 档标准电机转速（2900/1450/960/730/580 r/min）全组合试算
- 综合评分：欧拉闭环偏差 + 设计警告 + 比转速适配 + 叶尖速度（噪音）+ 预期效率
- 输出候选方案对比表 + 选型建议
- CLI / API / AI 对话三层入口全部支持

### 📈 性能曲线 (`perf.py`)
- 从设计结果生成整机 **P-Q / η-Q / N-Q 全性能曲线**
- 离心：按叶型区分的无量纲 ψ 形状（Eck 归一化）
- **实测数据标定**（非纯理论估算）：
  - 4-72（后向）/ 9-19（前向）/ 典型轴流风机样本点校准滑移与效率系数
  - 曲线峰值压力/流量/效率对齐样本点，标定偏差固化在 `tests/test_perf_calibration.py`
- 轴流：陡压曲线 + **失速边界标注** + 稳定裕度计算
- 相似律变转速换算：Q∝n，P∝n²，N∝n³
- CSV + SVG 图表导出（可直接放设计报告）

---

## ⌨️ CLI 用法

```bash
# 法兰
python main.py query DN100 PN16                   # 查询法兰参数（离线）
python main.py extract "DN100 PN16 平焊法兰"      # AI 提取参数
python main.py generate DN100 PN16                # 生成 SW 3D 模型（默认板式平焊）
python main.py generate DN100 PN16 --type slip_on     # 带颈平焊法兰
python main.py generate DN100 PN16 --type weld_neck   # 对焊法兰（锥颈）
python main.py generate DN100 PN16 --type blind       # 法兰盖（盲板）

# 离心风机叶轮
python main.py fan -Q 5000 -P 2500 -n 1450                   # 整机设计
python main.py fan -Q 5000 -P 2500                            # 转速自动选型
python main.py fan -Q 5000 -P 2500 --type airfoil --volute   # 机翼型 + 蜗壳
python main.py fan -Q 5000 -P 2500 --curve                    # 附性能曲线 CSV+SVG

# 轴流风机
python main.py axial -Q 30000 -P 800 -n 1450                 # 轴流设计
python main.py axial -Q 30000 -P 800                          # 转速自动选型
python main.py axial -Q 50000 -P 300 --airfoil ls_0413       # 低压轴流
python main.py axial -Q 50000 -P 300 --circulation variable --nu 0.5  # 变环量+指定轮毂比

# 风机选型（不知道用离心还是轴流？）
python main.py select -Q 20000 -P 800            # 机型 + 转速推荐 + 候选对比表
python main.py select -Q 20000 -P 800 --curve    # 附推荐方案性能曲线
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
│  AI 意图识别         │   ← LLM + 正则双模式
│  （缺转速→自动选型）   │
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  风机选型 fan_selector │   ← 机型 + 转速推荐（多方案评分）
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  设计计算引擎         │   ← 离心/轴流 专业计算
│  + 闭环验证          │      欧拉方程 + 滑移 + Lieblein
└────┬───────────────┘
     │
     ▼
┌────────────────────┐
│  性能曲线 perf        │   ← P-Q/η-Q 曲线 + 失速边界
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

## 🧪 开发与测试

```bash
pip install pytest
python -m pytest tests/ -q          # 全量运行，约 0.5s
```

**344 项单元测试，纯离线**（不需要 SolidWorks / LLM / 网络），覆盖：

| 测试文件 | 内容 | 数量 |
|----------|------|------|
| `test_flange_standards.py` | 4 类型 × 4 PN × DN10-300 全表几何不变量 + 关键规格 spot check | 253 |
| `test_flange_generator.py` | 半剖轮廓结构、螺栓孔几何、SolidWorks E2E 体积基准回归 | 42 |
| `test_fan_selector.py` | 比转速公式、6 类典型工况选型、评分排序、prefer 强制机型 | 17 |
| `test_perf_calibration.py` | 性能曲线标定点回归（4-72/9-19/轴流样本点偏差） | 16 |
| `test_ai_chat.py` | 正则模式意图识别、4 类法兰参数提取、转速缺省自动选型、LLM JSON 解析 | 16 |

体积基准值来自 SolidWorks 2022 实测（见 `e2e_flange.py`），几何回归 = 解析解逐位对比。

**CI**：`.github/workflows/build.yml` 与 `plugin-build.yml` 在打包前强制跑 `pytest`，测试不过不放行。

---

## 项目统计

| 指标 | 数值 |
|------|------|
| 总代码行数 | 11,867 |
| Python（引擎） | 9,264 行 |
| Python（测试） | 856 行 |
| C#（插件） | 1,747 行 |
| 单元测试 | 344 项（全离线，<1s） |
| 模块数 | 5（法兰 / 叶轮 / 轴流 / 选型 / 性能曲线） |
| 法兰规格 | 240（4 类型 × PN10/16/25/40 × DN10-300） |
| 叶轮叶型 | 5（前向/径向/径向出口/后向/机翼型） |
| 轴流翼型 | 7（CLARK-Y/LS×2/RAF×2/NACA×2） |
| 设计校验 | 欧拉闭环 + Stodola 滑移 + Lieblein + DeHaller + E2E 体积 |
| 协议 | MIT |

---

## 📄 许可证

MIT License
