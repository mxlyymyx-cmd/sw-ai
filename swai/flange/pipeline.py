"""
完整 Pipeline：自然语言 → 3D 模型

编排 AI 提取 → 国标查表 → SolidWorks 生成的完整流程。
"""

import os
import json
import time
from typing import Optional, Callable

from .params import FlangeParams, ExtractionResult, FlangeType
from .gb_standards import lookup, list_available, is_supported
from .ai_extractor import extract
from .generator import generate_flange, generate_sw_macro, HAS_PYWIN32


class FlangePipeline:
    """
    法兰盘自动生成 Pipeline

    使用示例:
        pipe = FlangePipeline()
        result = pipe.run("DN100 PN16 平焊法兰")
        if result["success"]:
            print(f"模型已保存: {result['output_path']}")
    """

    def __init__(self, dry_run: bool = False):
        """
        Args:
            dry_run: 仅输出参数，不实际生成模型
        """
        self.dry_run = dry_run
        self.history: list[dict] = []

    def run(
        self,
        user_input: str,
        output_dir: str = ".",
        on_extract: Optional[Callable] = None,
        on_generate: Optional[Callable] = None,
    ) -> dict:
        """
        执行完整流程

        Args:
            user_input: 用户自然语言描述
            output_dir: 模型输出目录
            on_extract: 参数提取后的回调 (params) -> None
            on_generate: 生成前的回调 (params) -> None

        Returns:
            {
                "success": bool,
                "params": FlangeParams | None,
                "output_path": str | None,
                "macro_path": str | None,
                "extraction": ExtractionResult,
                "duration": float,
                "error": str | None,
            }
        """
        start_time = time.time()
        result = {
            "success": False,
            "params": None,
            "output_path": None,
            "macro_path": None,
            "extraction": None,
            "duration": 0.0,
            "error": None,
        }

        print("=" * 60)
        print(f"  法兰 Pipeline | 输入: {user_input}")
        print("=" * 60)

        # ── Step 1: AI 参数提取 ──
        print("\n[Step 1/3] AI 参数提取...")
        extraction = extract(user_input)

        if not extraction.success:
            result["error"] = extraction.error
            result["extraction"] = extraction
            result["duration"] = time.time() - start_time
            print(f"  ❌ 提取失败: {extraction.error}")
            self.history.append(result)
            return result

        params = extraction.params
        result["params"] = params
        result["extraction"] = extraction
        print(f"  ✅ DN{params.dn} PN{params.pn} | {params.flange_type.value} | {params.material}")
        print(f"    外径 {params.d} × {params.c}mm | 螺栓 {params.n}×ø{params.l}")

        if on_extract:
            on_extract(params)

        # ── Step 2: 校验参数 ──
        print("\n[Step 2/3] 参数校验...")
        issues = self._validate(params)
        if issues:
            for issue in issues:
                print(f"  ⚠️  {issue}")
        else:
            print("  ✅ 参数合理")

        # ── Step 3: 生成模型 ──
        print(f"\n[Step 3/3] 生成模型...")

        # 确定输出路径
        safe_name = f"Flange_DN{params.dn}_PN{params.pn}_{params.flange_type.value}"
        output_path = os.path.join(output_dir, f"{safe_name}.SLDPRT")
        macro_path = os.path.join(output_dir, f"{safe_name}.swp")

        if self.dry_run:
            print("  📋 Dry-run 模式 → 输出参数摘要:")
            print(f"\n{params.summary}")
            result["success"] = True
        else:
            if HAS_PYWIN32:
                # Windows + pywin32 → 直接生成
                try:
                    if on_generate:
                        on_generate(params)
                    actual_path = generate_flange(params, output_path)
                    result["output_path"] = actual_path
                    result["success"] = True
                    print(f"  ✅ 模型已生成: {actual_path}")
                except Exception as e:
                    result["error"] = f"生成失败: {e}"
                    print(f"  ❌ {result['error']}")
                    # 降级：生成 VBA 宏
                    fallback_macro = generate_sw_macro(params)
                    macro_path = macro_path.replace(".swp", ".bas")
                    with open(macro_path, "w", encoding="utf-8") as f:
                        f.write(fallback_macro)
                    result["macro_path"] = macro_path
                    print(f"  📝 已降级输出 VBA 宏: {macro_path}")
            else:
                # 非 Windows → 生成 VBA 宏
                macro = generate_sw_macro(params)
                with open(macro_path, "w", encoding="utf-8") as f:
                    f.write(macro)
                result["macro_path"] = macro_path
                result["success"] = True
                print(f"  ✅ VBA 宏已生成: {macro_path}")

        result["duration"] = time.time() - start_time
        print(f"\n⏱  总耗时: {result['duration']:.2f}s")
        self.history.append(result)
        return result

    def _validate(self, params: FlangeParams) -> list[str]:
        """参数校验"""
        issues = []
        if params.n and params.l and params.k:
            # 检查螺栓孔距合理性
            max_bolt_circ = (params.k - params.l) / 2
            if max_bolt_circ < 5:
                issues.append(f"螺栓孔可能太靠近边缘: PCD={params.k}, 孔径={params.l}")
        if params.c < 2:
            issues.append(f"法兰厚度 {params.c}mm 过薄")
        return issues

    def show_history(self):
        """显示历史记录"""
        if not self.history:
            print("暂无 Pipeline 历史")
            return
        for i, h in enumerate(self.history, 1):
            status = "✅" if h["success"] else "❌"
            params_info = ""
            if h.get("params"):
                p = h["params"]
                params_info = f"  DN{p.dn} PN{p.pn} {p.flange_type.value}"
            print(f"  {i}. {status} {params_info} | {h['duration']:.1f}s")


def batch_auto(input_file: str, output_dir: str = "."):
    """
    批量自动生成：从文件读取输入列表

    文件格式: 每行一个自然语言描述
    """
    pipe = FlangePipeline()
    os.makedirs(output_dir, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    results = []
    for i, line in enumerate(lines, 1):
        print(f"\n{'─' * 50}")
        print(f"[{i}/{len(lines)}]")
        result = pipe.run(line, output_dir=output_dir)
        results.append(result)

    # 汇总
    success = sum(1 for r in results if r["success"])
    print(f"\n{'=' * 50}")
    print(f"批量完成: {success}/{len(results)} 成功")
    return results
