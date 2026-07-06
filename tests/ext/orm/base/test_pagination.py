"""Pagination 通用分页结果模型测试（ORM 无关）。

覆盖：三字段持有、泛型、默认值、可变性、相等比较、空 items、
大列表、不同元素类型、与旧 db.Pagination 字段一致。
validate_page_params / calc_finished 边界校验。
"""

import pytest
from easy_fastapi.ext.orm.base.pagination import (
    Pagination,
    calc_finished,
    validate_page_params,
)


def test_pagination_holds_three_fields():
    p = Pagination(total=10, items=[1, 2, 3], finished=False)
    assert p.total == 10
    assert p.items == [1, 2, 3]
    assert p.finished is False


def test_pagination_generic_str_items():
    p = Pagination[str](total=2, items=["a", "b"], finished=True)
    assert p.items == ["a", "b"]


def test_pagination_generic_dict_items():
    p = Pagination[dict](total=1, items=[{"k": 1}], finished=False)
    assert p.items == [{"k": 1}]


def test_pagination_empty_items():
    p = Pagination(total=0, items=[], finished=True)
    assert p.items == []
    assert p.total == 0


def test_pagination_is_dataclass():
    # 用构造器关键字参数实例化（dataclass 语义）
    import dataclasses

    assert dataclasses.is_dataclass(Pagination)


def test_pagination_fields_in_order():
    import dataclasses

    names = [f.name for f in dataclasses.fields(Pagination)]
    assert names == ["total", "items", "finished"]


def test_pagination_all_fields_required_no_defaults():
    # dataclass 无默认值，缺参应报 TypeError

    with pytest.raises(TypeError):
        Pagination(total=1)  # type: ignore[call-arg]


def test_pagination_equality():
    a = Pagination(total=3, items=[1, 2, 3], finished=False)
    b = Pagination(total=3, items=[1, 2, 3], finished=False)
    assert a == b


def test_pagination_inequality_on_finished():
    a = Pagination(total=3, items=[1, 2, 3], finished=False)
    b = Pagination(total=3, items=[1, 2, 3], finished=True)
    assert a != b


def test_pagination_mutable_items_list():
    # items 是普通 list，外部可变（非冻结）
    items = [1, 2]
    p = Pagination(total=2, items=items, finished=False)
    items.append(3)
    assert p.items == [1, 2, 3]


# ── validate_page_params ──


class TestValidatePageParams:
    def test_normal_values_unchanged(self):
        assert validate_page_params(2, 10) == (2, 10)

    def test_page_index_zero_clamped_to_one(self):
        assert validate_page_params(0, 10) == (1, 10)

    def test_page_index_negative_clamped_to_one(self):
        assert validate_page_params(-5, 10) == (1, 10)

    def test_page_size_zero_clamped_to_one(self):
        assert validate_page_params(1, 0) == (1, 1)

    def test_page_size_negative_clamped_to_one(self):
        assert validate_page_params(1, -3) == (1, 1)

    def test_both_invalid_clamped(self):
        assert validate_page_params(-1, 0) == (1, 1)


# ── calc_finished ──


class TestCalcFinished:
    def test_last_page(self):
        assert calc_finished(total=20, page_index=2, page_size=10) is True

    def test_not_last_page(self):
        assert calc_finished(total=25, page_index=2, page_size=10) is False

    def test_single_page(self):
        assert calc_finished(total=5, page_index=1, page_size=10) is True

    def test_exact_page_boundary(self):
        assert calc_finished(total=10, page_index=1, page_size=10) is True

    def test_empty_result(self):
        assert calc_finished(total=0, page_index=1, page_size=10) is True


def test_pagination_large_total():
    p = Pagination(total=1_000_000, items=list(range(100)), finished=False)
    assert p.total == 1_000_000
    assert len(p.items) == 100
