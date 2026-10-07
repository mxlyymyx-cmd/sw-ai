"""CLI 层测试：app/main.py 各子命令 handler 进程内直测（离线，无 COM）。

generate 命令只测 --dry-run（真实生成需 SolidWorks 真机）。
"""

import argparse
import sys

import pytest

import app.main as m


def ns(**kw) -> argparse.Namespace:
    return argparse.Namespace(**kw)


# ── 法兰：query / extract / generate / macro / list ──────

def test_query_prints_standards(capsys):
    m.cmd_query(ns(dn=100, pn=16, type="plate"))
    out = capsys.readouterr().out
    assert "GB/T 9119-2010" in out
    assert "DN100" in out


def test_query_weld_neck_standard(capsys):
    m.cmd_query(ns(dn=100, pn=16, type="weld_neck"))
    assert "GB/T 9115-2010" in capsys.readouterr().out


def test_query_unsupported_exits(capsys):
    with pytest.raises(SystemExit) as e:
        m.cmd_query(ns(dn=999, pn=16, type="plate"))
    assert e.value.code == 1
    assert "❌" in capsys.readouterr().out


def test_extract_regex_ok(capsys):
    m.cmd_extract(ns(text="DN100 PN16 带颈平焊法兰，8个螺栓孔"))
    out = capsys.readouterr().out
    assert "参数提取成功" in out
    assert "DN100" in out


def test_extract_garbage_fails_with_exit(capsys):
    with pytest.raises(SystemExit):
        m.cmd_extract(ns(text="今天天气真不错啊朋友们"))
    assert "提取失败" in capsys.readouterr().out


def test_generate_dry_run_prints_params_only(tmp_path, capsys):
    m.cmd_generate(ns(dn=100, pn=16, type="plate", dry_run=True,
                      output_dir=str(tmp_path)))
    out = capsys.readouterr().out
    assert "Dry-run" in out
    assert not list(tmp_path.iterdir())  # dry-run 不落任何文件


def test_macro_writes_bas_file(tmp_path, capsys):
    m.cmd_macro(ns(dn=100, pn=16, type="plate", output_dir=str(tmp_path)))
    out = capsys.readouterr().out
    assert "✅ VBA 宏已生成" in out
    f = tmp_path / "Flange_DN100_PN16_plate.bas"
    assert f.exists()
    assert "Sub " in f.read_text(encoding="utf-8")


def test_list_all_specs(capsys):
    m.cmd_list(ns(pn=None))
    out = capsys.readouterr().out
    assert "所有可用规格" in out
    assert "共 " in out


def test_list_filtered_by_pn(capsys):
    m.cmd_list(ns(pn=16))
    out = capsys.readouterr().out
    assert "PN16" in out
    assert "PN25" not in out


# ── 风机：select / fan / axial / ns / speed / profile ────

def test_select_recommends(capsys):
    m.cmd_select(ns(Q=20000, P=800, prefer="auto", curve=False, curve_dir=""))
    out = capsys.readouterr().out
    assert "推荐方案" in out or "推荐" in out


def test_select_prefer_centrifugal(capsys):
    m.cmd_select(ns(Q=5000, P=2500, prefer="centrifugal", curve=False, curve_dir=""))
    assert "离心" in capsys.readouterr().out


def test_select_with_curve_exports(tmp_path, capsys):
    m.cmd_select(ns(Q=20000, P=800, prefer="auto", curve=True, curve_dir=str(tmp_path)))
    files = {p.name for p in tmp_path.iterdir()}
    assert any(n.endswith("_curve.csv") for n in files)
    assert any(n.endswith("_curve.svg") for n in files)


def test_fan_design_fixed_speed(capsys):
    m.cmd_fan_design(ns(Q=5000, P=2500, n=1450, type="backward", material="Q235B",
                        macro=False, macro_dir="", profile=None, volute=False,
                        curve=False, curve_dir=""))
    assert len(capsys.readouterr().out) > 100  # 输出完整设计摘要


def test_fan_design_auto_speed(capsys):
    m.cmd_fan_design(ns(Q=5000, P=2500, n=0, type="backward", material="Q235B",
                        macro=False, macro_dir="", profile=None, volute=False,
                        curve=False, curve_dir=""))
    assert "自动选型" in capsys.readouterr().out


def test_fan_design_volute_and_macros(tmp_path, capsys):
    m.cmd_fan_design(ns(Q=5000, P=2500, n=1450, type="backward", material="Q235B",
                        macro=True, macro_dir=str(tmp_path), profile=None, volute=True,
                        curve=False, curve_dir=""))
    files = {p.name for p in tmp_path.iterdir()}
    assert any("impeller.bas" in n for n in files)
    assert any("volute.bas" in n for n in files)


def test_axial_design_fixed_speed(capsys):
    m.cmd_axial_design(ns(Q=20000, P=800, n=1450, airfoil="clark_y", material="Q235B",
                          sections=5, circulation="equal", nu=0,
                          macro=False, macro_dir="", export=None,
                          curve=False, curve_dir=""))
    assert len(capsys.readouterr().out) > 100


def test_axial_design_auto_speed(capsys):
    m.cmd_axial_design(ns(Q=30000, P=400, n=0, airfoil="clark_y", material="Q235B",
                          sections=5, circulation="equal", nu=0,
                          macro=False, macro_dir="", export=None,
                          curve=False, curve_dir=""))
    assert "自动选型" in capsys.readouterr().out


def test_axial_design_export_points(tmp_path, capsys):
    target = tmp_path / "blade.csv"
    m.cmd_axial_design(ns(Q=20000, P=800, n=1450, airfoil="clark_y", material="Q235B",
                          sections=5, circulation="equal", nu=0,
                          macro=False, macro_dir="", export=str(target),
                          curve=False, curve_dir=""))
    assert target.exists()


def test_fan_ns_prints_and_advises(capsys):
    m.cmd_fan_ns(ns(Q=5000, P=2500, n=1450))
    out = capsys.readouterr().out
    assert "n_s" in out
    assert "建议" in out


def test_fan_speed_prints_motor_options(capsys):
    m.cmd_fan_speed(ns(Q=5000, P=2500, n=1450))
    out = capsys.readouterr().out
    assert "1450" in out and "2900" in out


def test_profile_prints_points(capsys):
    m.cmd_profile(ns(r1=140, r2=280, beta1=35, beta2=60, points=50,
                     b1=None, b2=None, export=None, sw_curve=None))
    out = capsys.readouterr().out
    assert "50 个点" in out
    assert "包角" in out


def test_profile_export_csv(tmp_path, capsys):
    target = tmp_path / "profile.csv"
    m.cmd_profile(ns(r1=140, r2=280, beta1=35, beta2=60, points=30,
                     b1=50, b2=50, export=str(target), sw_curve=None))
    assert target.exists()
    assert target.read_text(encoding="utf-8").count(",") > 30  # 多行三维坐标


# ── main() 参数解析 + 子命令路由（端到端，进程内）─────────

def test_main_dispatch_query(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "query", "100", "16"])
    m.main()
    assert "GB/T 9119-2010" in capsys.readouterr().out


def test_main_dispatch_fan(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "fan", "-Q", "5000", "-P", "2500",
                                      "-n", "1450"])
    m.main()
    assert len(capsys.readouterr().out) > 100


def test_main_no_args_prints_help_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    with pytest.raises(SystemExit) as e:
        m.main()
    assert e.value.code == 1
    out = capsys.readouterr().out
    assert "用法" in out or "usage" in out.lower()


def test_main_survives_gbk_console(monkeypatch):
    """回归：打包 exe 在 GBK 控制台输出 emoji 曾 UnicodeEncodeError 崩溃。

    main() 应把控制台流降级为 errors=replace——emoji 变 ?，中文不受影响。
    """
    import io

    buf = io.BytesIO()
    monkeypatch.setattr(sys, "argv", ["main.py", "query", "100", "16"])
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(buf, encoding="gbk"))
    m.main()
    sys.stdout.flush()  # TextIOWrapper 有内部缓冲，不 flush 读不到
    out = buf.getvalue().decode("gbk")
    assert "DN100" in out
    assert "?" in out  # 📐 被降级为占位符而非崩溃
