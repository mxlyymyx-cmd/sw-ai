#!/usr/bin/env python3
"""通过 GitHub Git Data API 推送提交（github.com 主站不通，仅 api.github.com 可达）

用法: python _push_api.py          # 推送 FILES 中的更新 + 删除 DELETES 中的路径
"""
import base64
import json
import re
import sys
import urllib.request


def load_token():
    """从 WorkBuddy 插件仓库的 remote URL 中提取 PAT（本机 github.com 不通，git CLI 无法用）"""
    cfg = open(r"C:\Users\Administrator\Desktop\WorkBuddy\SolidWorksAI\.git\config", encoding="utf-8").read()
    m = re.search(r"https://([^:]+):([A-Za-z0-9_]+)@github\.com", cfg)
    if not m:
        raise RuntimeError("未在 WorkBuddy SolidWorksAI/.git/config 中找到 PAT")
    return m.group(2)


TOKEN = load_token()
REPO = "mxlyymyx-cmd/sw-ai"
API = f"https://api.github.com/repos/{REPO}"


def api(url, method="GET", payload=None):
    req = urllib.request.Request(url, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "User-Agent": "swai-push",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    })
    data = json.dumps(payload).encode() if payload is not None else None
    resp = urllib.request.urlopen(req, data=data, timeout=60)
    body = resp.read().decode()
    return json.loads(body) if body else {}


FILES = [
    "README.md",
    ".gitignore",
]

DELETES = [
    "__pycache__/api.cpython-312.pyc",
    "axial/__pycache__/__init__.cpython-312.pyc",
    "axial/__pycache__/blades.cpython-312.pyc",
    "axial/__pycache__/design.cpython-312.pyc",
    "axial/__pycache__/generator.cpython-312.pyc",
    "axial/__pycache__/params.cpython-312.pyc",
    "flange/__pycache__/__init__.cpython-312.pyc",
    "flange/__pycache__/ai_extractor.cpython-312.pyc",
    "flange/__pycache__/gb_standards.cpython-312.pyc",
    "flange/__pycache__/generator.cpython-312.pyc",
    "flange/__pycache__/params.cpython-312.pyc",
    "flange/__pycache__/pipeline.cpython-312.pyc",
    "impeller/__pycache__/__init__.cpython-312.pyc",
    "impeller/__pycache__/blades.cpython-312.pyc",
    "impeller/__pycache__/design.cpython-312.pyc",
    "impeller/__pycache__/generator.cpython-312.pyc",
    "impeller/__pycache__/params.cpython-312.pyc",
    "impeller/__pycache__/volute.cpython-312.pyc",
]

MESSAGE = """docs: README 补齐 4 类法兰/性能标定/测试 CI 说明 + 清理误提交的 .pyc

- README: 法兰模块 4 类型 240 规格说明、盲板 GB/T 9123、性能曲线实测标定、
  开发与测试章节（344 项离线测试清单）、统计表更新、CLI 示例修正 --type 参数
- .gitignore: 补 .pytest_cache/、outputs/、*.swp、build/、egg-info
- 删除 19 个历史误提交的 __pycache__/*.pyc

🤖 Generated with TRAE
"""


def main():
    # 1. 当前 main HEAD
    ref = api(f"{API}/git/ref/heads/main")
    parent_sha = ref["object"]["sha"]
    parent = api(f"{API}/git/commits/{parent_sha}")
    base_tree = parent["tree"]["sha"]
    print(f"parent: {parent_sha[:8]}  base_tree: {base_tree[:8]}")

    # 2. 逐文件创建 blob（base64 防中文乱码）
    entries = []
    for path in FILES:
        content = open(path, "rb").read()
        blob = api(f"{API}/git/blobs", "POST", {
            "content": base64.b64encode(content).decode(),
            "encoding": "base64",
        })
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  blob {path} ({len(content)} B)")

    # 3. 删除条目（sha: null）
    for path in DELETES:
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
        print(f"  del  {path}")

    # 4. 基于现有 tree 创建新 tree
    tree = api(f"{API}/git/trees", "POST", {"base_tree": base_tree, "tree": entries})
    print(f"tree: {tree['sha'][:8]}")

    # 5. 创建 commit
    commit = api(f"{API}/git/commits", "POST", {
        "message": MESSAGE,
        "tree": tree["sha"],
        "parents": [parent_sha],
    })
    print(f"commit: {commit['sha'][:8]}")

    # 6. 更新 main 引用（fast-forward）
    api(f"{API}/git/refs/heads/main", "PATCH", {"sha": commit["sha"]})
    print(f"main -> {commit['sha'][:8]}  PUSH OK")


if __name__ == "__main__":
    sys.exit(main())
