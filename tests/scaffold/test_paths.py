"""目录模式推导测试（fullstack/backend-only，≥8 用例）。"""

from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.paths import project_layout


def _mk(**kw):
    base = {"project_name": "p", "package_name": "p"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. frontend=True → fullstack ──


def test_layout_fullstack():
    assert project_layout(_mk(frontend=True)) == "fullstack"


# ── 2. frontend=False → backend-only ──


def test_layout_backend_only():
    assert project_layout(_mk(frontend=False)) == "backend-only"


# ── 3. 默认（frontend=False）→ backend-only ──


def test_layout_default_is_backend_only():
    assert project_layout(_mk()) == "backend-only"


# ── 4. 有数据库但无前端 → backend-only ──


def test_layout_backend_only_with_db():
    assert project_layout(_mk(frontend=False, database=True, orm="tortoise", db_dialect="mysql")) == "backend-only"


# ── 5. 全功能 → fullstack ──


def test_layout_fullstack_with_everything():
    o = _mk(
        frontend=True,
        database=True,
        orm="sqlalchemy",
        db_dialect="postgres",
        auth=True,
        redis=True,
    )
    assert project_layout(o) == "fullstack"


# ── 6. 只设 frontend=True，其他全默认 → fullstack ──


def test_layout_frontend_true_minimal():
    assert project_layout(_mk(frontend=True)) == "fullstack"


# ── 7. 返回值类型是 str ──


def test_layout_returns_str():
    result = project_layout(_mk())
    assert isinstance(result, str)


# ── 8. 返回值只能是两种之一 ──


def test_layout_only_two_possible_values():
    for frontend in (True, False):
        result = project_layout(_mk(frontend=frontend))
        assert result in ("fullstack", "backend-only")
