# tests/cli/test_plugin_loader.py
"""CLI 插件发现与注册测试。"""

import pkgutil
import sys
from types import ModuleType

import typer
from easy_fastapi_cli.plugin_loader import load_plugins
from easy_fastapi_cli.plugin_protocol import CLIPlugin


class _DummyPlugin:
    """测试用假插件。"""

    name = "dummy"

    def register(self, app, *, rich_help_panel=None):
        sub = typer.Typer(help="测试插件", no_args_is_help=True)

        @sub.command()
        def hello():
            typer.echo("hello from dummy")

        app.add_typer(sub, name="dummy", rich_help_panel=rich_help_panel)


def test_cli_plugin_protocol_duck_type():
    """不继承基类，鸭子类型满足 CLIPlugin 协议。"""
    plugin = _DummyPlugin()
    assert isinstance(plugin, CLIPlugin)


def test_cli_plugin_protocol_not_match():
    """缺少 name 属性的对象不满足协议。"""

    class NotAPlugin:
        def register(self, app, *, rich_help_panel=None): ...

    assert not isinstance(NotAPlugin(), CLIPlugin)


def test_discover_builtin_plugins_finds_cli_module(monkeypatch):
    """约定扫描：easy_fastapi.ext.{name}.cli 有 cli_plugin 对象时加载。"""
    from easy_fastapi_cli.plugin_loader import _discover_builtin_plugins

    # 构造一个 fake easy_fastapi.ext.i18n.cli 模块
    fake_cli = ModuleType("easy_fastapi.ext.i18n.cli")
    fake_cli.cli_plugin = _DummyPlugin()

    # 让 easy_fastapi.ext.i18n 是一个包
    fake_i18n_pkg = ModuleType("easy_fastapi.ext.i18n")
    fake_i18n_pkg.__path__ = ["fake"]
    fake_i18n_pkg.__package__ = "easy_fastapi.ext.i18n"

    fake_ext = ModuleType("easy_fastapi.ext")
    fake_ext.__path__ = ["/fake/ext"]

    # 注入 fake 模块
    monkeypatch.setitem(sys.modules, "easy_fastapi.ext", fake_ext)
    monkeypatch.setitem(sys.modules, "easy_fastapi.ext.i18n", fake_i18n_pkg)
    monkeypatch.setitem(sys.modules, "easy_fastapi.ext.i18n.cli", fake_cli)

    # 让 pkgutil.iter_modules 发现 i18n 包
    def fake_pkgutil_iter(paths):
        return [pkgutil.ModuleInfo(module_finder=None, name="i18n", ispkg=True)]

    monkeypatch.setattr(pkgutil, "iter_modules", fake_pkgutil_iter)

    plugins = _discover_builtin_plugins()
    assert len(plugins) == 1
    assert plugins[0].name == "dummy"


def test_discover_builtin_plugins_skips_no_cli(monkeypatch):
    """扩展没有 cli.py 模块时正常跳过。"""
    from easy_fastapi_cli.plugin_loader import _discover_builtin_plugins

    fake_ext = ModuleType("easy_fastapi.ext")
    fake_ext.__path__ = ["/fake/ext"]
    monkeypatch.setitem(sys.modules, "easy_fastapi.ext", fake_ext)

    def fake_pkgutil_iter(paths):
        return [pkgutil.ModuleInfo(module_finder=None, name="auth", ispkg=True)]

    monkeypatch.setattr(pkgutil, "iter_modules", fake_pkgutil_iter)

    plugins = _discover_builtin_plugins()
    assert len(plugins) == 0


def test_discover_builtin_plugins_graceful_when_core_not_installed(monkeypatch):
    """easy_fastapi 未安装时返回空列表，不报错。"""
    from easy_fastapi_cli.plugin_loader import _discover_builtin_plugins

    monkeypatch.delitem(sys.modules, "easy_fastapi.ext", raising=False)
    monkeypatch.setitem(sys.modules, "easy_fastapi", None)
    plugins = _discover_builtin_plugins()
    assert plugins == []


class _BrokenPlugin:
    """注册时抛异常的插件。"""

    name = "broken"

    def register(self, app, *, rich_help_panel=None):
        raise RuntimeError("plugin broken")


class _ConflictPlugin:
    """与 DummyPlugin 同名的插件。"""

    name = "dummy"

    def register(self, app, *, rich_help_panel=None):
        pass


def test_load_plugins_skips_duplicate_name(monkeypatch):
    """同名插件先到先得，后者跳过。"""
    app = typer.Typer()
    monkeypatch.setattr(
        "easy_fastapi_cli.plugin_loader._discover_builtin_plugins",
        lambda: [_DummyPlugin(), _ConflictPlugin()],
    )
    monkeypatch.setattr(
        "easy_fastapi_cli.plugin_loader._discover_entrypoint_plugins",
        lambda: [],
    )

    loaded = load_plugins(app)
    assert len(loaded) == 1
    assert loaded[0].name == "dummy"


def test_load_plugins_isolates_broken_plugin(monkeypatch):
    """单个插件注册失败不阻塞其他插件。"""
    app = typer.Typer()
    monkeypatch.setattr(
        "easy_fastapi_cli.plugin_loader._discover_builtin_plugins",
        lambda: [_BrokenPlugin(), _DummyPlugin()],
    )
    monkeypatch.setattr(
        "easy_fastapi_cli.plugin_loader._discover_entrypoint_plugins",
        lambda: [],
    )

    loaded = load_plugins(app)
    assert len(loaded) == 1
    assert loaded[0].name == "dummy"
