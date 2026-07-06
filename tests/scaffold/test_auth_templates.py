"""auth 模板测试。"""

from pathlib import Path

from jinja2 import Environment, StrictUndefined

_TEMPLATES = Path("packages/easy_fastapi_cli/src/easy_fastapi_cli/templates")
_ENV = Environment(undefined=StrictUndefined, keep_trailing_newline=True)


def _render(rel: str) -> str:
    return _ENV.from_string((_TEMPLATES / rel).read_text(encoding="utf-8")).render()


def test_auth_router_template_has_no_me_endpoint():
    """模板 auth router 不再生成 /me（框架已提供 /auth/me）。"""
    rendered = _render("backend/base/backend/app/routers/auth.py.j2")
    assert '"/me"' not in rendered
    assert "'/me'" not in rendered


def test_auth_router_template_keeps_register():
    """模板保留 /register。"""
    rendered = _render("backend/base/backend/app/routers/auth.py.j2")
    assert "/register" in rendered
