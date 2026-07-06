"""目录模式推导与落盘路径（双模式契约）。

frontend=True → fullstack monorepo（后端进 backend/，前端进 frontend/）；
否则 backend-only（app/ 在顶层）。
"""

from .options import CreateOptions


def project_layout(options: CreateOptions) -> str:
    """frontend=True → fullstack；否则 backend-only。"""
    return "fullstack" if options.frontend else "backend-only"
