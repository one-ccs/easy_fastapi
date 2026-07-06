"""Fragment + Manifest 数据模型测试（≥8 用例）。"""

import pytest
from easy_fastapi_cli.scaffold.manifest import Fragment, Manifest
from pydantic import ValidationError

# ── 1. Fragment 默认值 ──


def test_fragment_defaults():
    f = Fragment(src="a", dest="b")
    assert f.src == "a"
    assert f.dest == "b"
    assert f.is_template is True


# ── 2. Fragment copy (is_template=False) ──


def test_fragment_copy_not_template():
    f = Fragment(src="a", dest="b", is_template=False)
    assert f.is_template is False


# ── 3. Fragment 字段集合 ──


def test_fragment_fields_are_src_dest_is_template():
    """Fragment 字段仅 src/dest/is_template（when 死字段已删除）。"""
    fields = set(Fragment.model_fields.keys())
    assert fields == {"src", "dest", "is_template"}


# ── 4. Manifest 默认空列表 ──


def test_manifest_defaults():
    m = Manifest()
    assert m.fragments == []
    assert m.dependencies == []
    assert m.dev_dependencies == []
    assert m.post_messages == []


# ── 5. Manifest 构造带内容 ──


def test_manifest_build():
    m = Manifest(
        fragments=[Fragment(src="x", dest="y")],
        dependencies=["fastapi"],
        dev_dependencies=["pytest"],
        post_messages=["下一步：uv sync"],
    )
    assert len(m.fragments) == 1
    assert m.dependencies == ["fastapi"]
    assert m.dev_dependencies == ["pytest"]
    assert m.post_messages == ["下一步：uv sync"]


# ── 6. Fragment src/dest 必填 ──


def test_fragment_src_required():
    with pytest.raises(ValidationError):
        Fragment(dest="b")


def test_fragment_dest_required():
    with pytest.raises(ValidationError):
        Fragment(src="a")


# ── 7. Manifest 可追加 fragment ──


def test_manifest_append_fragment():
    m = Manifest()
    m.fragments.append(Fragment(src="a", dest="b"))
    assert len(m.fragments) == 1
    assert m.fragments[0].src == "a"


# ── 8. Manifest 多 fragment ──


def test_manifest_multiple_fragments():
    m = Manifest(
        fragments=[
            Fragment(src="a", dest="b", is_template=True),
            Fragment(src="c", dest="d", is_template=False),
            Fragment(src="e", dest="f"),
        ]
    )
    assert len(m.fragments) == 3
    assert m.fragments[1].is_template is False


# ── 9. Fragment extra='forbid' 不存在——无显式 forbid，测试 model_dump ──


def test_fragment_model_dump():
    f = Fragment(src="a", dest="b")
    d = f.model_dump()
    assert d == {"src": "a", "dest": "b", "is_template": True}


# ── 10. Manifest model_dump ──


def test_manifest_model_dump():
    m = Manifest(dependencies=["fastapi"], post_messages=["msg"])
    d = m.model_dump()
    assert d["dependencies"] == ["fastapi"]
    assert d["post_messages"] == ["msg"]
    assert d["fragments"] == []


# ── 11. 不变量：package_name/project_name 不参与任何 Fragment dest 路径命名 ──
# 见 docs/post-1.0/efa-create-fixes.md「不变量」章节。包名只作配置字段值，
# 不作文件/目录路径名。覆盖多组合（含特殊字符包名）以拦截回归。


@pytest.mark.parametrize(
    "kwargs",
    [
        {"project_name": "demo", "package_name": "demo"},
        {"project_name": "demo", "package_name": "my_pkg"},
        {"project_name": "Demo App", "package_name": "demo_app"},
        {
            "project_name": "demo",
            "package_name": "demo",
            "database": True,
            "orm": "tortoise",
            "db_dialect": "mysql",
            "auth": True,
            "redis": True,
        },
        {
            "project_name": "demo",
            "package_name": "demo",
            "frontend": True,
        },
        {
            "project_name": "demo",
            "package_name": "Weird.Pkg-Name",
            "database": True,
            "orm": "sqlalchemy",
            "db_dialect": "postgres",
        },
        {
            "project_name": "demo",
            "package_name": "demo",
            "static": True,
        },
    ],
    ids=["minimal", "pkg-differs", "slug-names", "backend-full", "fullstack", "weird-pkg", "static"],
)
def test_fragment_dest_never_contains_package_or_project_name(kwargs):
    """所有 Fragment 的 dest 路径不得含 package_name / project_name 子串。

    防回归：若未来有人误用 options.package_name 拼路径（如 dest=f"{pkg}/main.py"），
    此测试会失败。固定路径片段（app/、backend/、frontend/ 等）不受影响。
    """
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(**kwargs)
    m = build_manifest(o)
    pkg = o.package_name
    proj = o.project_name
    for f in m.fragments:
        # 归一化比较：dest 用正斜杠，包名/项目名可能含空格/大小写
        dest_norm = f.dest.replace("\\", "/").lower()
        assert pkg.lower() not in dest_norm, (
            f"Fragment dest {f.dest!r} 不应包含 package_name {pkg!r}（包名不得作路径名）"
        )
        assert proj.lower() not in dest_norm, (
            f"Fragment dest {f.dest!r} 不应包含 project_name {proj!r}（项目名不得作路径名）"
        )


# ── 12. E8: auth manifest 含 schemas/services/routers dest（spec 6.4）──


def _auth_manifest():
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(
        project_name="demo",
        package_name="demo",
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        auth=True,
    )
    return build_manifest(o)


def test_auth_manifest_has_schemas_dest():
    """auth=True 的 manifest 含 app/schemas/ dest。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert any("app/schemas/" in d for d in dests), dests


def test_auth_manifest_has_services_dest():
    """auth=True 的 manifest 含 app/services/ dest。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert any("app/services/" in d for d in dests), dests


def test_auth_manifest_has_routers_dest():
    """auth=True 的 manifest 含 app/routers/ dest。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert any("app/routers/" in d for d in dests), dests


def test_auth_manifest_has_auth_router_dest():
    """auth=True 的 manifest 含 app/routers/auth.py。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert "app/routers/auth.py" in dests


def test_auth_manifest_has_user_role_schemas():
    """auth=True 的 manifest 含 user.py / role.py schema。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert "app/schemas/user.py" in dests
    assert "app/schemas/role.py" in dests


def test_auth_manifest_has_user_role_services():
    """auth=True 的 manifest 含 user.py / role.py service。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert "app/services/user.py" in dests
    assert "app/services/role.py" in dests


def test_auth_manifest_has_page_query_schema():
    """auth=True 的 manifest 含 page_query schema（分页查询）。"""
    dests = {f.dest for f in _auth_manifest().fragments}
    assert "app/schemas/page_query.py" in dests


def test_auth_manifest_absent_when_auth_false():
    """auth=False 时不应有 schemas/services/routers 业务片段。"""
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(project_name="demo", package_name="demo")
    m = build_manifest(o)
    dests = {f.dest for f in m.fragments}
    assert not any("app/schemas/" in d for d in dests)
    assert not any("app/services/" in d for d in dests)


# ── 13. E8: common manifest 含 log_config.json / logs/ dest ──


def _common_manifest():
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(project_name="demo", package_name="demo")
    return build_manifest(o)


def test_common_manifest_has_log_config_json():
    """common manifest 含 log_config.json dest。"""
    dests = {f.dest for f in _common_manifest().fragments}
    assert "log_config.json" in dests


def test_common_manifest_has_logs_dir():
    """common manifest 含 logs/ 目录 dest。"""
    dests = {f.dest for f in _common_manifest().fragments}
    assert any(d.startswith("logs/") for d in dests), dests


def test_common_manifest_has_log_config_as_copy():
    """log_config.json 为原样拷贝（is_template=False）。"""
    for f in _common_manifest().fragments:
        if f.dest == "log_config.json":
            assert f.is_template is False
            return
    pytest.fail("未找到 log_config.json fragment")


# ── 14. E8: test manifest 含 test/ dest ──


def _test_manifest():
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(project_name="demo", package_name="demo")
    return build_manifest(o)


def test_test_manifest_has_test_dir():
    """test manifest 含 test/ 目录 dest。"""
    dests = {f.dest for f in _test_manifest().fragments}
    assert any("test/" in d for d in dests), dests


def _test_manifest_with_auth():
    """带 auth=True 的 manifest（用于 auth 专属文件断言）。"""
    from easy_fastapi_cli.scaffold.manifest import build_manifest
    from easy_fastapi_cli.scaffold.options import CreateOptions

    o = CreateOptions(project_name="demo", package_name="demo", auth=True)
    return build_manifest(o)


def test_test_manifest_has_conftest():
    """auth 项目 manifest 含 test/conftest.py。"""
    dests = {f.dest for f in _test_manifest_with_auth().fragments}
    assert "test/conftest.py" in dests


def test_test_manifest_no_conftest_without_auth():
    """非 auth 项目不生成 test/conftest.py（避免依赖不存在的 /auth/login）。"""
    dests = {f.dest for f in _test_manifest().fragments}
    assert "test/conftest.py" not in dests


def test_test_manifest_has_auth_router_test():
    """auth 项目 manifest 含 test/test_auth_router.py。"""
    dests = {f.dest for f in _test_manifest_with_auth().fragments}
    assert "test/test_auth_router.py" in dests


def test_test_manifest_no_auth_router_test_without_auth():
    """非 auth 项目不生成 test/test_auth_router.py。"""
    dests = {f.dest for f in _test_manifest().fragments}
    assert "test/test_auth_router.py" not in dests


def test_test_manifest_has_init_py():
    """test manifest 含 test/__init__.py。"""
    dests = {f.dest for f in _test_manifest().fragments}
    assert "test/__init__.py" in dests


def test_test_manifest_adds_pytest_dev_dependency():
    """test manifest 总是添加 pytest/httpx 到 dev_dependencies。"""
    m = _test_manifest()
    assert "pytest" in m.dev_dependencies
    assert "httpx" in m.dev_dependencies
