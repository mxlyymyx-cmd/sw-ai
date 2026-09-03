"""
国标法兰数据库测试 — 4 类型 × PN10/16/25/40 × DN10~300 全表不变量校验

数据源:
  plate     GB/T 9119-2010（板式平焊）
  slip_on   GB/T 9116-2010 / HG/T 20592-2009（带颈平焊）
  weld_neck GB/T 9115-2010 / HG/T 20592-2009（对焊）
  blind     GB/T 9123-2010（法兰盖）
"""

import pytest

from flange.gb_standards import (
    SUPPORTED_PN,
    is_supported,
    list_available,
    lookup,
)
from flange.params import FlangeParams, FlangeType

ALL_TYPES = ["plate", "slip_on", "weld_neck", "blind"]
ALL_DNS = [10, 15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300]

# ═══════════════════════════════════════════════════════════════
# 全表几何不变量（240 组）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.parametrize("ftype", ALL_TYPES)
@pytest.mark.parametrize("pn", SUPPORTED_PN)
@pytest.mark.parametrize("dn", ALL_DNS)
def test_lookup_geometric_invariants(dn, pn, ftype):
    p = lookup(dn, pn, ftype)

    assert isinstance(p, FlangeParams)
    assert p.dn == dn and p.pn == pn
    assert p.flange_type == FlangeType(ftype)

    # 厚度/孔基本量
    assert p.c > 0
    assert p.f > 0
    assert p.n >= 4
    assert p.l > 0

    # 径向链: 内孔 < 密封面 < 螺栓孔分布 < 法兰外圆
    assert p.d > p.k > p.d1 > 0
    # 螺栓孔完全位于法兰盘内
    assert p.k + p.l <= p.d
    # 螺栓孔不侵入密封面（孔内缘直径 > 密封面外径）
    assert p.k - p.l > p.d1

    # 内径
    if ftype == "blind":
        assert p.inner_d == 0
    else:
        assert 0 < p.inner_d < p.d1

    # 颈部
    if ftype in ("plate", "blind"):
        assert p.neck_d == 0 and p.neck_h == 0 and p.neck_tip_d == 0
    else:
        assert p.neck_d > 0
        assert p.neck_h > 0
        assert p.neck_d < p.d1
    if ftype == "weld_neck":
        # 对焊: 内径 < 小端 A1 ≤ 根径 N < 密封面
        assert p.inner_d < p.neck_tip_d <= p.neck_d
        assert p.neck_thk > 0
        assert p.neck_straight_h > 0
    if ftype == "slip_on":
        # 带颈平焊: 直颈，小端 = 根径
        assert p.neck_tip_d == p.neck_d


# ═══════════════════════════════════════════════════════════════
# 关键规格 spot check（HG/T 20592-2009 / GB/T 9119-2010）
# ═══════════════════════════════════════════════════════════════


def test_plate_dn100_pn16_spot():
    p = lookup(100, 16, "plate")
    assert (p.d, p.k, p.l, p.n, p.c) == (220, 180, 18, 8, 20)
    assert p.f == 3
    assert p.d1 == 156
    assert p.inner_d == 108
    assert p.standard == "GB/T 9119-2010"


def test_slip_on_dn100_pn16_spot():
    p = lookup(100, 16, "slip_on")
    assert (p.d, p.k, p.l, p.n, p.c) == (220, 180, 18, 8, 20)
    assert p.d1 == 158
    assert p.inner_d == 110        # B 法兰内径
    assert p.neck_d == 140         # N
    assert p.neck_h == 18          # H=40 - C=20 - f=2
    assert p.neck_tip_d == 140     # 直颈: 小端 = N
    assert p.standard == "GB/T 9116-2010"


def test_weld_neck_dn100_pn16_spot():
    p = lookup(100, 16, "weld_neck")
    assert p.neck_d == 131         # N
    assert p.neck_tip_d == 108     # A1 钢管外径
    assert p.inner_d == pytest.approx(108 - 2 * 3.6)   # A1 - 2S
    assert p.neck_thk == 3.6       # S
    assert p.neck_straight_h == 12  # H1
    assert p.neck_h == 30          # H=52 - C=20 - f=2
    assert p.standard == "GB/T 9115-2010"


def test_blind_dn100_pn16_spot():
    p = lookup(100, 16, "blind")
    assert (p.d, p.k, p.l, p.n, p.c) == (220, 180, 18, 8, 20)
    assert p.inner_d == 0
    assert p.neck_d == 0 and p.neck_h == 0
    assert p.standard == "GB/T 9123-2010"


def test_lookup_accepts_enum_and_str():
    assert lookup(100, 16, FlangeType.WELD_NECK) == lookup(100, 16, "weld_neck")


# ═══════════════════════════════════════════════════════════════
# 错误路径
# ═══════════════════════════════════════════════════════════════


def test_lookup_unsupported_dn():
    with pytest.raises(ValueError, match="DN"):
        lookup(500, 16, "plate")


def test_lookup_unsupported_pn():
    with pytest.raises(ValueError, match="PN"):
        lookup(100, 63, "plate")


def test_lookup_unsupported_type():
    with pytest.raises(ValueError, match="暂不支持"):
        lookup(100, 16, "threaded")


@pytest.mark.parametrize("dn,pn,expected", [
    (100, 16, True),
    (300, 40, True),
    (500, 16, False),
    (100, 63, False),
])
def test_is_supported(dn, pn, expected):
    assert is_supported(dn, pn) is expected


def test_list_available_covers_all_pn():
    avail = list_available()
    assert len(avail) == len(SUPPORTED_PN) * len(ALL_DNS)
    pns = {item["pn"] for item in avail}
    assert set(SUPPORTED_PN) == pns
    filtered = list_available(pn=16)
    assert len(filtered) == len(ALL_DNS)
    assert all(item["pn"] == 16 for item in filtered)
