"""分页通用结果模型（ORM 无关）。

供各 ORM 实现的列表查询返回统一结构：total（总数）、items（当页数据）、finished（是否最后一页）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

# 分页参数下界
_MIN_PAGE_INDEX = 1
_MIN_PAGE_SIZE = 1


def validate_page_params(page_index: int, page_size: int) -> tuple[int, int]:
    """校验并规范化分页参数，防止负 offset / 零 size 导致 SQL 错误。

    - page_index < 1 → 1（首页）
    - page_size < 1 → 1（至少一条）
    """
    if page_index < _MIN_PAGE_INDEX:
        page_index = _MIN_PAGE_INDEX
    if page_size < _MIN_PAGE_SIZE:
        page_size = _MIN_PAGE_SIZE
    return page_index, page_size


def calc_finished(total: int, page_index: int, page_size: int) -> bool:
    """判断是否已到最后一页。

    finished = total <= page_index * page_size
    此公式在 validate_page_params 保证 page_index>=1, page_size>=1 后不会出现除零或越界。
    """
    return total <= page_index * page_size


@dataclass
class Pagination(Generic[T]):
    """通用分页结果。"""

    total: int
    items: list[T]
    finished: bool
