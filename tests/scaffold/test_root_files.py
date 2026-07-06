"""根级文件 + README + 快速指南 + 前端遍历产物测试。"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _fullstack(**kw):
    defaults = {"project_name": "demo", "package_name": "demo", "frontend": True}
    defaults.update(kw)
    return build_manifest(CreateOptions(**defaults))


def _backend_only(**kw):
    defaults = {"project_name": "demo", "package_name": "demo"}
    defaults.update(kw)
    return build_manifest(CreateOptions(**defaults))


# ── 根级文件 ──


def test_fullstack_root_has_pyproject_workspace():
    m = _fullstack()
    dests = {f.dest for f in m.fragments}
    assert "pyproject.toml" in dests
    assert "package.json" in dests
    assert "pnpm-workspace.yaml" in dests
    assert ".gitignore" in dests


def test_backend_only_root_has_gitignore_and_readme():
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert ".gitignore" in dests
    assert "README.md" in dests


def test_backend_only_no_workspace_files():
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    assert "package.json" not in dests
    assert "pnpm-workspace.yaml" not in dests


# ── README ──


def test_fullstack_has_two_readmes():
    m = _fullstack()
    dests = {f.dest for f in m.fragments}
    assert "README.md" in dests  # 根
    assert "backend/README.md" in dests  # 后端
    # api-sdk README 在 frontend/packages/api-sdk/（base 子树）
    assert "frontend/packages/api-sdk/README.md" in dests
    # 不应有 admin README
    assert "frontend/admin/README.md" not in dests
    assert "frontend/shared/api-sdk/README.md" not in dests


def test_backend_only_has_one_readme():
    m = _backend_only()
    dests = {f.dest for f in m.fragments}
    readmes = [d for d in dests if d.endswith("README.md")]
    assert len(readmes) == 1
    assert "README.md" in readmes


# ── 快速指南 ──


def test_post_messages_fullstack_zh():
    m = _fullstack(database=True, orm="tortoise", db_dialect="mysql", auth=True)
    joined = " ".join(m.post_messages)
    assert "uv sync" in joined
    assert "pnpm install" in joined
    assert "sdk:gen" in joined
    assert "efa db sync" in joined
    assert "认证" in joined or "管理员" in joined


def test_post_messages_fullstack_en():
    m = _fullstack(language="en", database=True, orm="tortoise", db_dialect="mysql", auth=True)
    joined = " ".join(m.post_messages)
    assert "uv sync" in joined
    assert "pnpm install" in joined
    assert "sdk:gen" in joined
    assert "Auth" in joined or "admin" in joined


def test_post_messages_backend_only():
    m = _backend_only(database=True, orm="tortoise", db_dialect="mysql")
    joined = " ".join(m.post_messages)
    assert "uv sync" in joined
    assert "pnpm" not in joined


def test_post_messages_minimal():
    m = _backend_only()
    joined = " ".join(m.post_messages)
    assert "uv sync" in joined
    assert "pnpm" not in joined
    assert "db sync" not in joined


# ── 前端遍历产物 ──


def test_frontend_traversal_has_api_sdk():
    m = _fullstack()
    dests = {f.dest for f in m.fragments}
    assert "frontend/packages/api-sdk/package.json" in dests
    assert "frontend/packages/api-sdk/openapi-ts.config.ts" in dests
    assert "frontend/packages/api-sdk/src/index.ts" in dests
    assert "frontend/packages/api-sdk/README.md" in dests


def test_frontend_traversal_has_apps_gitkeep():
    m = _fullstack()
    dests = {f.dest for f in m.fragments}
    assert "frontend/apps/.gitkeep" in dests


def test_no_admin_or_shared_in_dest():
    """确认 admin/shared 旧结构不再出现。"""
    m = _fullstack()
    for f in m.fragments:
        assert "frontend/admin" not in f.dest, f"admin 路径残留：{f.dest}"
        assert "frontend/shared" not in f.dest, f"shared 路径残留：{f.dest}"
