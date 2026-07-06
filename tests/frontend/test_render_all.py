"""前端模板渲染快照测试（全套渲染无 StrictUndefined 报错）。

遍历 templates/frontend/{base,pnpm} 两子树所有 .j2，确保渲染通过。
"""

from pathlib import Path

from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.renderer import Renderer


def _fe_dir():
    from importlib.resources import files

    return Path(str(files("easy_fastapi_cli") / "templates" / "frontend"))


def _all_j2():
    """遍历 base + pnpm 两子树所有 .j2。"""
    out = []
    for sub in ("base", "pnpm"):
        out.extend(sorted((_fe_dir() / sub).rglob("*.j2")))
    return out


def _render_all(language, **kw):
    defaults = {"project_name": "demo", "package_name": "demo", "frontend": True, "language": language}
    defaults.update(kw)
    o = CreateOptions(**defaults)
    r = Renderer(o)
    failures = []
    for tpl in _all_j2():
        try:
            r.render(tpl.read_text(encoding="utf-8"))
        except Exception as e:
            failures.append(f"{tpl.name}: {e}")
    return failures


def test_all_frontend_templates_render_zh():
    failures = _render_all("zh")
    assert not failures, "渲染失败(zh)：\n" + "\n".join(failures)


def test_all_frontend_templates_render_en():
    failures = _render_all("en")
    assert not failures, "渲染失败(en)：\n" + "\n".join(failures)


def test_frontend_template_count():
    """base + pnpm 两子树 .j2 总数。"""
    assert len(_all_j2()) == 5


def test_render_zh_with_orm():
    failures = _render_all("zh", database=True, orm="tortoise", db_dialect="sqlite")
    assert not failures, "渲染失败(zh+orm)：\n" + "\n".join(failures)


def test_render_en_with_orm():
    failures = _render_all("en", database=True, orm="tortoise", db_dialect="sqlite")
    assert not failures, "渲染失败(en+orm)：\n" + "\n".join(failures)


def test_render_zh_with_auth():
    failures = _render_all("zh", database=True, orm="tortoise", db_dialect="sqlite", auth=True)
    assert not failures, "渲染失败(zh+auth)：\n" + "\n".join(failures)


def test_render_en_with_auth():
    failures = _render_all("en", database=True, orm="tortoise", db_dialect="sqlite", auth=True)
    assert not failures, "渲染失败(en+auth)：\n" + "\n".join(failures)


def test_render_custom_project_name():
    failures = _render_all("zh", project_name="myapp", package_name="myapp")
    assert not failures, "渲染失败(custom name)：\n" + "\n".join(failures)


def test_render_full_options():
    failures = _render_all(
        "en",
        project_name="fullapp",
        package_name="fullapp",
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        auth=True,
        migration=True,
        redis=True,
    )
    assert not failures, "渲染失败(full options)：\n" + "\n".join(failures)
