"""非交互全参数模式 options_from_args 测试（≥8 用例）。"""

import pytest
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.wizard import options_from_args
from pydantic import ValidationError

# ── 1. 最小参数 ──


def test_from_args_minimal():
    o = options_from_args(project_name="demo", package_name="demo")
    assert o.project_name == "demo"
    assert o.frontend is False


# ── 2. 全参数 ──


def test_from_args_full():
    o = options_from_args(
        project_name="demo",
        package_name="demo",
        frontend=True,
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        migration=True,
        auth=True,
        redis=True,
        language="en",
    )
    assert o.frontend is True
    assert o.orm == "tortoise"
    assert o.migration is True
    assert o.language == "en"


# ── 3. package_name 缺省从 project slug ──


def test_from_args_default_package_from_project():
    o = options_from_args(project_name="demo")
    assert o.package_name == "demo"


# ── 4. package_name 缺省 slug 化 ──


def test_from_args_package_slug():
    o = options_from_args(project_name="My Cool Project")
    assert o.package_name == "my_cool_project"


# ── 5. 非法 orm 被拒 ──


def test_from_args_invalid_orm_rejected():
    with pytest.raises(ValidationError):
        options_from_args(project_name="demo", orm="invalid")


# ── 6. 非法 language 被拒 ──


def test_from_args_invalid_language_rejected():
    with pytest.raises(ValidationError):
        options_from_args(project_name="demo", language="jp")


# ── 7. 返回 CreateOptions 实例 ──


def test_from_args_returns_options():
    o = options_from_args(project_name="demo")
    assert isinstance(o, CreateOptions)


# ── 11. _slug 容忍 None/空（防御性，不抛 AttributeError）──


def test_slug_handles_none_and_empty():
    from easy_fastapi_cli.scaffold.wizard import _slug

    assert _slug(None) == "app"
    assert _slug("") == "app"
    assert _slug("   ") == "app"


def test_slug_numeric_only_falls_back_to_app():
    """纯数字/数字开头项目名 → fallback 'app'（不是合法 Python 包名）。"""
    from easy_fastapi_cli.scaffold.wizard import _slug

    assert _slug("123") == "app"
    assert _slug("1abc") == "app"


def test_slug_compresses_consecutive_underscores():
    """连续特殊字符 → 压缩为单下划线。"""
    from easy_fastapi_cli.scaffold.wizard import _slug

    assert _slug("My___Project") == "my_project"
