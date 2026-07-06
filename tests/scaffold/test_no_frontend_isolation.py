"""backend-only 模式零前端隔离测试（≥8 用例）。"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _backend_only(**kw):
    defaults = {"project_name": "demo", "package_name": "demo"}
    defaults.update(kw)
    return build_manifest(CreateOptions(**defaults))


def test_backend_only_has_no_frontend_fragments():
    m = _backend_only()
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)


def test_backend_only_has_no_admin_fragments():
    m = _backend_only()
    assert not any("frontend/admin" in f.dest for f in m.fragments)


def test_backend_only_has_no_pnpm_messages():
    m = _backend_only()
    assert not any("pnpm" in msg for msg in m.post_messages)


def test_backend_only_has_no_frontend_deps():
    m = _backend_only()
    joined = " ".join(m.dependencies + m.dev_dependencies).lower()
    for fe in ("vue", "vite", "pinia", "element-plus", "tailwindcss", "vue-router"):
        assert fe not in joined, f"backend-only 不应含前端依赖 {fe}"


def test_backend_only_with_orm_no_frontend():
    m = _backend_only(database=True, orm="tortoise", db_dialect="sqlite")
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)


def test_backend_only_with_auth_no_frontend():
    m = _backend_only(database=True, orm="tortoise", db_dialect="sqlite", auth=True)
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)


def test_backend_only_with_redis_no_frontend():
    m = _backend_only(redis=True)
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)


def test_backend_only_with_migration_no_frontend():
    m = _backend_only(database=True, orm="tortoise", db_dialect="sqlite", migration=True)
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)


def test_frontend_true_has_frontend_fragments():
    o = CreateOptions(project_name="demo", package_name="demo", frontend=True)
    m = build_manifest(o)
    assert any(f.dest.startswith("frontend/") for f in m.fragments)


# ── E9: backend-only 白名单断言（spec 6.5）──


def test_backend_only_includes_log_config():
    """backend-only manifest 含 log_config.json。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert "log_config.json" in dests


def test_backend_only_includes_logs_dir():
    """backend-only manifest 含 logs/ 目录。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert any(d.startswith("logs/") for d in dests), dests


def test_backend_only_includes_test_dir():
    """backend-only manifest 含 test/ 目录。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert any("test/" in d for d in dests), dests


def test_backend_only_includes_main_py():
    """backend-only manifest 含 app/main.py。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert "app/main.py" in dests


def test_backend_only_includes_gitignore():
    """backend-only manifest 含 .gitignore。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert ".gitignore" in dests


def test_backend_only_includes_handlers_dir():
    """backend-only manifest 含 app/handlers/ 目录。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert any("app/handlers/" in d for d in dests), dests


def test_backend_only_includes_utils_dir():
    """backend-only manifest 含 app/utils/ 目录。"""
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert any("app/utils/" in d for d in dests), dests


def test_backend_only_log_config_is_copy_not_template():
    """log_config.json 为原样拷贝（is_template=False）。"""
    m = _backend_only()
    for f in m.fragments:
        if f.dest == "log_config.json":
            assert f.is_template is False
            return
    raise AssertionError("未找到 log_config.json fragment")
