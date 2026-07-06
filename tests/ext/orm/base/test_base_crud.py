"""BaseCRUDMixin 协议签名验证。"""

from __future__ import annotations

import inspect
from typing import Any

from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.base.pagination import Pagination

# ── 1. 协议基本属性 ──


def test_base_crud_is_runtime_checkable():
    """BaseCRUDMixin 是 runtime_checkable Protocol。"""

    # runtime_checkable 的 Protocol 有 __protocol_attrs__ 或可被 isinstance 使用
    assert isinstance(BaseCRUDMixin, type)
    # 确认它确实是 Protocol 子类
    from typing import Protocol

    assert issubclass(BaseCRUDMixin, Protocol)


def test_base_crud_is_not_abstract_base_class():
    """BaseCRUDMixin 是 Protocol 而非 ABC。"""
    import abc

    assert not issubclass(BaseCRUDMixin, abc.ABC)


# ── 2. by_id 方法签名 ──


def test_base_crud_declares_by_id():
    """协议声明 by_id classmethod。"""
    assert hasattr(BaseCRUDMixin, "by_id")


def test_by_id_signature_has_id_parameter():
    sig = inspect.signature(BaseCRUDMixin.by_id)
    params = list(sig.parameters.keys())
    # classmethod 的第一个参数是 cls，第二个是 id
    assert "id" in params


def test_by_id_has_prefetch_optional_parameter():
    sig = inspect.signature(BaseCRUDMixin.by_id)
    params = sig.parameters
    assert "prefetch" in params
    # prefetch 应有默认值 None
    assert params["prefetch"].default is not inspect.Parameter.empty


# ── 3. paginate 方法签名 ──


def test_base_crud_declares_paginate():
    assert hasattr(BaseCRUDMixin, "paginate")


def test_paginate_has_page_index_and_page_size():
    sig = inspect.signature(BaseCRUDMixin.paginate)
    params = list(sig.parameters.keys())
    assert "page_index" in params
    assert "page_size" in params


def test_paginate_has_prefetch_optional():
    sig = inspect.signature(BaseCRUDMixin.paginate)
    params = sig.parameters
    assert "prefetch" in params
    assert params["prefetch"].default is not inspect.Parameter.empty


# ── 4. create 方法签名 ──


def test_base_crud_declares_create():
    assert hasattr(BaseCRUDMixin, "create")


def test_create_accepts_kwargs():
    sig = inspect.signature(BaseCRUDMixin.create)
    params = list(sig.parameters.values())
    # classmethod(cls) + **kwargs
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    assert has_var_keyword, "create should accept **kwargs"


# ── 5. update_from_dict 方法签名 ──


def test_base_crud_declares_update_from_dict():
    assert hasattr(BaseCRUDMixin, "update_from_dict")


def test_update_from_dict_has_instance_and_data_params():
    sig = inspect.signature(BaseCRUDMixin.update_from_dict)
    params = list(sig.parameters.keys())
    assert "instance" in params
    assert "data" in params


# ── 6. delete_by_ids 方法签名 ──


def test_base_crud_declares_delete_by_ids():
    assert hasattr(BaseCRUDMixin, "delete_by_ids")


def test_delete_by_ids_has_ids_parameter():
    sig = inspect.signature(BaseCRUDMixin.delete_by_ids)
    params = list(sig.parameters.keys())
    assert "ids" in params


# ── 7. 协议可用于 isinstance 检查 ──


def test_concrete_class_satisfies_protocol():
    """一个实现了所有方法的类应满足 BaseCRUDMixin 协议。"""

    class ConcreteCRUD:
        @classmethod
        async def by_id(cls, id: int, prefetch: tuple | None = None) -> Any: ...

        @classmethod
        async def paginate(cls, page_index: int, page_size: int, prefetch: tuple | None = None) -> Pagination: ...

        @classmethod
        async def create(cls, **kwargs: Any) -> Any: ...

        @classmethod
        async def update_from_dict(cls, instance: Any, data: dict) -> Any: ...

        @classmethod
        async def delete_by_ids(cls, ids: list[int]) -> int: ...

    assert isinstance(ConcreteCRUD, BaseCRUDMixin)


def test_incomplete_class_does_not_satisfy_protocol():
    """缺少方法的类不满足协议（runtime_checkable 只检查方法存在性）。"""

    class IncompleteCRUD:
        @classmethod
        async def by_id(cls, id: int, prefetch: tuple | None = None) -> Any: ...

    # runtime_checkable 只做 has-a 检查；缺少方法时 isinstance 返回 False
    # 注意：Python Protocol runtime_checkable 检查的是方法/属性是否存在，不是签名
    # 缺少 paginate/create/update_from_dict/delete_by_ids
    assert not isinstance(IncompleteCRUD, BaseCRUDMixin)


# ── 8. 边界：参数类型注解 ──


def test_by_id_id_parameter_is_int_annotated():
    sig = inspect.signature(BaseCRUDMixin.by_id)
    id_param = sig.parameters.get("id")
    assert id_param is not None
    # 注解应为 int
    annotation = id_param.annotation
    assert annotation is int or "int" in str(annotation)


def test_delete_by_ids_ids_parameter_is_list_int_annotated():
    sig = inspect.signature(BaseCRUDMixin.delete_by_ids)
    ids_param = sig.parameters.get("ids")
    assert ids_param is not None
    annotation = str(ids_param.annotation)
    assert "list" in annotation.lower() and "int" in annotation.lower()


def test_paginate_page_index_is_int():
    sig = inspect.signature(BaseCRUDMixin.paginate)
    param = sig.parameters.get("page_index")
    assert param is not None
    annotation = param.annotation
    assert annotation is int or "int" in str(annotation)


def test_paginate_page_size_is_int():
    sig = inspect.signature(BaseCRUDMixin.paginate)
    param = sig.parameters.get("page_size")
    assert param is not None
    annotation = param.annotation
    assert annotation is int or "int" in str(annotation)


# ── 5. 顶层包导出验证 ──


def test_base_crud_importable_from_base_package():
    """BaseCRUDMixin 可从 easy_fastapi.ext.orm.base 直接导入。"""
    from easy_fastapi.ext.orm.base import BaseCRUDMixin as BCM

    assert BCM is BaseCRUDMixin


def test_base_crud_in_all():
    """BaseCRUDMixin 在 base/__init__.py 的 __all__ 中。"""
    import easy_fastapi.ext.orm.base as base_mod

    assert "BaseCRUDMixin" in base_mod.__all__
