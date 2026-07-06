"""Tortoise 会话管理 + db_session_factory service。

tortoise 经 require() 守卫。init_tortoise 自动追加 aerich.models（迁移表）。
generate_schemas 基于 Tortoise 已初始化状态建表（无参）。
make_session_factory 返回 DbSessionFactory：__call__ → async cm → DbSession。
"""

from __future__ import annotations

import importlib
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from easy_fastapi.core.extras import require

tortoise = require("tortoise-orm", "tortoise")


async def init_tortoise(
    *, db_url: str, models: list[str], timezone: str = "Asia/Chongqing", echo: bool = False
) -> None:
    """初始化 Tortoise，自动追加 aerich.models（供迁移使用，aerich 未安装时跳过）。

    Tortoise 1.1+ 使用 contextvars 管理连接，启用 _enable_global_fallback 以支持 ASGI 请求。
    """
    _ = echo  # tortoise 经 config 控制，预留
    all_models = list(models)
    try:
        importlib.import_module("aerich.models")
        all_models = ["aerich.models", *all_models]
    except ModuleNotFoundError:
        pass  # aerich 未安装，跳过迁移表
    config = {
        "connections": {"default": db_url},
        "apps": {"models": {"models": all_models, "default_connection": "default"}},
        "use_tz": False,
        "timezone": timezone,
    }
    # Tortoise 1.1+ 支持 _enable_global_fallback（ASGI contextvars 兼容）
    import inspect

    init_sig = inspect.signature(tortoise.Tortoise.init)
    if "_enable_global_fallback" in init_sig.parameters:
        await tortoise.Tortoise.init(config=config, _enable_global_fallback=True)
    else:
        await tortoise.Tortoise.init(config=config)


async def generate_schemas() -> None:
    """基于已 init 的 Tortoise 状态建表（须先 init_tortoise）。"""
    await tortoise.Tortoise.generate_schemas()


class _TortoiseSession:
    """tortoise 无显式 per-request session（连接在 Tortoise 级别管理）。
    此 Session 提供协议要求的 commit/rollback/close 占位，语义为无操作。"""

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass


@asynccontextmanager
async def _session_cm() -> Any:
    try:
        yield _TortoiseSession()
    finally:
        pass


def make_session_factory(*, db_url: str, models: list[str]):
    """返回 DbSessionFactory（__call__ -> AsyncContextManager[DbSession]）。

    db_url/models 仅记录语义（tortoise 连接由 Tortoise 级别管理，factory 不重新 init）。
    """

    def factory() -> AbstractAsyncContextManager:
        return _session_cm()

    return factory
