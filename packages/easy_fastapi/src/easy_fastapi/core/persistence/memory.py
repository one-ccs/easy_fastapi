"""内存持久化（core 预注册的 persistence 默认值）。

redis 未启用时 auth 用它。支持简易 TTL 过期（ex 秒）：
set 时记录到期时间戳，get 时检查并惰性删除过期键。
非单例（消除旧 persistence.py 的 __new__ 单例 hack）。
"""

from __future__ import annotations

import time
from typing import Any


class MemoryPersistence:
    MAX_ENTRIES = 10_000  # 容量上限，防止未读键无限累积

    def __init__(self) -> None:
        # value + expire_at（None 表示永不过期）
        self._data: dict[str, tuple[Any, float | None]] = {}

    def _evict_expired(self) -> None:
        """主动清理所有过期键。"""
        now = time.monotonic()
        expired = [k for k, (_, ea) in self._data.items() if ea is not None and now >= ea]
        for k in expired:
            del self._data[k]

    async def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if expire_at is not None and time.monotonic() >= expire_at:
            # 惰性删除过期键
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ex: int | None = None) -> None:
        if len(self._data) >= self.MAX_ENTRIES:
            self._evict_expired()
        expire_at = time.monotonic() + ex if ex and ex > 0 else None
        self._data[key] = (value, expire_at)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
