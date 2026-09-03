#!/usr/bin/env python3
"""
SolidWorks 参数化法兰盘 — CLI 入口

用法:
    # 查询国标参数
    python main.py query DN100 PN16

    # AI 提取参数
    python main.py extract "DN100 PN16 平焊法兰"

    # 生成模型（需要 Windows + SolidWorks）
    python main.py generate DN100 PN16

    # 生成 VBA 宏（在任何平台都可以）
    python main.py macro DN100 PN16 --output ./outputs

    # 批量处理
    python main.py batch input.txt --output-dir ./outputs

    # 列出可用规格
    python main.py list --pn 16

    # 交互模式
    python main.py interactive

    # 轴流风机
    python main.py axial -Q 20000 -P 800 -n 1450
    python main.py axial -Q 20000 -P 800 -n 1450 --macro

    # 风机选型（自动推荐机型 + 转速）
    python main.py select -Q 20000 -P 800
    python main.py select -Q 20000 -P 800 --curve

    # 离心/轴流 不指定转速 → 自动选型
    python main.py fan -Q 5000 -P 2500 --volute
    python main.py axial -Q 50000 -P 300 --circulation equal
"""

import sys
import os
import argparse

# 确保可以导入本包
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flange.params import FlangeParams, FlangeType
from flange.gb_standards import lookup, list_available, is_supported
from flange.ai_extractor import extract
from flange.pipeline import FlangePipeline, batch_auto
from flange.generator import generate_sw_macro

from impeller.params import ImpellerDesignInput, BladeType
from impeller.design import design_impeller, calc_ns, recommend_speed
from impeller.blades import generate_blade_profile, generate_3d_blade, export_csv, export_sw_curve, CurveType
from impeller.generator import generate_vba_macro as gen_impeller_macro, design_and_generate
from impeller.volute import match_impeller, volute_profile, generate_vba_macro as gen_volute_macro

from axial.params import AxialFanInput, AirfoilType as AxialAirfoilType, CirculationType
from axial.design import design_axial_fan, calc_ns as axial_calc_ns, estimate_diameter
from axial.blades import generate_blade_points, export_csv as axial_export_csv, export_sw_curve as axial_export_sw_curve
from axial.generator import generate_vba_macro as gen_axial_macro, design_and_generate as axial_design_and_generate

from fan_selector import select_fan
from perf import perf_curve


def cmd_query(args):
    """查询国标法兰参数"""
    try:
        params = lookup(args.dn, args.pn, args.type)
        print(f"\n📐 {params.standard}")
        print(params.summary)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)


def cmd_extract(args):
    """AI 提取参数"""
    result = extract(args.text)
    if result.success:
        print(f"\n✅ 参数提取成功 (置信度: {result.confidence:.0%})")
        print(result.params.summary)
        if result.notes:
            print("\n💡 提示:")
            for note in result.notes:
                print(f"  • {note}")
    else:
        print(f"\n❌ 提取失败: {result.error}")
        sys.exit(1)


def cmd_generate(args):
    """直接生成（跳过 AI 提取，用指定参数）"""
    try:
        params = lookup(args.dn, args.pn, args.type)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    pipe = FlangePipeline(dry_run=args.dry_run)
    result = pipe.run(
        f"DN{args.dn} PN{args.pn} {args.type}",
        output_dir=args.output_dir,
    )
    if not result["success"] and result.get("error"):
        sys.exit(1)


def cmd_macro(args):
    """生成 VBA 宏（跨平台方案）"""
    try:
        params = lookup(args.dn, args.pn, args.type)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    name = f"Flange_DN{params.dn}_PN{params.pn}_{params.flange_type.value}.bas"
    path = os.path.join(args.output_dir, name)

    macro = generate_sw_macro(params)
    with open(path, "w", encoding="utf-8") as f:
        f.write(macro)

    print(f"✅ VBA 宏已生成: {path}")
    print(f"   在 SolidWorks 中: 工具 → 宏 → 运行 → 选择此文件")


def cmd_list(args):
    """列出可用规格"""
    specs = list_available(pn=args.pn)

    if args.pn:
        print(f"\n📋 GB/T 9119-2010 PN{args.pn} 可用规格:")
    else:
        print(f"\n📋 GB/T 9119-2010 所有可用规格:")

    # 表头
    print(f"{'DN':>5} {'PN':>5} {'外径 D':>8} {'PCD K':>8} {'孔径 L':>6} {'孔数':>5} {'厚度 C':>6} {'内径':>6}")
    print("-" * 55)

    for spec in specs:
        print(f"{spec['dn']:>5} {spec['pn']:>5} {spec['d']:>8} {spec['k']:>8} "
              f"{spec['l']:>6} {spec['n']:>5} {spec['c']:>6} {spec['inner_d']:>6}")

    print(f"\n共 {len(specs)} 个规格")


def cmd_batch(args):
    """批量处理"""
    print(f"📂 批量处理: {args.input_file}")
    results = batch_auto(args.input_file, output_dir=args.output_dir)


def _export_curve(design, Q: float, P: float, n: float, curve_dir: str):
    """导出性能曲线 CSV + SVG"""
    os.makedirs(curve_dir, exist_ok=True)
    curve = perf_curve(design)
    prefix = f"{curve.machine.capitalize()}_{Q:.0f}m3h_{P:.0f}Pa_{n:.0f}rpm"
    csv_path = os.path.join(curve_dir, f"{prefix}_curve.csv")
    svg_path = os.path.join(curve_dir, f"{prefix}_curve.svg")
    curve.export_csv(csv_path)
    curve.export_svg(svg_path)
    print(f"\n📈 性能曲线: {csv_path}")
    print(f"            {svg_path}")


def cmd_select(args):
    """风机选型：机型（离心 vs 轴流）+ 转速推荐"""
    try:
        sel = select_fan(Q=args.Q, P=args.P, prefer=args.prefer)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print(sel.summary)
    if sel.best is None:
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  推荐方案完整设计结果（{sel.best.machine_name} @ {sel.best.n:.0f} r/min）")
    print(f"{'='*55}")
    print(sel.best.design.summary)

    if args.curve:
        _export_curve(sel.best.design, args.Q, args.P, sel.best.n, args.curve_dir)


def cmd_fan_design(args):
    """离心风机叶轮设计（转速缺省时自动选型）"""
    if args.n <= 0:
        sel = select_fan(Q=args.Q, P=args.P, prefer="centrifugal")
        if sel.best is None:
            print(f"❌ 无可行离心方案（Q={args.Q} m³/h, P={args.P} Pa），"
                  f"建议尝试 axial 或 select 命令")
            sys.exit(1)
        args.n = sel.best.n
        print(f"⚙️ 未指定转速 → 自动选型: 离心风机 @ {args.n:.0f} r/min "
              f"(n_s={sel.best.ns:.1f}, 候选 {len(sel.candidates)} 个)")
    inp = ImpellerDesignInput(
        Q=args.Q,
        P=args.P,
        n=args.n,
        blade_type=args.type,
        material=args.material,
    )
    try:
        design = design_impeller(inp)
        print(design.summary)

        # ── 蜗壳匹配 ──
        vol = None
        if args.volute:
            vol = match_impeller(design)
            print(f"\n{'─'*55}")
            print(vol.summary)

        # ── 宏生成 ──
        if args.macro:
            os.makedirs(args.macro_dir, exist_ok=True)
            safe = f"Fan_{args.Q:.0f}m3h_{args.P:.0f}Pa_{args.n:.0f}rpm"

            # 叶轮宏
            imp_macro = gen_impeller_macro(design)
            imp_path = os.path.join(args.macro_dir, f"{safe}_impeller.bas")
            with open(imp_path, "w", encoding="utf-8") as f:
                f.write(imp_macro)
            print(f"\n📜 Impeller macro: {imp_path}")

            # 蜗壳宏
            if vol:
                profile = volute_profile(vol)
                vol_macro = gen_volute_macro(vol, profile)
                vol_path = os.path.join(args.macro_dir, f"{safe}_volute.bas")
                with open(vol_path, "w", encoding="utf-8") as f:
                    f.write(vol_macro)
                print(f"📜 Volute macro: {vol_path}")

        if args.profile:
            r1 = design.D1 / 2
            r2 = design.D2 / 2
            pts = generate_blade_profile(r1, r2, design.beta1, design.beta2, n_points=50)
            pts_3d = generate_3d_blade(pts, design.b1, design.b2)
            export_csv(pts_3d, args.profile)

        # ── 性能曲线导出 ──
        if args.curve:
            _export_curve(design, args.Q, args.P, args.n, args.curve_dir)

    except ValueError as e:
        print(f"❌ 设计失败: {e}")
        sys.exit(1)


def cmd_profile(args):
    """生成叶片型线坐标"""
    pts = generate_blade_profile(
        args.r1, args.r2, args.beta1, args.beta2,
        CurveType.MARCHING, args.points,
    )
    print(f"\n✅ 叶片型线: {len(pts)} 个点")
    print(f"    进口: r={pts[0]['r']}  θ={pts[0]['theta']}°  β={pts[0]['beta']}°")
    print(f"    出口: r={pts[-1]['r']}  θ={pts[-1]['theta']}°  β={pts[-1]['beta']}°")
    print(f"    包角: {pts[-1]['theta']:.1f}°")

    if args.export:
        os.makedirs(os.path.dirname(args.export) or ".", exist_ok=True)
        pts_3d = generate_3d_blade(pts, args.b1 or 50, args.b2 or 50)
        export_csv(pts_3d, args.export)

    if args.sw_curve:
        os.makedirs(os.path.dirname(args.sw_curve) or ".", exist_ok=True)
        pts_3d = generate_3d_blade(pts, args.b1 or 50, args.b2 or 50)
        export_sw_curve(pts_3d, args.sw_curve)


def cmd_fan_ns(args):
    """计算比转速"""
    ns = calc_ns(args.Q, args.P, args.n)
    print(f"\n比转速 n_s = {ns:.1f}")
    if ns < 25:
        print("  建议叶型: 前向")
    elif ns < 55:
        print("  建议叶型: 径向或前向")
    elif ns < 90:
        print("  建议叶型: 后向（最常用）")
    else:
        print("  建议: 双吸入或轴流")


def cmd_fan_speed(args):
    """推荐转速"""
    ns = calc_ns(args.Q, args.P, args.n)
    print(f"\n当前比转速 n_s = {ns:.1f}")
    print(f"  若配 4 极电机 (1450r/min): D₂ ≈ {args.n * 60 * 1000 / (3.14159 * args.n * 2**0.5):.0f}mm 量级")
    print(f"  若配 6 极电机 (960r/min):  外径更大，适合大流量")
    print(f"  若配 2 极电机 (2900r/min): 外径更小，适合高全压")


def cmd_axial_design(args):
    """轴流风机设计（转速缺省时自动选型）"""
    if args.n <= 0:
        sel = select_fan(Q=args.Q, P=args.P, prefer="axial")
        if sel.best is None:
            print(f"❌ 无可行轴流方案（Q={args.Q} m³/h, P={args.P} Pa），"
                  f"建议尝试 fan 或 select 命令")
            sys.exit(1)
        args.n = sel.best.n
        print(f"⚙️ 未指定转速 → 自动选型: 轴流风机 @ {args.n:.0f} r/min "
              f"(n_s={sel.best.ns:.1f}, 候选 {len(sel.candidates)} 个)")
    inp = AxialFanInput(
        Q=args.Q,
        P=args.P,
        n=args.n,
        airfoil=args.airfoil,
        material=args.material,
        sections=args.sections,
        circulation=args.circulation,
        nu=args.nu,
    )
    try:
        design = design_axial_fan(inp)
        print(design.summary)

        # ── 宏生成 ──
        if args.macro:
            os.makedirs(args.macro_dir, exist_ok=True)
            safe = f"Axial_{args.Q:.0f}m3h_{args.P:.0f}Pa_{args.n:.0f}rpm"

            import_path = os.path.join(args.macro_dir, f"{safe}.bas")
            macro = gen_axial_macro(design)
            with open(import_path, "w", encoding="utf-8") as f:
                f.write(macro)
            print(f"\n📜 Axial macro: {import_path}")

            # 导出叶型曲线
            from axial.blades import generate_blade_points as gbp
            from axial.blades import export_sw_curve as esc
            pts = gbp(design.sections, design.airfoil, n_per_section=20)
            curve_path = os.path.join(args.macro_dir, f"{safe}.sldcrv")
            esc(pts, curve_path)
            print(f"📜 Blade curve: {curve_path}")

        # ── 导出曲线 CSV ──
        if args.export:
            os.makedirs(os.path.dirname(args.export) or ".", exist_ok=True)
            pts = generate_blade_points(design.sections, design.airfoil, n_per_section=30)
            axial_export_csv(pts, args.export)

        # ── 性能曲线导出 ──
        if args.curve:
            _export_curve(design, args.Q, args.P, args.n, args.curve_dir)

    except ValueError as e:
        print(f"❌ 设计失败: {e}")
        sys.exit(1)


def cmd_interactive(args):
    """交互模式 — 支持法兰、离心叶轮和轴流风机"""
    from impeller.params import BladeType as BT
    pipe = FlangePipeline()

    print("=" * 60)
    print("  SolidWorks 参数化设计 — 交互模式")
    print("  法兰: 直接输入规格（如: DN100 PN16 平焊法兰）")
    print("  叶轮: fan Q=流量 P=全压 n=转速 [type=叶型]")
    print("  exit 退出  history 查看历史")
    print("=" * 60)

    while True:
        try:
            text = input("\n🐾 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in ("exit", "quit", "q"):
            break
        if text.lower() == "history":
            pipe.show_history()
            continue

        # 叶轮设计模式
        if text.lower().startswith("fan") or text.lower().startswith("叶轮"):
            params = _parse_fan_input(text)
            if "error" in params:
                print(f"  ❌ {params['error']}")
                print("  格式: fan Q=5000 P=2500 n=1450 [type=backward]")
                continue
            inp = ImpellerDesignInput(**params)
            try:
                design = design_impeller(inp)
                print(design.summary)

                # 蜗壳匹配
                vol = match_impeller(design)
                print(f"\n{'─'*45}")
                print(vol.summary)

                # 自动生成宏
                safe = f"Fan_{design.input_params.Q:.0f}m3h_{design.input_params.P:.0f}Pa"
                imp_macro = gen_impeller_macro(design)
                with open(f"./{safe}_impeller.bas", "w", encoding="utf-8") as f:
                    f.write(imp_macro)
                print(f"\n📜 Impeller macro: ./{safe}_impeller.bas")

                profile = volute_profile(vol)
                vol_macro = gen_volute_macro(vol, profile)
                with open(f"./{safe}_volute.bas", "w", encoding="utf-8") as f:
                    f.write(vol_macro)
                print(f"📜 Volute macro: ./{safe}_volute.bas")
            except ValueError as e:
                print(f"  ❌ 设计失败: {e}")
        else:
            # 法兰模式
            result = pipe.run(text)
            if result["macro_path"] and not result.get("output_path"):
                print(f"\n💡 提示: VBA 宏已保存到 {result['macro_path']}")
                print(f"   在 Windows + SolidWorks 上运行此宏即可生成模型")


def _parse_fan_input(text: str) -> dict:
    """解析交互模式中的叶轮输入"""
    import re
    params = {}
    # 提取 key=value 对
    pairs = re.findall(r'(\w+)="*([^"\s]+)"*', text)
    for k, v in pairs:
        k = k.lower()
        if k == "q":
            params["Q"] = float(v)
        elif k == "p":
            params["P"] = float(v)
        elif k == "n":
            params["n"] = float(v)
        elif k == "type":
            params["blade_type"] = v
    if "Q" not in params or "P" not in params or "n" not in params:
        return {"error": "缺少参数，需要 Q(流量) P(全压) n(转速)"}
    return params


def main():
    parser = argparse.ArgumentParser(
        description="SolidWorks 参数化设计 — 机械行业 AI 自动化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 法兰
  python main.py query DN100 PN16                查询国标参数
  python main.py extract "DN100 PN16"             AI 提取
  python main.py generate DN100 PN16              生成模型
  python main.py macro DN100 PN16                 生成 VBA 宏
  python main.py list --pn 16                     列出规格

  # 离心风机叶轮
  python main.py fan -Q 5000 -P 2500 -n 1450      完整设计
  python main.py fan -Q 5000 -P 2500 --volute     转速自动选型 + 蜗壳
  python main.py ns -Q 5000 -P 2500 -n 1450        计算比转速
  python main.py interactive                       交互模式

  # 轴流风机
  python main.py axial -Q 50000 -P 300 -n 960      低压大流量轴流
  python main.py axial -Q 20000 -P 800 -n 1450     中压通用轴流
  python main.py axial -Q 5000 -P 2000 -n 2900     高压轴流
  python main.py axial -Q 20000 -P 800 -n 1450 --macro  轴流设计+宏
  python main.py axial -Q 50000 -P 300 --circulation var --nu 0.5

  # 风机选型
  python main.py select -Q 20000 -P 800            机型+转速推荐
  python main.py select -Q 20000 -P 800 --curve    附性能曲线
        """,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # ── query ──
    p_query = sub.add_parser("query", help="查询国标法兰参数")
    p_query.add_argument("dn", type=int, help="公称通径，如 100")
    p_query.add_argument("pn", type=int, help="公称压力，如 16")
    p_query.add_argument("--type", default="plate", choices=[t.value for t in FlangeType],
                       help="法兰类型 (default: plate)")

    # ── extract ──
    p_extract = sub.add_parser("extract", help="AI 从自然语言提取参数")
    p_extract.add_argument("text", type=str, help="自然语言描述")

    # ── generate ──
    p_gen = sub.add_parser("generate", help="生成 SolidWorks 模型")
    p_gen.add_argument("dn", type=int, help="公称通径")
    p_gen.add_argument("pn", type=int, help="公称压力")
    p_gen.add_argument("--type", default="plate", choices=[t.value for t in FlangeType],
                       help="法兰类型 (default: plate)")
    p_gen.add_argument("--output-dir", default=".", help="输出目录")
    p_gen.add_argument("--dry-run", action="store_true", help="Dry-run，只输出参数")

    # ── macro ──
    p_macro = sub.add_parser("macro", help="生成 VBA 宏（跨平台方案）")
    p_macro.add_argument("dn", type=int, help="公称通径")
    p_macro.add_argument("pn", type=int, help="公称压力")
    p_macro.add_argument("--type", default="plate", choices=[t.value for t in FlangeType],
                        help="法兰类型 (default: plate)")
    p_macro.add_argument("--output-dir", "-o", default="./outputs", help="输出目录")

    # ── list ──
    p_list = sub.add_parser("list", help="列出可用规格")
    p_list.add_argument("--pn", type=int, help="按压力过滤")

    # ── batch ──
    p_batch = sub.add_parser("batch", help="批量处理")
    p_batch.add_argument("input_file", type=str, help="输入文件（每行一个描述）")
    p_batch.add_argument("--output-dir", default="./outputs", help="输出目录")

    # ── interactive ──
    sub.add_parser("interactive", help="交互模式（法兰 + 叶轮）")

    # ── 风机选型 ──
    p_select = sub.add_parser("select", help="风机选型（离心 vs 轴流 + 转速推荐）")
    p_select.add_argument("-Q", type=float, required=True, help="流量 (m³/h)")
    p_select.add_argument("-P", type=float, required=True, help="全压 (Pa)")
    p_select.add_argument("--prefer", default="auto",
                          choices=["auto", "centrifugal", "axial"],
                          help="机型偏好（默认自动）")
    p_select.add_argument("--curve", action="store_true", help="导出性能曲线 CSV + SVG")
    p_select.add_argument("--curve-dir", default="./outputs", help="曲线输出目录")

    # ── 离心风机叶轮设计 ──
    p_fan = sub.add_parser("fan", help="离心风机叶轮设计")
    p_fan.add_argument("-Q", type=float, required=True, help="流量 (m³/h)")
    p_fan.add_argument("-P", type=float, required=True, help="全压 (Pa)")
    p_fan.add_argument("-n", type=float, default=0, help="转速 (r/min，0=自动选型)")
    p_fan.add_argument("--type", default="backward",
                       choices=[t.value for t in BladeType], help="叶型")
    p_fan.add_argument("--material", default="Q235B", help="材料")
    p_fan.add_argument("--macro", action="store_true", help="生成 VBA 宏")
    p_fan.add_argument("--macro-dir", default="./outputs", help="宏输出目录")
    p_fan.add_argument("--profile", type=str, help="导出叶片型线 CSV 路径")
    p_fan.add_argument("--volute", action="store_true", help="匹配蜗壳设计")
    p_fan.add_argument("--curve", action="store_true", help="导出性能曲线 CSV + SVG")
    p_fan.add_argument("--curve-dir", default="./outputs", help="曲线输出目录")

    # ── 比转速 ──
    p_ns = sub.add_parser("ns", help="计算比转速")
    p_ns.add_argument("-Q", type=float, required=True, help="流量 (m³/h)")
    p_ns.add_argument("-P", type=float, required=True, help="全压 (Pa)")
    p_ns.add_argument("-n", type=float, required=True, help="转速 (r/min)")

    # ── 推荐转速 ──
    p_spd = sub.add_parser("speed", help="估算合适转速")
    p_spd.add_argument("-Q", type=float, required=True, help="流量 (m³/h)")
    p_spd.add_argument("-P", type=float, required=True, help="全压 (Pa)")
    p_spd.add_argument("-n", type=float, required=True, help="转速 (r/min)")

    # ── 叶片型线生成 ──
    p_prof = sub.add_parser("profile", help="生成叶片型线坐标")
    p_prof.add_argument("--r1", type=float, required=True, help="进口半径 mm")
    p_prof.add_argument("--r2", type=float, required=True, help="出口半径 mm")
    p_prof.add_argument("--beta1", type=float, required=True, help="进口角 °")
    p_prof.add_argument("--beta2", type=float, required=True, help="出口角 °")
    p_prof.add_argument("--points", type=int, default=50, help="点数")
    p_prof.add_argument("--b1", type=float, help="进口宽度 mm (3D)")
    p_prof.add_argument("--b2", type=float, help="出口宽度 mm (3D)")
    p_prof.add_argument("--export", type=str, help="导出 CSV 路径")
    p_prof.add_argument("--sw-curve", type=str, help="导出 SW .sldcrv 路径")

    # ── 轴流风机设计 ──
    p_axial = sub.add_parser("axial", help="轴流风机设计")
    p_axial.add_argument("-Q", type=float, required=True, help="流量 (m³/h)")
    p_axial.add_argument("-P", type=float, required=True, help="全压 (Pa)")
    p_axial.add_argument("-n", type=float, default=0, help="转速 (r/min，0=自动选型)")
    p_axial.add_argument("--airfoil", default="clark_y",
                         choices=[t.value for t in AxialAirfoilType], help="翼型")
    p_axial.add_argument("--material", default="Q235B", help="材料")
    p_axial.add_argument("--sections", type=int, default=5, help="径向截面数")
    p_axial.add_argument("--circulation", default="equal",
                         choices=[t.value for t in CirculationType],
                         help="环量分布（equal=等环量, linear=线性, variable=变环量）")
    p_axial.add_argument("--nu", type=float, default=0, help="轮毂比 ν（0=自动）")
    p_axial.add_argument("--macro", action="store_true", help="生成 VBA 宏")
    p_axial.add_argument("--macro-dir", default="./outputs", help="宏输出目录")
    p_axial.add_argument("--export", type=str, help="导出叶片点云 CSV 路径")
    p_axial.add_argument("--curve", action="store_true", help="导出性能曲线 CSV + SVG")
    p_axial.add_argument("--curve-dir", default="./outputs", help="曲线输出目录")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 路由
    {
        "query": cmd_query,
        "extract": cmd_extract,
        "generate": cmd_generate,
        "macro": cmd_macro,
        "list": cmd_list,
        "batch": cmd_batch,
        "interactive": cmd_interactive,
        "select": cmd_select,
        "fan": cmd_fan_design,
        "ns": cmd_fan_ns,
        "speed": cmd_fan_speed,
        "profile": cmd_profile,
        "axial": cmd_axial_design,
    }[args.command](args)


if __name__ == "__main__":
    main()
