# legacy 工具归档

`push_api.py` / `push_commits.py`：本机 git push 打不通期间，用 GitHub Git Data API
硬推提交的临时工具（2026-08 收编）。https push 恢复后仅作故障兜底保留，用法见文件头注释。

`macro_probe.vbs` / `macro_probe.ps1`：SolidWorks 宏执行通道（.swp 假宏 → VBA →
cscript/VBS）调试期的探针代表样本。全套 22 个探针已删除，需要时从 git 历史
（v1.0.2-final 的 `tools/probe/`）找回。
