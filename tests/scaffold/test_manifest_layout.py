"""build_manifest 双模式落盘路径测试（≥8 用例）。"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions

# ── 1. fullstack 后端片段加 backend/ 前缀 ──


def test_backend_prefix_in_fullstack():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql"
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert any(d.startswith("backend/") for d in dests)
    assert any(d.startswith("backend/app/main.py") for d in dests)


# ── 2. fullstack 不出现顶层 app/main.py ──


def test_no_toplevel_app_main_in_fullstack():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql"
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert "app/main.py" not in dests


# ── 3. backend-only 保留顶层 app/main.py ──


def test_no_backend_prefix_in_backend_only():
    o = CreateOptions(project_name="d", package_name="d", database=True, orm="tortoise", db_dialect="mysql")
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert "app/main.py" in dests
    assert not any(d.startswith("backend/") for d in dests)


# ── 4. fullstack 含 frontend/ 片段 ──


def test_fullstack_includes_frontend_fragment():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql"
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert any(d.startswith("frontend/") for d in dests)


# ── 5. backend-only 无 frontend/ 片段 ──


def test_backend_only_no_frontend_fragment():
    o = CreateOptions(project_name="d", package_name="d")
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert not any(d.startswith("frontend/") for d in dests)


# ── 6. fullstack 所有后端 dest 都带 backend/ 前缀（根级文件除外）──


# 根级文件（workspace 三件套 + README + .gitignore）落项目根，不带 backend/ 前缀
_ROOT_FILES = {
    "pyproject.toml",
    "package.json",
    "pnpm-workspace.yaml",
    "README.md",
    ".gitignore",
    ".npmrc",
}


def test_fullstack_all_backend_dests_prefixed():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql"
    )
    m = build_manifest(o)
    # 非 frontend/ 的 dest 中，排除根级文件后都应以 backend/ 开头
    backend_dests = [f.dest for f in m.fragments if not f.dest.startswith("frontend/") and f.dest not in _ROOT_FILES]
    for d in backend_dests:
        assert d.startswith("backend/"), f"dest 未加 backend/ 前缀：{d}"


# ── 6b. fullstack 根级文件不带 backend/ 前缀 ──


def test_fullstack_root_files_not_prefixed():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql"
    )
    m = build_manifest(o)
    dests = {f.dest for f in m.fragments}
    # 根级文件存在且不带 backend/ 前缀（pyproject.toml/README.md 同时有 backend/ 版本，属正常）
    for root_file in ("pyproject.toml", "package.json", "pnpm-workspace.yaml", "README.md", ".gitignore"):
        assert root_file in dests, f"根级文件缺失：{root_file}"


# ── 7. fullstack backend/app/models/user.py 存在 ──


def test_fullstack_user_model_path():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="sqlalchemy", db_dialect="sqlite"
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert "backend/app/models/user.py" in dests


# ── 8. backend-only app/models/user.py 存在 ──


def test_backend_only_user_model_path():
    o = CreateOptions(project_name="d", package_name="d", database=True, orm="sqlalchemy", db_dialect="sqlite")
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert "app/models/user.py" in dests
    assert "backend/app/models/user.py" not in dests


# ── 9. fullstack auth 路由在 backend/ 下 ──


def test_fullstack_auth_route_path():
    o = CreateOptions(
        project_name="d", package_name="d", frontend=True, database=True, orm="tortoise", db_dialect="mysql", auth=True
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    assert "backend/app/routers/auth.py" in dests


# ── 10. fullstack static 仅写入 yaml 配置，不生成静态文件 ──


def test_fullstack_static_path():
    o = CreateOptions(
        project_name="d",
        package_name="d",
        frontend=True,
        database=False,
        orm=None,
        static=True,
    )
    m = build_manifest(o)
    dests = [f.dest for f in m.fragments]
    # static 走 StaticExtension（yaml 配置），不再生成 mount.py / index.html
    assert "backend/static/index.html" not in dests
    assert not any(d.startswith("backend/app/core/static_mount.py") for d in dests)
    # static 配置由 easy-fastapi.yaml.j2 渲染
    assert any(f.src.endswith("easy-fastapi.yaml.j2") for f in m.fragments)
