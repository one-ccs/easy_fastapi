"""Renderer 测试（纯 Jinja2+StrictUndefined+generated_at，≥8 用例）。"""

import pytest
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.renderer import Renderer
from jinja2 import UndefinedError


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. 变量替换 project_name ──


def test_render_substitutes_project_name():
    r = Renderer(_mk())
    out = r.render("name={{ options.project_name }}")
    assert out == "name=demo"


# ── 2. generated_at 注入且非空 ──


def test_render_injects_generated_at():
    r = Renderer(_mk())
    out = r.render("at={{ generated_at }}")
    assert "at=" in out
    assert out != "at="  # generated_at 非空


# ── 3. layout 注入 ──


def test_render_injects_layout():
    r = Renderer(_mk(frontend=True))
    out = r.render("layout={{ layout }}")
    assert out == "layout=fullstack"


# ── 4. layout backend-only ──


def test_render_layout_backend_only():
    r = Renderer(_mk())
    out = r.render("layout={{ layout }}")
    assert out == "layout=backend-only"


# ── 5. StrictUndefined 报错 ──


def test_strict_undefined_raises():
    r = Renderer(_mk())
    with pytest.raises(UndefinedError):
        r.render("{{ nope_xyz }}")


# ── 6. 循环渲染（jinja for 语法）──


def test_render_loop():
    r = Renderer(_mk(frontend=True))
    out = r.render("{% for a in ['x', 'y'] %}{{ a }}{% endfor %}")
    assert out == "xy"


# ── 7. 条件渲染 ──


def test_render_condition():
    r = Renderer(_mk(database=True, orm="tortoise", db_dialect="mysql"))
    out = r.render("{% if options.database %}has_db{% else %}no_db{% endif %}")
    assert out == "has_db"


# ── 8. 条件渲染 False ──


def test_render_condition_false():
    r = Renderer(_mk())
    out = r.render("{% if options.database %}has_db{% else %}no_db{% endif %}")
    assert out == "no_db"


# ── 9. 多变量替换 ──


def test_render_multiple_vars():
    r = Renderer(_mk(project_name="myapp", package_name="myapp", language="en"))
    out = r.render("{{ options.project_name }}-{{ options.package_name }}-{{ options.language }}")
    assert out == "myapp-myapp-en"


# ── 10. trailing newline 保留 ──


def test_render_keeps_trailing_newline():
    r = Renderer(_mk())
    out = r.render("hello\n")
    assert out.endswith("\n")


# ── 11. generated_at 含 ISO 格式 ──


def test_generated_at_iso_format():
    r = Renderer(_mk())
    out = r.render("{{ generated_at }}")
    # ISO 格式至少含 T
    assert "T" in out
