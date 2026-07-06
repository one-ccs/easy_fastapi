"""顶层导出约束。

只导出 core 稳定 API + 扩展分发入口 get_extension；import easy_fastapi 不应拖入
tortoise/redis 等重型可选依赖（仍经 ext.get_extension(name) 按需 import）；
旧 0.x 顶层符号（init_tortoise/ExtendedCRUD 等）不再导出（1.0 breaking）。

注：fastapi 已是 easy_fastapi 硬依赖，顶层 eager import 触达 fastapi
是预期行为（旧版 PEP 562 懒加载已移除）。可选依赖未被拖入的测试需在干净状态下
验证——若别的测试先 import 了 tortoise/redis，sys.modules 会被污染。本文件用
subprocess 在全新解释器里单独执行 import，确保结论可信。
"""

import subprocess
import sys

import easy_fastapi
import pytest

# core 稳定 API + 扩展分发入口导出清单（P1 契约）
_CORE_EXPORTS = [
    "EasyFastAPI",
    "get_extension_context",
    "EasyFastAPIError",
    "ExtensionError",
    "ConfigError",
    "FailureException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "Extension",
    "ExtensionContext",
    "ConfigLoader",
    "BaseResult",
    "Result",
    "ResponseResult",
    "get_extension",
    "__version__",
]

# 旧 0.x 顶层符号，1.0 不再导出（breaking）
# 注：BaseResult/Result/ResponseResult 已重新加入顶层导出（模板对齐设计）。
_LEGACY_BANNED = [
    "init_tortoise",
    "generate_schemas",
    "ExtendedCRUD",
    "Pagination",
    "Config",
    "DB",
    "db",
    "persistence",
    "authentication",
]


# ---- core API 导出 ----


def test_exports_core_stable_api():
    for name in _CORE_EXPORTS:
        assert hasattr(easy_fastapi, name), f"顶层应导出 core 稳定 API: {name}"


def test_all_lists_core_exports():
    # __all__ 至少包含全部 core 导出（允许更多，但 core 必须在）
    for name in _CORE_EXPORTS:
        assert name in easy_fastapi.__all__, f"{name} 应在 __all__ 中"


def test_version_is_1_0_0():
    assert easy_fastapi.__version__ == "1.0.0"


def test_easy_fastapi_is_class():
    from easy_fastapi.core.app import EasyFastAPI as CoreEasyFastAPI

    assert easy_fastapi.EasyFastAPI is CoreEasyFastAPI
    assert isinstance(easy_fastapi.EasyFastAPI, type)


def test_exception_hierarchy_exported():
    # EasyFastAPIError 是 ExtensionError/ConfigError 的基类
    assert issubclass(easy_fastapi.ExtensionError, easy_fastapi.EasyFastAPIError)
    assert issubclass(easy_fastapi.ConfigError, easy_fastapi.EasyFastAPIError)


# ---- 不拖入可选依赖（subprocess 全新解释器验证）----


def _import_in_clean_process() -> str:
    """在全新 python 子进程里 import easy_fastapi，返回 stdout（含诊断信息）。"""
    code = (
        "import sys; "
        "import easy_fastapi; "
        "print('tortoise', 'tortoise' in sys.modules); "
        "print('redis', 'redis' in sys.modules); "
        "print('version', easy_fastapi.__version__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_top_level_import_does_not_load_tortoise():
    out = _import_in_clean_process()
    assert "tortoise True" not in out, f"顶层 import 不应拖入 tortoise:\n{out}"
    assert "tortoise False" in out


def test_top_level_import_does_not_load_redis():
    out = _import_in_clean_process()
    assert "redis True" not in out, f"顶层 import 不应拖入 redis:\n{out}"
    assert "redis False" in out


def test_top_level_import_succeeds_and_reports_version():
    out = _import_in_clean_process()
    assert "version 1.0.0" in out


def test_top_level_import_eager_loads_core_symbols():
    # 顶层 eager import：core 符号在 import 时即可达，身份与子模块定义一致
    from easy_fastapi.core.app import EasyFastAPI as CoreEasyFastAPI
    from easy_fastapi.core.config.loader import ConfigLoader as CoreConfigLoader
    from easy_fastapi.core.context import get_extension_context as CoreFn
    from easy_fastapi.core.extension import Extension as CoreExtension
    from easy_fastapi.core.extension import ExtensionContext as CoreCtx

    assert easy_fastapi.EasyFastAPI is CoreEasyFastAPI
    assert easy_fastapi.ConfigLoader is CoreConfigLoader
    assert easy_fastapi.get_extension_context is CoreFn
    assert easy_fastapi.Extension is CoreExtension
    assert easy_fastapi.ExtensionContext is CoreCtx


def test_unknown_attribute_raises_attribute_error():
    with pytest.raises(AttributeError):
        easy_fastapi.definitely_not_a_real_attr  # noqa: B018


# ---- 旧符号不再导出 ----


def test_top_level_does_not_export_legacy_symbols():
    for name in _LEGACY_BANNED:
        assert not hasattr(easy_fastapi, name), f"顶层不应再导出旧符号: {name}"


def test_legacy_symbols_not_in_all():
    for name in _LEGACY_BANNED:
        assert name not in easy_fastapi.__all__, f"旧符号不应在 __all__: {name}"


def test_core_subpackage_importable_independently():
    # core 子包可独立 import，不依赖顶层 re-export
    import importlib

    for mod in [
        "easy_fastapi.core.app",
        "easy_fastapi.core.context",
        "easy_fastapi.core.extension",
        "easy_fastapi.core.config.loader",
        "easy_fastapi.core.exceptions",
    ]:
        importlib.import_module(mod)


# ---- E13: result/exceptions 符号验证（spec 6.5）----


def test_top_level_exports_result_symbols():
    """顶层导出 result 模块符号。"""
    from easy_fastapi.core.result import BaseResult as CoreBaseResult
    from easy_fastapi.core.result import ResponseResult as CoreResponseResult
    from easy_fastapi.core.result import Result as CoreResult

    assert easy_fastapi.BaseResult is CoreBaseResult
    assert easy_fastapi.Result is CoreResult
    assert easy_fastapi.ResponseResult is CoreResponseResult


def test_top_level_exports_business_exceptions():
    """顶层导出业务异常符号。"""
    from easy_fastapi.core.exceptions import (
        FailureException as CoreFailure,
    )
    from easy_fastapi.core.exceptions import (
        ForbiddenException as CoreForbidden,
    )
    from easy_fastapi.core.exceptions import (
        NotFoundException as CoreNotFound,
    )
    from easy_fastapi.core.exceptions import (
        UnauthorizedException as CoreUnauthorized,
    )

    assert easy_fastapi.FailureException is CoreFailure
    assert easy_fastapi.UnauthorizedException is CoreUnauthorized
    assert easy_fastapi.ForbiddenException is CoreForbidden
    assert easy_fastapi.NotFoundException is CoreNotFound


def test_top_level_result_symbols_are_classes():
    """BaseResult/Result/ResponseResult 是类/类型。"""
    assert isinstance(easy_fastapi.BaseResult, type)
    assert isinstance(easy_fastapi.Result, type)
    assert isinstance(easy_fastapi.ResponseResult, type)


def test_top_level_business_exceptions_are_http_exception_subclasses():
    """业务异常是 HTTPException 子类。"""
    from fastapi import HTTPException

    assert issubclass(easy_fastapi.FailureException, HTTPException)
    assert issubclass(easy_fastapi.UnauthorizedException, HTTPException)
    assert issubclass(easy_fastapi.ForbiddenException, HTTPException)
    assert issubclass(easy_fastapi.NotFoundException, HTTPException)


def test_top_level_result_import_does_not_drag_orm():
    """import Result 不应拖入 ORM 可选依赖。"""
    import subprocess
    import sys

    code = (
        "import sys; "
        "from easy_fastapi import BaseResult, Result, ResponseResult; "
        "print('tortoise', 'tortoise' in sys.modules); "
        "print('sqlalchemy', 'sqlalchemy' in sys.modules); "
        "print('sqlmodel', 'sqlmodel' in sys.modules)"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    out = result.stdout
    assert "tortoise True" not in out
    assert "sqlalchemy True" not in out
    assert "sqlmodel True" not in out
