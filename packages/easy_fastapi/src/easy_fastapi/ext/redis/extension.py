"""Redis 运行时扩展（override persistence）。

enabled=true 时用 ctx.provide('persistence', RedisPersistence(...), override=True)
覆盖 core 预注册的 MemoryPersistence；enabled=false 时不 override，保留 Memory。

init_app 组合已注册的 lifespan（如 ORM 扩展的 engine.dispose），
追加 Redis 连接池关闭逻辑，避免应用 shutdown 时连接泄漏。
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, ClassVar

from .config import RedisConfig
from .persistence import RedisPersistence

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext


class RedisExtension:
    name = "redis"
    requires: ClassVar[list[str]] = []

    def config_model(self):
        return RedisConfig

    def init_app(self, app: FastAPI, config: RedisConfig | None, ctx: ExtensionContext) -> None:
        cfg = config or RedisConfig()
        if not cfg.enabled:
            return  # 不 override，保留 core 的 MemoryPersistence
        persistence = RedisPersistence(enabled=True, url=cfg.url)
        ctx.provide("persistence", persistence, override=True)

        # 组合已有 lifespan（如 ORM 扩展绑定的 engine.dispose），追加 Redis 连接池关闭。
        # 不能直接赋值 app.router.lifespan_context，否则会覆盖 ORM 扩展的 lifespan。
        prev_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            async with AsyncExitStack() as stack:
                # 进入前一个 lifespan（ORM 的 create_all/engine.dispose 等）
                await stack.enter_async_context(prev_lifespan(_app))
                try:
                    yield
                finally:
                    await persistence.close()

        app.router.lifespan_context = lifespan
