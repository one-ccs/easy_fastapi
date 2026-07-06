"""context 挂载访问。

提供从任意 app 对象取回 ExtensionContext 的统一入口：经 app.state.easy_fastapi.context。
未挂载（或对象无 state/无 easy_fastapi 属性）时翻译为 ExtensionError，避免裸 AttributeError 泄露。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import ExtensionError

if TYPE_CHECKING:
    from fastapi import FastAPI

    from .extension import ExtensionContext


def get_extension_context(app: FastAPI) -> ExtensionContext:
    """从已装配的 app 取回 ExtensionContext。

    要求该 app 经 EasyFastAPI(app, ...) 装配。
    未挂载或对象非 FastAPI 实例 → ExtensionError（EasyFastAPIError 子类），不泄露 AttributeError。
    """
    state = getattr(app, "state", None)
    easy = getattr(state, "easy_fastapi", None) if state is not None else None
    if easy is None:
        raise ExtensionError("当前 app 并非 EasyFastAPI 装配实例，无法获取 ExtensionContext。")
    return easy.context
