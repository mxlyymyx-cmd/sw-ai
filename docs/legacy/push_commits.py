#!/usr/bin/env python3
"""通过 GitHub Git Data API 提交并推送（本机 github.com 不通，仅 api.github.com 可达）

用法:
  set SWAI_TOKEN=ghp_xxx
  py -3 tools/push_commits.py            # 按下方 COMMITS 配置逐个推送

特性:
  - 中文/二进制文件 base64 上传
  - 多个 commit 依序推送，每次基于上一次结果
"""
import base64
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "mxlyymyx-cmd/sw-ai"
API = f"https://api.github.com/repos/{REPO}"
TOKEN = os.environ.get("SWAI_TOKEN", "")

COMMITS = [
    {
        "message": """feat: volute 蜗壳 SW2022 实测配方重写 + 插件稳定性修复

- impeller/volute.py: VBS 通道 CreateSpline 返回 Nothing，改用 CreateLine2 折线逼近螺旋线；
  螺旋起点外移 gap=max(2, 0.6%*R2) 避免与内腔圆相切导致 FeatureCut3 失败；
  FeatureExtrusion3 采用 23 参数 MidPlane 版本（SW2022 实机验证配方）
- plugin/ApiClient.cs: 新增 ApiResult.GetValue() 简化调用
- plugin/SWAIAddin.cs: 加载诊断日志 + SetAddinCallbackInfo2 握手 + 任务窗格图标
- plugin/TaskPaneControl.cs: PreviewKeyDown/KeyPress 兜底，修复任务窗格 Enter 键不触发发送

🤖 Generated with TRAE""",
        "files": [
            "impeller/volute.py",
            "plugin/ApiClient.cs",
            "plugin/SWAIAddin.cs",
            "plugin/TaskPaneControl.Designer.cs",
            "plugin/TaskPaneControl.cs",
        ],
    },
    {
        "message": """fix: API 能力诚实化 + 仓库卫生整理 + 本地构建支持

- api.py: /api/models 摘除无数据支持的 threaded 法兰与 ff/rj 密封面选项；
  DN 范围修正为实际的 DN10~DN300
- flange/ai_extractor.py: LLM 提示词与正则映射同步移除 threaded/ff/rj
- ai_chat.py: 聊天系统提示词同步移除 ff 宣传
- 收编 SolidWorks Interop DLL 到 plugin/libs/（克隆即可编译）
- 收编 build_swai.ps1/.rsp（Roslyn 本地编译部署脚本）
- 归档 21 个 SW 调试探针到 tools/probe/，_push_api.py 转正为 tools/push_api.py
- 收编 启动/停止AI服务.bat 服务管理脚本

🤖 Generated with TRAE""",
        "files": [
            "api.py",
            "ai_chat.py",
            "flange/ai_extractor.py",
            "tools/push_api.py",
            "tools/vba_to_vbs.py",
            "tools/_dbg_marks.py",
            "plugin/build_swai.ps1",
            "plugin/build_swai.rsp",
            "plugin/libs/SolidWorks.Interop.sldworks.dll",
            "plugin/libs/SolidWorks.Interop.swconst.dll",
            "plugin/libs/SolidWorks.Interop.swpublished.dll",
            "启动AI服务.bat",
            "停止AI服务.bat",
        ]
        + [f"tools/probe/{n}" for n in [
            "_macro_probe.ps1", "_macro_probe.vbs", "_probe10.vbs", "_probe2.vbs",
            "_probe3.vbs", "_probe4.vbs", "_probe5.vbs", "_probe6.vbs", "_probe7.vbs",
            "_probe8.vbs", "_probe9.vbs", "_probeV1.vbs", "_probeV2.vbs", "_probe_box.vbs",
            "_probe_diag.vbs", "_probe_dir.vbs", "_probe_mass.vbs", "_probe_ours.vbs",
            "_probe_pat.vbs", "_revolve_probe.vbs", "_test_axial_loop.py",
        ]],
    },
]


def api(url, method="GET", payload=None):
    req = urllib.request.Request(url, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "User-Agent": "swai-push",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
    })
    data = json.dumps(payload).encode() if payload is not None else None
    resp = urllib.request.urlopen(req, data=data, timeout=300)
    body = resp.read().decode()
    return json.loads(body) if body else {}


def push_commit(spec, parent_sha):
    parent = api(f"{API}/git/commits/{parent_sha}")
    base_tree = parent["tree"]["sha"]
    print(f"  parent: {parent_sha[:8]}  base_tree: {base_tree[:8]}")

    entries = []
    for path in spec["files"]:
        with open(os.path.join(ROOT, path), "rb") as fh:
            content = fh.read()
        blob = api(f"{API}/git/blobs", "POST", {
            "content": base64.b64encode(content).decode(),
            "encoding": "base64",
        })
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  blob {path} ({len(content)} B)")

    tree = api(f"{API}/git/trees", "POST", {"base_tree": base_tree, "tree": entries})
    commit = api(f"{API}/git/commits", "POST", {
        "message": spec["message"],
        "tree": tree["sha"],
        "parents": [parent_sha],
    })
    print(f"  commit: {commit['sha'][:8]}")

    api(f"{API}/git/refs/heads/main", "PATCH", {"sha": commit["sha"]})
    print(f"  main -> {commit['sha'][:8]}  PUSH OK")
    return commit["sha"]


def main():
    if not TOKEN:
        sys.exit("SWAI_TOKEN 环境变量未设置")
    ref = api(f"{API}/git/ref/heads/main")
    sha = ref["object"]["sha"]
    for i, spec in enumerate(COMMITS, 1):
        print(f"[{i}/{len(COMMITS)}] {spec['message'].splitlines()[0]}")
        sha = push_commit(spec, sha)
    print("ALL DONE")


if __name__ == "__main__":
    sys.exit(main())
