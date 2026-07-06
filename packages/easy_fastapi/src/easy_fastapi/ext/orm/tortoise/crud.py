"""Tortoise ExtendedCRUD + Pagination（来自 base）。

设计为 mixin 类：by_id/paginate 作为 classmethod，继承后 cls 即模型类。
生成项目中 User/Role 继承 ExtendedCRUD 即可获得 by_id/paginate。
"""

from __future__ import annotations

from typing import Any

from easy_fastapi.ext.orm.base.pagination import Pagination, calc_finished, validate_page_params


class ExtendedCRUD:
    """Tortoise CRUD 工具（by_id / paginate / create / update_from_dict / delete_by_ids），作为模型 mixin 使用。"""

    @classmethod
    async def by_id(cls, id: int, prefetch: tuple | None = None) -> Any:
        qs = cls.get_or_none(id=id)
        if prefetch:
            qs = qs.prefetch_related(*prefetch)
        return await qs

    @classmethod
    async def paginate(
        cls,
        page_index: int,
        page_size: int,
        prefetch: tuple | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Pagination:
        page_index, page_size = validate_page_params(page_index, page_size)
        base = cls.filter(*args, **kwargs)
        if prefetch:
            base = base.prefetch_related(*prefetch)
        total = await base.count()
        items = await base.limit(page_size).offset((page_index - 1) * page_size)
        return Pagination(total=total, items=list(items), finished=calc_finished(total, page_index, page_size))

    @classmethod
    async def create(cls, **kwargs: Any) -> Any:
        """创建记录并返回实例。

        不直接调用 cls.create 以避免与自身递归；
        走 Tortoise Model 的实例化 + save 路径。
        """
        instance = cls(**kwargs)
        await instance.save()
        return instance

    @classmethod
    async def update_from_dict(cls, instance: Any, data: dict) -> Any:
        """更新实例字段并保存。"""
        instance.update_from_dict(data)
        await instance.save()
        return instance

    @classmethod
    async def delete_by_ids(cls, ids: list[int]) -> int:
        """按 id 列表批量删除，返回删除数量。"""
        if not ids:
            return 0
        return await cls.filter(id__in=ids).delete()

    @classmethod
    async def exists(cls, **filters: Any) -> bool:
        """按过滤条件查询是否存在记录。

        例：User.exists(username='u0') / Role.exists(role='admin')。
        """
        if not filters:
            raise ValueError("exists() 至少需要一个过滤条件")
        return bool(await cls.filter(**filters).exists())

    @classmethod
    async def exists_by_email(cls, email: str) -> bool:
        """按 email 查询是否存在记录（User 模型用）。"""
        return bool(await cls.filter(email=email).exists())

    @classmethod
    async def get_or_create(cls, **kwargs: Any) -> Any:
        """按过滤条件查询；不存在则创建。返回 (instance, created)。

        代理到 Tortoise Model.get_or_create，避免与自身递归。
        """
        from tortoise import Model

        return await Model.get_or_create(cls, **kwargs)

    # ── 业务方法（原 repository 迁入，classmethod，Tortoise 原生 Manager 风格） ──

    @classmethod
    async def get_by_username(cls, username: str | None) -> Any:
        """按用户名查询。"""
        return await cls.get_or_none(username=username)

    @classmethod
    async def get_by_id(cls, id: int) -> Any:
        """按 ID 查询（业务方法，与 CRUD by_id 语义相同但签名更简）。"""
        return await cls.get_or_none(id=id)

    @classmethod
    async def get_by_email(cls, email: str | None) -> Any:
        """按邮箱查询。"""
        return await cls.get_or_none(email=email)

    @classmethod
    async def get_by_username_or_email(cls, username_or_email: str | None) -> Any:
        """按用户名或邮箱查询。

        若模型有 roles 关系则预加载（auth 登录后读取 scopes）。
        """
        from tortoise.expressions import Q

        qs = cls.filter(Q(username=username_or_email) | Q(email=username_or_email))
        if "roles" in cls._meta.fields_map or "roles" in cls._meta.fetch_fields:
            qs = qs.prefetch_related("roles")
        return await qs.first()

    @classmethod
    async def create_user(cls, username: str | None, hashed_password: str, **extra) -> Any:
        """创建用户（注册专用）。"""
        return await cls.create(username=username, hashed_password=hashed_password, **extra)

    @classmethod
    async def update_password(cls, id: int, hashed_password: str) -> None:
        """更新用户密码。"""
        await cls.filter(id=id).update(hashed_password=hashed_password)

    # ── Role 业务方法 ──

    @classmethod
    async def get_by_role(cls, role: str) -> Any:
        """按角色名查询。"""
        return await cls.get_or_none(role=role)

    @classmethod
    async def create_role(cls, role: str, role_desc: str, **extra) -> Any:
        """创建角色。"""
        return await cls.create(role=role, role_desc=role_desc, **extra)
