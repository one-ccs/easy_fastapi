"""gen/db/run 共用的项目守卫（统一报错）。

薄壳 helper：轻探测用 Path.exists，真实解析调 easy_fastapi.project.read_marker()。
read_marker 已下沉到 Core（CLI 与 Core 共用）。
"""

from pathlib import Path

from easy_fastapi.project import read_marker


def require_project() -> dict:
    """读当前目录 marker，缺失/损坏统一抛 ConfigError。"""
    return read_marker(Path.cwd())
