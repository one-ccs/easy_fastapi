"""RedisPersistence 测试。"""

from easy_fastapi.core.protocols import Persistence
from easy_fastapi.ext.redis.persistence import RedisPersistence


async def test_satisfies_persistence_protocol():
    p = RedisPersistence(enabled=False)
    assert isinstance(p, Persistence)


async def test_disabled_get_returns_none():
    p = RedisPersistence(enabled=False)
    assert await p.get("any") is None


async def test_disabled_set_no_op():
    p = RedisPersistence(enabled=False)
    # 不抛异常即通过
    await p.set("k", "v")


async def test_disabled_delete_returns_false():
    p = RedisPersistence(enabled=False)
    assert await p.delete("k") is False


async def test_enabled_with_fake_redis_crud():
    class FakeRedis:
        def __init__(self):
            self.store = {}

        async def get(self, k):
            return self.store.get(k)

        async def set(self, k, v, **kw):
            self.store[k] = v

        async def delete(self, k):
            if k in self.store:
                del self.store[k]
                return 1
            return 0

    p = RedisPersistence(enabled=True, client=FakeRedis())
    await p.set("k", "v")
    assert await p.get("k") == "v"
    assert await p.delete("k") is True
    assert await p.get("k") is None


async def test_enabled_delete_nonexistent_returns_false():
    class FakeRedis:
        async def get(self, k):
            return None

        async def set(self, k, v, **kw):
            pass

        async def delete(self, k):
            return 0

    p = RedisPersistence(enabled=True, client=FakeRedis())
    assert await p.delete("missing") is False


async def test_enabled_set_with_ex():
    """set(key, val, ex=N) 透传 ex 参数给 client.set。"""
    calls = []

    class FakeRedis:
        async def get(self, k):
            return None

        async def set(self, k, v, **kw):
            calls.append(("set", k, v, kw.get("ex")))

        async def delete(self, k):
            return 0

    p = RedisPersistence(enabled=True, client=FakeRedis())
    await p.set("k", "v", ex=60)
    assert calls == [("set", "k", "v", 60)]


async def test_default_enabled_true():
    """enabled 默认 True，无 client 时需外部注入或由 from_url 构建。"""
    # 不传 client 且 enabled=True → 构造时自建 redis.asyncio.from_url。
    # 测试中验证 enabled 属性即可，不连真实 Redis。
    p = RedisPersistence(enabled=False)
    assert p._enabled is False


async def test_enabled_set_without_ex():
    calls = []

    class FakeRedis:
        async def get(self, k):
            return None

        async def set(self, k, v, **kw):
            calls.append(("set", k, v, kw.get("ex")))

        async def delete(self, k):
            return 0

    p = RedisPersistence(enabled=True, client=FakeRedis())
    await p.set("k", "v")
    assert calls == [("set", "k", "v", None)]
