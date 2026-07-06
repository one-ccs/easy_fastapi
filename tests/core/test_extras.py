"""可选依赖守卫 require() 测试。

覆盖：目标缺失翻译、父包缺失翻译、未知包 fallback 提示、异常链、
消息内容、已存在模块正常返回、模块名带点顶层匹配、返回模块可用。
"""

import builtins
import importlib

import pytest
from easy_fastapi.core.exceptions import ExtensionError
from easy_fastapi.core.extras import require

REAL_IMPORT = builtins.__import__


def _make_missing_import(missing_top: str):
    """构造 import 拦截器：导入以 missing_top 为顶层名的模块时抛 ModuleNotFoundError。"""

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        top = name.split(".")[0]
        if top == missing_top:
            raise ModuleNotFoundError(f"No module named '{missing_top}'", name=missing_top)
        return REAL_IMPORT(name, globals, locals, fromlist, level)

    return fake_import


# ---- 正常路径 ----


def test_require_present_module_returns_module():
    mod = require("stdlib-json-fake", "json")
    assert mod is importlib.import_module("json")


def test_require_returns_usable_module():
    # 返回的模块应可正常访问属性
    mod = require("stdlib-json-fake", "json")
    assert mod.loads('{"a": 1}') == {"a": 1}


def test_require_missing_target_module_raises_extension_error(monkeypatch):
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError) as exc_info:
        require("tortoise-orm", "tortoise.orm")
    msg = str(exc_info.value)
    assert "tortoise-orm" in msg
    assert "uv add tortoise-orm" in msg


def test_require_missing_target_parent_package(monkeypatch):
    # 父包 tortoise 没装，tortoise.expressions 同样翻译
    # 需先移除 sys.modules 缓存（前面测试可能已 import tortoise）
    import sys

    tortoise_keys = [k for k in sys.modules if k.startswith("tortoise")]
    for k in tortoise_keys:
        monkeypatch.delitem(sys.modules, k, raising=False)
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError) as exc_info:
        require("tortoise-orm", "tortoise.expressions")
    assert "tortoise-orm" in str(exc_info.value)


def test_require_missing_dotted_top_matches(monkeypatch):
    # module_name 带点：顶层 = tortoise，缺失 tortoise → 翻译
    import sys

    tortoise_keys = [k for k in sys.modules if k.startswith("tortoise")]
    for k in tortoise_keys:
        monkeypatch.delitem(sys.modules, k, raising=False)
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError):
        require("tortoise-orm", "tortoise.models")


# ---- 提示与消息内容 ----


def test_require_unknown_package_uses_generic_hint(monkeypatch):
    # 不在 _MISSING_HINT 映射中的包名 → fallback 到 `uv add {package}`
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("acme_orm"))
    with pytest.raises(ExtensionError) as exc_info:
        require("acme-orm", "acme_orm")
    msg = str(exc_info.value)
    assert "uv add acme-orm" in msg


def test_require_message_includes_module_name(monkeypatch):
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError) as exc_info:
        require("tortoise-orm", "tortoise.orm")
    assert "tortoise.orm" in str(exc_info.value)


def test_require_message_includes_original_error(monkeypatch):
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError) as exc_info:
        require("tortoise-orm", "tortoise.orm")
    assert "原始错误" in str(exc_info.value)


# ---- 异常链（集成意图：上层可顺链追溯根因） ----


def test_require_chains_original_cause(monkeypatch):
    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(ExtensionError) as exc_info:
        require("tortoise-orm", "tortoise.orm")
    assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)


def test_require_error_is_extension_error_subclass(monkeypatch):
    # ExtensionError 继承 EasyFastAPIError，可被框架根异常统一捕获
    from easy_fastapi.core.exceptions import EasyFastAPIError

    monkeypatch.setattr(builtins, "__import__", _make_missing_import("tortoise"))
    with pytest.raises(EasyFastAPIError):
        require("tortoise-orm", "tortoise.orm")


# ---- 子依赖缺失与运行时异常不误包装 ----


def test_require_subdependency_missing_not_wrapped(tmp_path):
    """目标模块 acme 存在（可被定位），但其内部 import 的 ghost_dep 缺失 → 原样抛 ModuleNotFoundError。

    必须用真实模块文件复现：importlib 在导入顶层模块时会把最外层 ModuleNotFoundError
    归一化为「找不到该顶层」，从而抹掉真实的子依赖名；只有真实子 import 语句抛出的
    ModuleNotFoundError 才能携带正确的 e.name='ghost_dep'，正确驱动不误包装判定。
    """
    import sys

    pkg = tmp_path / "acme"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import ghost_dep\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(ModuleNotFoundError) as exc_info:
            require("acme", "acme")
        # 真实子依赖缺失：异常 name 指向 ghost_dep，未被 require 翻译/包装
        assert exc_info.value.name == "ghost_dep"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("acme", None)


def test_require_subdependency_missing_is_not_extension_error(tmp_path):
    """子依赖缺失原样抛 ModuleNotFoundError，绝不被包装成 ExtensionError。"""
    import sys

    pkg = tmp_path / "acme"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import ghost_dep\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        try:
            require("acme", "acme")
        except ExtensionError as e:  # pragma: no cover - 不应进入
            pytest.fail(f"不应包装为 ExtensionError：{e}")
        except ModuleNotFoundError:
            pass  # 预期路径
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("acme", None)


def test_require_internal_runtime_error_not_wrapped(tmp_path):
    """模块存在但 import 时内部抛 RuntimeError → 原样抛出（except 只捕获 ModuleNotFoundError）。"""
    import sys

    mod_file = tmp_path / "boom_mod.py"
    mod_file.write_text('raise RuntimeError("init explosion")\n', encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(RuntimeError):
            require("boom-pkg", "boom_mod")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("boom_mod", None)


def test_require_internal_value_error_not_wrapped(tmp_path):
    """模块内部抛其它非 ModuleNotFoundError 异常（ValueError）同样原样抛出。"""
    import sys

    mod_file = tmp_path / "bad_mod.py"
    mod_file.write_text('raise ValueError("bad config")\n', encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(ValueError):
            require("bad-pkg", "bad_mod")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("bad_mod", None)


def test_require_is_target_missing_helper_false():
    """白盒：ghost_dep 相对 acme 不匹配 → False（驱动不误包装判定）。"""
    from easy_fastapi.core.extras import _is_target_missing

    assert _is_target_missing("ghost_dep", "acme") is False


def test_require_is_target_missing_helper_true():
    """白盒：tortoise 相对 tortoise.orm 同顶层 → True。"""
    from easy_fastapi.core.extras import _is_target_missing

    assert _is_target_missing("tortoise", "tortoise.orm") is True
