"""Redis 持久化（实现 Persistence 协议，enabled=false 回退）。

enabled=false 时所有操作静默回退：get→None、set→no-op、delete→False。
enabled=true 且未注入 client 时，自动用 redis.asyncio.from_url 构建连接。
"""

from __future__ import annotations

from typing import Any

from easy_fastapi.core.extras import require


class RedisPersistence:
    def __init__(
        self,
        *,
        enabled: bool = True,
        url: str = "redis://localhost:6379/0",
        client: Any = None,
    ) -> None:
        self._enabled = enabled
        self._client = client
        if enabled and client is None:
            redis = require("redis", "redis")
            self._client = redis.asyncio.from_url(url)

    async def get(self, key: str) -> Any:
        if not self._enabled:
            return None
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        if not self._enabled:
            return
        if ex is not None and ex > 0:
            await self._client.set(key, value, ex=ex)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> bool:
        if not self._enabled:
            return False
        return bool(await self._client.delete(key))

    async def close(self) -> None:
        """关闭底层 Redis 连接池（应用 shutdown 时调用）。"""
        if self._enabled and self._client is not None:
            await self._client.aclose()
