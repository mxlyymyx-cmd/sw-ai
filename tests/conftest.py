"""pytest 配置 — 将仓库根目录加入 sys.path（swai/ 与 app/ 包在仓库根下）"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
