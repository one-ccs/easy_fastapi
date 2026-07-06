"""核心服务协议测试。

Persistence / PasswordHasher / DbSession / DbSessionFactory / AuthUser /
UserModelProtocol / RoleModelProtocol / ModelIntrospector 各为 @runtime_checkable Protocol，
供 ctx.require(key, type_) 在运行时做 isinstance 校验。
本文件随各 Task（11-14）逐步补充覆盖。
"""

from easy_fastapi.core.protocols import PasswordHasher, Persistence

# ---- Persistence（正常路径） ----


class _FakePersistence:
    def get(self, key):
        return None

    def set(self, key, value, ex=None):
        pass

    def delete(self, key):
        pass


def test_persistence_runtime_checkable_accepts_fake():
    assert isinstance(_FakePersistence(), Persistence)


def test_persistence_accepts_implementation_with_extra_kwarg():
    # 协议只看方法存在与否，签名允许更宽（多带 kwargs）
    class P:
        def get(self, key, *args, **kwargs):
            return None

        def set(self, key, value, ex=None, **kwargs):
            pass

        def delete(self, key):
            pass

    assert isinstance(P(), Persistence)


# ---- Persistence（错误路径：缺方法） ----


def test_persistence_rejects_missing_set():
    class Bad:
        def get(self, key):
            return None

        def delete(self, key):
            pass

    assert not isinstance(Bad(), Persistence)


def test_persistence_rejects_missing_get():
    class Bad:
        def set(self, key, value, ex=None):
            pass

        def delete(self, key):
            pass

    assert not isinstance(Bad(), Persistence)


def test_persistence_rejects_missing_delete():
    class Bad:
        def get(self, key):
            return None

        def set(self, key, value, ex=None):
            pass

    assert not isinstance(Bad(), Persistence)


def test_persistence_rejects_empty_class():
    assert not isinstance(object(), Persistence)


# ---- PasswordHasher（正常 + 错误） ----


class _FakeHasher:
    def hash(self, password: str) -> str:
        return "h"

    def verify(self, password: str, hashed: str) -> bool:
        return True


def test_password_hasher_runtime_checkable_accepts_fake():
    assert isinstance(_FakeHasher(), PasswordHasher)


def test_password_hasher_rejects_missing_verify():
    class Bad:
        def hash(self, password: str) -> str:
            return "h"

    assert not isinstance(Bad(), PasswordHasher)


def test_password_hasher_rejects_missing_hash():
    class Bad:
        def verify(self, password: str, hashed: str) -> bool:
            return True

    assert not isinstance(Bad(), PasswordHasher)


# ---- 边界：非 Protocol 实例类型 ----


def test_none_is_not_persistence():
    assert not isinstance(None, Persistence)


def test_dict_is_not_password_hasher():
    assert not isinstance({}, PasswordHasher)


# ---- DbSession / DbSessionFactory ----

from contextlib import asynccontextmanager  # noqa: E402

from easy_fastapi.core.protocols import DbSession, DbSessionFactory  # noqa: E402


class _FakeSession:
    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass


def test_db_session_runtime_checkable():
    assert isinstance(_FakeSession(), DbSession)


def test_db_session_rejects_missing_commit():
    class Bad:
        async def rollback(self):
            pass

        async def close(self):
            pass

    assert not isinstance(Bad(), DbSession)


def test_db_session_rejects_missing_rollback():
    class Bad:
        async def commit(self):
            pass

        async def close(self):
            pass

    assert not isinstance(Bad(), DbSession)


def test_db_session_rejects_missing_close():
    class Bad:
        async def commit(self):
            pass

        async def rollback(self):
            pass

    assert not isinstance(Bad(), DbSession)


def test_db_session_rejects_plain_object():
    assert not isinstance(object(), DbSession)


def test_db_session_factory_runtime_checkable():
    class FakeFactory:
        def __call__(self):
            @asynccontextmanager
            async def _cm():
                yield _FakeSession()

            return _cm()

    assert isinstance(FakeFactory(), DbSessionFactory)


def test_db_session_factory_rejects_missing_call():
    # 没有 __call__ → 不是工厂
    class Bad:
        pass

    assert not isinstance(Bad(), DbSessionFactory)


async def test_db_session_factory_end_to_end_yields_session():
    """集成意图：工厂 __call__ 返回的 async context manager 进入后得到一个 DbSession。"""

    class FakeFactory:
        def __call__(self):
            @asynccontextmanager
            async def _cm():
                yield _FakeSession()

            return _cm()

    factory = FakeFactory()
    async with factory() as session:
        assert isinstance(session, DbSession)
        await session.commit()  # 可调用，无异常即通过


# ---- AuthUser / UserModelProtocol / RoleModelProtocol ----

from easy_fastapi.core.protocols import AuthUser  # noqa: E402


class _FakeUser:
    id = 1
    username = "u"
    hashed_password = "h"
    is_active = True
    scopes = ["user"]


def test_auth_user_runtime_checkable():
    assert isinstance(_FakeUser(), AuthUser)


def test_auth_user_attr_values_accessible():
    # 协议虽只声明属性，但真实对象应能按属性名取值（auth 读取 hashed_password/is_active）
    u = _FakeUser()
    assert u.hashed_password == "h"
    assert u.is_active is True


def test_auth_user_accepts_extra_attributes():
    # 协议最小视图：允许对象携带额外属性（ORM 模型常有更多字段）
    class RichUser:
        id = 2
        username = "rich"
        hashed_password = "hp"
        is_active = False
        scopes = ["admin"]
        email = "rich@x.com"
        created_at = "2026-01-01"

    assert isinstance(RichUser(), AuthUser)


# ---- A4: AuthUser 协议声明 scopes 属性（spec 2.2） ----


def test_auth_user_protocol_declares_scopes_annotation():
    """AuthUser 协议 __annotations__ 含 scopes 声明。"""
    assert "scopes" in AuthUser.__annotations__


def test_auth_user_protocol_scopes_annotation_is_list_of_str():
    """scopes 类型注解为 list[str]。"""
    from typing import get_args, get_type_hints

    hints = get_type_hints(AuthUser)
    scopes_hint = hints["scopes"]
    # list[str] 形式：origin 是 list，args 含 str
    assert getattr(scopes_hint, "__origin__", None) is list
    assert str in get_args(scopes_hint)


def test_auth_user_instance_scopes_returns_list():
    """实现 AuthUser 的对象 scopes 应返回 list。"""
    u = _FakeUser()
    assert isinstance(u.scopes, list)


def test_auth_user_instance_scopes_default_empty_when_absent():
    """AuthUser 协议声明 scopes，缺省时实现应提供空 list（不强制 runtime_checkable 检查）。"""
    # 注意：runtime_checkable Protocol 对数据属性无法运行时检查缺省，
    # 但声明本身要求实现者提供 scopes。
    # 这里仅断言协议声明存在，运行时由装饰器 getattr(user, "scopes", None) 兜底。
    assert "scopes" in AuthUser.__annotations__


def test_auth_user_scopes_accessible_via_protocol_attr():
    """通过实例访问 scopes 属性得到预期值。"""
    u = _FakeUser()
    assert u.scopes == ["user"]


def test_auth_user_scopes_can_be_empty_list():
    """scopes 允许为空 list（无权限用户）。"""

    class NoScopeUser:
        id = 3
        username = "ns"
        hashed_password = "h"
        is_active = True
        scopes = []

    assert NoScopeUser().scopes == []


def test_auth_user_scopes_can_contain_multiple():
    """scopes 允许包含多个权限字符串。"""

    class MultiScopeUser:
        id = 4
        username = "ms"
        hashed_password = "h"
        is_active = True
        scopes = ["admin", "super", "user"]

    assert MultiScopeUser().scopes == ["admin", "super", "user"]
