"""SQLAlchemy CRUD mixin（by_id / paginate / create / update_from_dict / delete_by_ids
+ 业务方法 get_by_username / get_by_id / get_by_email / get_by_username_or_email /
create_user / update_password）。

作为模型 mixin 使用：生成项目的模型继承此 mixin + SQLAlchemy Declarative Base 即可获得全部能力。
需在模型类上设置 _sa_session_factory 属性（由扩展 init_app 时注入）。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from easy_fastapi.core.extras import require
from easy_fastapi.ext.orm.base.pagination import Pagination, calc_finished, validate_page_params

sa = require("sqlalchemy", "sqlalchemy")


class SQLAlchemyCRUDMixin:
    """SQLAlchemy CRUD + 业务方法 mixin。

    子类需设置 _sa_session_factory: Callable[[], AsyncSession]。
    由 SQLAlchemyExtension.init_app 在注入时设置。
    """

    _sa_session_factory: Any = None

    # ── session 管理（自动 commit-on-success / rollback-on-error） ──

    @classmethod
    @asynccontextmanager
    async def _session(cls):
        """AsyncSession 上下文管理器：commit-on-success / rollback-on-error / always-close。"""
        s = cls._sa_session_factory()
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise
        finally:
            await s.close()

    # ── CRUD 方法（协议: BaseCRUDMixin） ──

    @classmethod
    async def by_id(cls, id: int, prefetch: tuple | None = None) -> Any:
        """按主键查询单条记录。"""
        async with cls._session() as s:
            result = await s.get(cls, id)
            if prefetch and result is not None:
                for rel in prefetch:
                    await s.refresh(result, attribute_names=[rel])
            return result

    @classmethod
    async def paginate(
        cls,
        page_index: int,
        page_size: int,
        prefetch: tuple | None = None,
    ) -> Pagination:
        """分页查询。"""
        page_index, page_size = validate_page_params(page_index, page_size)
        async with cls._session() as s:
            count_stmt = sa.select(sa.func.count()).select_from(cls)
            total = (await s.execute(count_stmt)).scalar() or 0
            stmt = sa.select(cls).limit(page_size).offset((page_index - 1) * page_size)
            if prefetch:
                from sqlalchemy.orm import selectinload

                for rel in prefetch:
                    stmt = stmt.options(selectinload(getattr(cls, rel)))
            items = list((await s.execute(stmt)).scalars().all())
            return Pagination(total=total, items=items, finished=calc_finished(total, page_index, page_size))

    @classmethod
    async def create(cls, **kwargs: Any) -> Any:
        """创建记录并返回实例。"""
        async with cls._session() as s:
            instance = cls(**kwargs)
            s.add(instance)
            await s.flush()
            await s.refresh(instance)
            return instance

    @classmethod
    async def update_from_dict(cls, instance: Any, data: dict) -> Any:
        """更新实例字段并保存。

        instance 可能来自已关闭的 session（detached），
        通过 merge 重新关联到新 session 后更新。
        """
        async with cls._session() as s:
            merged = await s.merge(instance)
            for key, value in data.items():
                setattr(merged, key, value)
            await s.flush()
            await s.refresh(merged)
            # 同步原始实例的属性
            for key in data:
                setattr(instance, key, getattr(merged, key))
            return merged

    @classmethod
    async def delete_by_ids(cls, ids: list[int]) -> int:
        """按 id 列表批量删除，返回删除数量。"""
        if not ids:
            return 0
        async with cls._session() as s:
            stmt = sa.delete(cls).where(cls.id.in_(ids))
            result = await s.execute(stmt)
            return result.rowcount

    # ── 扩展 CRUD 方法（非协议，但三 ORM 一致） ──

    @classmethod
    async def exists(cls, **filters: Any) -> bool:
        """按过滤条件查询是否存在记录。

        例：User.exists(username='u0') / Role.exists(role='admin')。
        """
        if not filters:
            raise ValueError("exists() 至少需要一个过滤条件")
        async with cls._session() as s:
            conditions = [getattr(cls, key) == value for key, value in filters.items()]
            stmt = sa.select(cls.id).where(*conditions)
            result = await s.execute(stmt)
            return result.first() is not None

    @classmethod
    async def exists_by_email(cls, email: str) -> bool:
        """按 email 查询是否存在记录（User 模型用）。"""
        return await cls.exists(email=email)

    @classmethod
    async def get_or_create(cls, **kwargs: Any) -> tuple[Any, bool]:
        """按过滤条件查询；不存在则创建。返回 (instance, created)。"""
        async with cls._session() as s:
            conditions = [getattr(cls, key) == value for key, value in kwargs.items()]
            stmt = sa.select(cls).where(*conditions)
            result = await s.execute(stmt)
            instance = result.scalars().one_or_none()
            if instance is not None:
                return instance, False
        # 不存在 → 创建（走统一 create 路径）
        instance = await cls.create(**kwargs)
        return instance, True

    # ── 业务方法（原 repository 迁入，classmethod，原生 sa API） ──

    @classmethod
    async def get_by_username(cls, username: str | None) -> Any:
        """按用户名查询。"""
        async with cls._session() as s:
            return (await s.execute(sa.select(cls).where(cls.username == username))).scalar_one_or_none()

    @classmethod
    async def get_by_id(cls, id: int) -> Any:
        """按 ID 查询（业务方法，与 CRUD by_id 语义相同但签名更简）。"""
        async with cls._session() as s:
            return (await s.execute(sa.select(cls).where(cls.id == id))).scalar_one_or_none()

    @classmethod
    async def get_by_email(cls, email: str | None) -> Any:
        """按邮箱查询。"""
        async with cls._session() as s:
            return (await s.execute(sa.select(cls).where(cls.email == email))).scalar_one_or_none()

    @classmethod
    async def get_by_username_or_email(cls, username_or_email: str | None) -> Any:
        """按用户名或邮箱查询。

        若模型有 roles 关系则预加载（auth 登录后读取 scopes）。
        """
        from sqlalchemy.orm import selectinload

        async with cls._session() as s:
            stmt = sa.select(cls).where((cls.username == username_or_email) | (cls.email == username_or_email))
            if hasattr(cls, "roles"):
                stmt = stmt.options(selectinload(cls.roles))
            return (await s.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def create_user(cls, username: str | None, hashed_password: str, **extra) -> Any:
        """创建用户（注册专用，与 CRUD create(**kwargs) 区分）。"""
        async with cls._session() as s:
            u = cls(username=username, hashed_password=hashed_password, **extra)
            s.add(u)
            await s.flush()
            await s.refresh(u)
            return u

    @classmethod
    async def update_password(cls, id: int, hashed_password: str) -> None:
        """更新用户密码。"""
        async with cls._session() as s:
            u = (await s.execute(sa.select(cls).where(cls.id == id))).scalar_one_or_none()
            if u:
                u.hashed_password = hashed_password

    # ── Role 业务方法（与 Tortoise ExtendedCRUD 对齐，满足 RoleModelProtocol） ──

    @classmethod
    async def get_by_role(cls, role: str) -> Any:
        """按角色名查询。"""
        async with cls._session() as s:
            return (await s.execute(sa.select(cls).where(cls.role == role))).scalar_one_or_none()

    @classmethod
    async def create_role(cls, role: str, role_desc: str, **extra) -> Any:
        """创建角色。"""
        return await cls.create(role=role, role_desc=role_desc, **extra)
