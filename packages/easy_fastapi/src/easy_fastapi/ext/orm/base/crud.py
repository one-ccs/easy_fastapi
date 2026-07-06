"""ORM 无关的 CRUD 方法协议。

各 ORM 的 ExtendedCRUD mixin 实现此协议，保证统一方法签名。
生成项目的 service 层只调用这些方法，不直接使用 ORM 原生 API。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from easy_fastapi.ext.orm.base.pagination import Pagination


@runtime_checkable
class BaseCRUDMixin(Protocol):
    """统一 CRUD 接口协议。

    所有方法为 classmethod，cls 即模型类本身。
    各 ORM（tortoise / sqlalchemy / sqlmodel）的 ExtendedCRUD mixin 实现此协议，
    使生成项目的 service 层可在任意 ORM 下运行。
    """

    @classmethod
    async def by_id(cls, id: int, prefetch: tuple | None = None) -> Any:
        """按主键查询单条记录。

        Args:
            id: 主键值。
            prefetch: 需预加载的关系字段元组，None 表示不预加载。

        Returns:
            模型实例，未找到时返回 None。
        """
        ...

    @classmethod
    async def paginate(
        cls,
        page_index: int,
        page_size: int,
        prefetch: tuple | None = None,
    ) -> Pagination:
        """分页查询。

        Args:
            page_index: 页码（从 1 开始）。
            page_size: 每页条数。
            prefetch: 需预加载的关系字段元组。

        Returns:
            Pagination(total, items, finished)。
        """
        ...

    @classmethod
    async def create(cls, **kwargs: Any) -> Any:
        """创建记录并返回实例。"""
        ...

    @classmethod
    async def update_from_dict(cls, instance: Any, data: dict) -> Any:
        """更新实例字段并保存。

        Args:
            instance: 待更新的模型实例。
            data: 字段名 → 新值的映射。

        Returns:
            更新后的实例。
        """
        ...

    @classmethod
    async def delete_by_ids(cls, ids: list[int]) -> int:
        """按 id 列表批量删除。

        Args:
            ids: 主键值列表。

        Returns:
            实际删除的记录数。
        """
        ...
