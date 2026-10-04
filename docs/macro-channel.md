# SolidWorks 宏通道与真机实测记录

> 引擎生成 3D 模型走"宏代码 → SolidWorks 执行"路线。本文记录宏通道的三代演进、
> 真机（SolidWorks 2022）实测验证记录，以及调试期探针的归档位置。

---

## 宏通道三代演进

| 代 | 方案 | 结局 |
|---|---|---|
| 1 | 生成 `.swp` 纯文本假头 + `RunMacro2` | ❌ SolidWorks 的 .swp 是 VBA 工程二进制格式，纯文本假头不可能被接受 |
| 2 | 生成 VBA 模块（Module1）+ `RunMacro2` | ⚠️ "无法打开宏文件"——宏文件路径/编码/模块名声明处处是坑（ANSI 编码、Module1 声明等各自修过一轮） |
| 3 | **cscript/VBS 通道**（现行，3a119bf） | ✅ 插件生成 VBS 脚本，`cscript` 执行；VBS 侧 `GetObject` 附着已开 SolidWorks，绕开宏工程格式问题 |

配套工具 `cad/vba_to_vbs.py`：VBA 宏 → VBS 的转换器。

调试期写过 22 个一次性探针（`tools/probe/`，1,698 行），2026-10 已从仓库清除；
代表性样本 `macro_probe.vbs/.ps1` 与推送兜底工具归档在 `docs/legacy/`，
全套从 git 历史（`v1.0.2-final` tag）可找回。

## 真机实测验证记录（SolidWorks 2022）

| 验证项 | 方法 | 结果 |
|---|---|---|
| 法兰建模 | 7 组基准件实测体积 vs Pappus 旋转体解析解（含螺栓孔弓形重叠修正），脚本 `cad/e2e_flange.py` | **偏差 0.000%**，基准值固化在 `tests/test_flange_generator.py` |
| 蜗壳建模 | 72 点外壁型线配方按 SW2022 实测重写（commit 2e969d1，117 行） | 通过 |
| 叶轮建模 | COM 步骤 2-6（盖板/叶片样条/放样/圆周阵列）补全（55f0e47） | 通过 |
| 轴流建模 | `_test_axial_loop.py` 循环验证（已随探针归档） | 通过 |

> ⚠️ COM 生成路径只有真机能验证。改 `swai/*/generator.py` 或 `cad/` 下任何脚本后，
> 务必在装有 SolidWorks 的机器上跑一次 `python -m pytest tests/ -q`（离线基准回归）
> 加一轮真机 E2E，再发布。

## 引擎收编同步规则（给下游 mechmind）

`swai/` 三包是整条产品线的引擎唯一正版（source of truth）。下游项目收编引擎时：
- 从本仓库 `v2` 分支整体拷贝 `swai/`（包内全是相对 import，整体拷贝即可运行）
- 引擎改动在本仓库做、344 测试绿后再拷入下游；不要双头改
