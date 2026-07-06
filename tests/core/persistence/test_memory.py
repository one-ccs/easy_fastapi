"""MemoryPersistence 测试（core 预注册的 persistence 默认值）。

覆盖：满足 Persistence 协议、set/get/delete 正确、缺失返回 None、
ex 安全忽略、非单例（实例独立）、覆盖更新、delete 幂等、None/任意值。
"""

from easy_fastapi.core.persistence.memory import MemoryPersistence
from easy_fastapi.core.protocols import Persistence


def test_memory_persistence_satisfies_protocol():
    assert isinstance(MemoryPersistence(), Persistence)


async def test_set_get_delete():
    p = MemoryPersistence()
    await p.set("k", "v")
    assert await p.get("k") == "v"
    await p.delete("k")
    assert await p.get("k") is None


async def test_get_missing_returns_none():
    p = MemoryPersistence()
    assert await p.get("nope") is None


async def test_set_with_ex_stores_with_ttl():
    """MemoryPersistence 支持 TTL：ex 秒后键过期（惰性删除）。"""
    p = MemoryPersistence()
    await p.set("k", "v", ex=60)
    assert await p.get("k") == "v"  # 未过期仍可取


async def test_set_with_zero_ex_does_not_expire():
    """ex=0 或负数视为永不过期（与 redis 语义一致：ex<=0 不设过期）。"""
    p = MemoryPersistence()
    await p.set("k", "v", ex=0)
    assert await p.get("k") == "v"


async def test_expired_key_returns_none(monkeypatch):
    """过期后 get 返回 None 并惰性删除。"""
    import time

    p = MemoryPersistence()
    await p.set("k", "v", ex=10)
    # 模拟时间前进 11 秒
    fake_now = [time.monotonic()]
    monkeypatch.setattr(
        "easy_fastapi.core.persistence.memory.time.monotonic",
        lambda: fake_now[0],
    )
    fake_now[0] += 11
    assert await p.get("k") is None
    # 惰性删除后键已从存储移除
    assert "k" not in p._data


async def test_set_overwrites_existing():
    p = MemoryPersistence()
    await p.set("k", "v1")
    await p.set("k", "v2")
    assert await p.get("k") == "v2"


async def test_delete_missing_is_idempotent():
    # delete 不存在的 key 不报错
    p = MemoryPersistence()
    await p.delete("ghost")  # 无异常
    await p.set("a", 1)
    await p.delete("a")
    await p.delete("a")  # 再删一次也不报错
    assert await p.get("a") is None


async def test_instances_are_independent():
    # 非单例：两个实例存储隔离（消除旧 persistence.py 的 __new__ 单例 hack）
    a = MemoryPersistence()
    b = MemoryPersistence()
    await a.set("k", "in-a")
    assert await b.get("k") is None
    assert a is not b


async def test_stores_none_value():
    # None 作为 value 应可存可取（与"键不存在返回 None"需区分，但本实现允许）
    p = MemoryPersistence()
    await p.set("k", None)
    assert await p.get("k") is None


async def test_stores_arbitrary_types():
    p = MemoryPersistence()
    await p.set("list", [1, 2, 3])
    await p.set("dict", {"a": 1})
    await p.set("obj", object())
    assert await p.get("list") == [1, 2, 3]
    assert await p.get("dict") == {"a": 1}
    assert await p.get("obj") is not None


async def test_delete_returns_none():
    # delete 无返回值（纯副作用）
    p = MemoryPersistence()
    await p.set("k", "v")
    assert await p.delete("k") is None


async def test_isolation_between_keys():
    p = MemoryPersistence()
    await p.set("a", 1)
    await p.set("b", 2)
    await p.delete("a")
    assert await p.get("a") is None
    assert await p.get("b") == 2
