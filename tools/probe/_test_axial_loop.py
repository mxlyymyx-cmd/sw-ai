"""轴流风机闭环验证测试：三种环量分布 + 过载修正"""
from axial.params import AxialFanInput, AirfoilType, CirculationType
from axial.design import design_axial_fan

cases = [
    ("等环量", CirculationType.EQUAL),
    ("线性", CirculationType.LINEAR),
    ("变环量", CirculationType.VARIABLE),
]

print("── 闭环归一化测试（Q=20000, P=800, n=1450）──")
for name, circ in cases:
    inp = AxialFanInput(Q=20000, P=800, n=1450, circulation=circ)
    r = design_axial_fan(inp)
    print(f"{name}: P_th={r.P_th:.0f}Pa  偏差={r.P_dev:+.1%}  ν={r.nu:.3f}  "
          f"Df_max={r.Df_max:.2f}  cl_max={r.cl_req_max:.2f}  "
          f"DeHaller={r.dehaller_min:.2f}")

print()
print("── 极端工况测试 ──")
extremes = [
    AxialFanInput(Q=50000, P=300, n=960),
    AxialFanInput(Q=20000, P=800, n=1450),
    AxialFanInput(Q=5000, P=2000, n=2900),
    AxialFanInput(Q=100000, P=1500, n=980),
]
for inp in extremes:
    r = design_axial_fan(inp)
    print(f"Q={inp.Q:>6} P={inp.P:>4}Pa n={inp.n:>4}: D={r.D:.0f}mm ν={r.nu:.2f} "
          f"Z={r.Z} 偏差={r.P_dev:+.1%} Df={r.Df_max:.2f} cl={r.cl_req_max:.2f} "
          f"DeHaller={r.dehaller_min:.2f} 警告{len(r.warnings)}条")

print()
print("── 用户指定轮毂比（不自动修正）──")
inp = AxialFanInput(Q=20000, P=800, n=1450, nu=0.4)
r = design_axial_fan(inp)
print(f"ν={r.nu} Df_max={r.Df_max:.2f} cl_max={r.cl_req_max:.2f} "
      f"DeHaller={r.dehaller_min:.2f}（应保持原始过载状态）")
