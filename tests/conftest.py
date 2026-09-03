"""pytest 配置 — 将仓库根目录加入 sys.path（模块平铺在根目录）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
