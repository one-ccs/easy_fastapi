"""核心服务协议。

所有需要被 ctx.require(key, type_) 运行时校验的协议统一 @runtime_checkable。
覆盖 Persistence/PasswordHasher、DbSession/DbSessionFactory、
AuthUser/UserModelProtocol/RoleModelProtocol、ModelIntrospector。
"""

from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Persistence(Protocol):
    """登出令牌黑名单 / 临时存储协议。"""

    async def get(self, key: str) -> Any: ...

    async def set(self, key: str, value: Any, ex: int | None = None) -> Any: ...

    async def delete(self, key: str) -> Any: ...


@runtime_checkable
class PasswordHasher(Protocol):
    """密码哈希协议（pwdlib 实现）。"""

    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed: str) -> bool: ...


@runtime_checkable
class DbSession(Protocol):
    """ORM 内部会话协议。"""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def close(self) -> None: ...


@runtime_checkable
class DbSessionFactory(Protocol):
    """会话工厂：调用返回一个异步上下文管理器，进入得到 DbSession。"""

    def __call__(self) -> AbstractAsyncContextManager: ...


@runtime_checkable
class AuthUser(Protocol):
    """最小用户视图（auth 不暴露 ORM 模型类）。"""

    id: int
    username: str
    hashed_password: str
    is_active: bool
    scopes: list[str]


@runtime_checkable
class UserModelProtocol(Protocol):
    """用户模型协议（替代 UserRepository）。

    User 类本身满足此协议：提供认证业务 classmethod。
    ORM 扩展 provide('user_model', User)，auth require('user_model', UserModelProtocol)。
    CRUD 能力（by_id/paginate/create/update_from_dict/delete_by_ids）由各 ORM 的
    CRUDMixin 提供（满足 BaseCRUDMixin 协议），此处不重复声明。
    """

    @classmethod
    async def get_by_username(cls, username: str | None) -> AuthUser | None: ...

    @classmethod
    async def get_by_id(cls, id: int) -> AuthUser | None: ...

    @classmethod
    async def get_by_email(cls, email: str | None) -> AuthUser | None: ...

    @classmethod
    async def get_by_username_or_email(cls, username_or_email: str | None) -> AuthUser | None: ...

    @classmethod
    async def create_user(cls, username: str | None, hashed_password: str, **extra) -> AuthUser: ...

    @classmethod
    async def update_password(cls, id: int, hashed_password: str) -> None: ...


@runtime_checkable
class RoleModelProtocol(Protocol):
    """角色模型协议。

    Role 类本身满足此协议。ORM 扩展 provide('role_model', Role)。
    """

    @classmethod
    async def get_by_id(cls, id: int) -> Any: ...

    @classmethod
    async def get_by_role(cls, role: str) -> Any: ...

    @classmethod
    async def create_role(cls, role: str, role_desc: str, **extra) -> Any: ...
