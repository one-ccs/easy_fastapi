"""端到端：生成项目 → import app → TestClient 打 OpenAPI + auth 全流程。

生成的项目必须真能跑：装配 EasyFastAPI + 扩展 + auth 路由，注册/登录/me/refresh/logout 全通过。
"""

import importlib
import sys
from importlib.resources import files
from pathlib import Path

import pytest
from easy_fastapi_cli.main import app
from easy_fastapi_cli.scaffold.conflict import check_target
from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate
from easy_fastapi_cli.scaffold.write import write_manifest
from typer.testing import CliRunner


def _create_project_with_cli(tmp_path, name, extra_args=None):
    """用 CLI 生成项目。"""
    target = tmp_path / name
    args = [
        "create",
        str(target),
        "--no-interactive",
        "--project-name",
        name,
        "--package-name",
        name,
    ]
    if extra_args:
        args.extend(extra_args)
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, f"CLI 失败：{result.output}"
    return target


def _create_project_programmatic(tmp_path, name, **kwargs):
    """用程序 API 生成项目（更可控）。"""
    o = apply_defaults(CreateOptions(project_name=name, package_name=name, **kwargs))
    o = validate(o)
    project_dir = tmp_path / name
    check_target(project_dir, in_place=False)
    project_dir.mkdir(parents=True)
    templates_root = Path(str(files("easy_fastapi_cli") / "templates"))
    manifest = build_manifest(o, templates_root=templates_root)
    write_manifest(manifest, o, project_dir, templates_root)
    write_marker(project_dir, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    return project_dir


def _load_app(project_dir: Path):
    """动态 import 生成项目的 app.main:app。需要 CWD 在项目根目录。"""
    import os

    prev_cwd = Path.cwd()
    sys.path.insert(0, str(project_dir))
    os.chdir(project_dir)
    try:
        for mod in list(sys.modules):
            if mod == "app" or mod.startswith("app."):
                del sys.modules[mod]
        mod = importlib.import_module("app.main")
        return mod.app
    finally:
        os.chdir(prev_cwd)
        sys.path.remove(str(project_dir))


# --- 后端 e2e ---


def test_backend_only_app_importable(tmp_path):
    project_dir = _create_project_programmatic(tmp_path, "be_min")
    fastapi_app = _load_app(project_dir)
    assert fastapi_app is not None


def test_backend_only_openapi_reachable(tmp_path):
    from fastapi.testclient import TestClient

    project_dir = _create_project_programmatic(tmp_path, "be_oapi")
    fastapi_app = _load_app(project_dir)
    client = TestClient(fastapi_app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "info" in spec


def test_backend_with_orm_app_importable(tmp_path):
    project_dir = _create_project_programmatic(tmp_path, "be_orm", database=True, orm="tortoise", db_dialect="sqlite")
    fastapi_app = _load_app(project_dir)
    assert fastapi_app is not None


def test_backend_with_orm_auth_app_importable(tmp_path):
    project_dir = _create_project_programmatic(
        tmp_path, "be_auth", database=True, orm="tortoise", db_dialect="sqlite", auth=True
    )
    fastapi_app = _load_app(project_dir)
    assert fastapi_app is not None


def test_backend_auth_has_config_files(tmp_path):
    project_dir = _create_project_programmatic(
        tmp_path, "be_files", database=True, orm="tortoise", db_dialect="sqlite", auth=True
    )
    assert (project_dir / "app" / "routers" / "auth.py").exists()
    assert (project_dir / "app" / "handlers" / "auth_handler.py").exists()
    assert not (project_dir / "app" / "core" / "auth_config.py").exists()


def test_generated_tortoise_project_uses_unified_user_modules_and_auto_model_scan(tmp_path):
    project_dir = _create_project_programmatic(
        tmp_path, "rename_check", database=True, orm="tortoise", db_dialect="sqlite", auth=True
    )
    assert (project_dir / "app" / "routers" / "user.py").exists()
    assert (project_dir / "app" / "services" / "user.py").exists()
    assert not (project_dir / "app" / "routers" / "user_router.py").exists()
    assert not (project_dir / "app" / "services" / "user_service.py").exists()
    assert not (project_dir / "app" / "routers" / "role_router.py").exists()
    assert not (project_dir / "app" / "services" / "role_service.py").exists()

    main_text = (project_dir / "app" / "main.py").read_text(encoding="utf-8")
    assert "TortoiseExtension" not in main_text
    # 扩展实例化在 app/extensions/ 下，app_factory 链式 use
    orm_text = (project_dir / "app" / "extensions" / "orm.py").read_text(encoding="utf-8")
    assert "TortoiseExtension(models=[User, Role])" in orm_text
    factory_text = (project_dir / "app" / "bootstrap" / "app_factory.py").read_text(encoding="utf-8")
    assert ".use(orm)" in factory_text


@pytest.mark.parametrize("orm", ["tortoise", "sqlalchemy", "sqlmodel"])
def test_backend_auth_full_flow(tmp_path, orm):
    """生成项目 auth 全流程：注册→登录→/auth/me→错误密码→刷新→登出→重复注册。

    这是脚手架核心回归：生成的项目必须真能跑，而不只是 importable。
    """
    from fastapi.testclient import TestClient

    project_dir = _create_project_programmatic(
        tmp_path, f"flow_{orm}", database=True, orm=orm, db_dialect="sqlite", auth=True
    )
    # 用文件数据库替代 :memory:（Tortoise 0.25.x :memory: 每连接独立，TestClient 跨连接失败）
    yaml_path = project_dir / "easy-fastapi.yaml"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    db_path = str(project_dir / "test.db").replace("\\", "/")
    yaml_text = yaml_text.replace('database: ":memory:"', f'database: "{db_path}"')
    yaml_path.write_text(yaml_text, encoding="utf-8")
    fastapi_app = _load_app(project_dir)
    with TestClient(fastapi_app) as client:
        # 健康检查
        assert client.get("/health").status_code == 200

        # 注册
        r = client.post("/users/register", json={"username": "alice", "password": "secret123"})
        assert r.status_code == 201
        assert r.json()["username"] == "alice"

        # 登录（OAuth2 表单）
        r = client.post("/auth/login", data={"username": "alice", "password": "secret123"})
        assert r.status_code == 200
        login_data = r.json()["data"]
        token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # 当前用户（框架 /auth/me，不含 hashed_password）
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        me_data = r.json()["data"]
        assert "hashed_password" not in me_data
        assert me_data["username"] == "alice"

        # 错误密码
        assert client.post("/auth/login", data={"username": "alice", "password": "wrong"}).status_code == 401

        # 无 token 访问受保护端点
        assert client.get("/auth/me").status_code == 401

        # 重复注册
        r = client.post("/users/register", json={"username": "alice", "password": "x"})
        assert r.status_code == 409

        # 刷新（body 模式：旧 refresh_token 放 Authorization 请求头）
        r = client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
        assert r.status_code == 200
        assert "access_token" in r.json()["data"]

        # 登出
        assert client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"}).status_code == 204


# --- fullstack e2e ---


def test_fullstack_project_has_frontend_dir(tmp_path):
    project_dir = _create_project_programmatic(
        tmp_path, "fs_fe", frontend=True, database=True, orm="tortoise", db_dialect="sqlite"
    )
    assert (project_dir / "frontend").is_dir()
    assert (project_dir / "package.json").exists()


def test_fullstack_backend_app_importable(tmp_path):
    project_dir = _create_project_programmatic(
        tmp_path, "fs_app", frontend=True, database=True, orm="tortoise", db_dialect="sqlite"
    )
    # fullstack 下 app 在 backend/ 下，CWD 需在项目根目录
    import os

    prev_cwd = Path.cwd()
    sys.path.insert(0, str(project_dir / "backend"))
    os.chdir(project_dir)
    try:
        for mod in list(sys.modules):
            if mod == "app" or mod.startswith("app."):
                del sys.modules[mod]
        mod = importlib.import_module("app.main")
        assert mod.app is not None
    finally:
        os.chdir(prev_cwd)
        sys.path.remove(str(project_dir / "backend"))


# --- CLI e2e ---


def test_cli_create_backend_only(tmp_path):
    target = _create_project_with_cli(tmp_path, "cli_be")
    assert (target / "app" / "main.py").exists()
    assert (target / "pyproject.toml").exists()


def test_cli_create_fullstack(tmp_path):
    target = _create_project_with_cli(
        tmp_path,
        "cli_fs",
        extra_args=["--frontend", "--database", "--orm", "tortoise", "--db-dialect", "sqlite"],
    )
    assert (target / "package.json").exists()
    assert (target / "backend" / "app" / "main.py").exists()


# --- 前端 SDK 链路 e2e ---


def test_fullstack_frontend_sdk_chain_present(tmp_path):
    """验证 fullstack 生成项目含可运行的 pnpm sdk:gen 脚本链路。"""
    import json

    target = _create_project_with_cli(
        tmp_path,
        "fse2e",
        extra_args=["--frontend", "--database", "--orm", "tortoise", "--db-dialect", "sqlite", "--auth"],
    )
    # workspace 根有 sdk:gen 脚本
    root_pkg = json.loads((target / "package.json").read_text(encoding="utf-8"))
    assert "sdk:gen" in root_pkg["scripts"]
    # api-sdk 包有 openapi-ts 配置（packages 而非 shared）
    assert (target / "frontend" / "packages" / "api-sdk" / "openapi-ts.config.ts").exists()
    assert (target / "frontend" / "packages" / "api-sdk" / "package.json").exists()
    # 不再有 admin 应用
    assert not (target / "frontend" / "admin").exists()


def test_fullstack_sdk_gen_points_to_api_sdk(tmp_path):
    """sdk:gen 脚本应 filter 到 api-sdk 包的 gen 命令。"""
    import json

    target = _create_project_with_cli(
        tmp_path,
        "sdk2",
        extra_args=["--frontend", "--database", "--orm", "tortoise", "--db-dialect", "sqlite"],
    )
    root_pkg = json.loads((target / "package.json").read_text(encoding="utf-8"))
    assert "api-sdk" in root_pkg["scripts"]["sdk:gen"]


def test_fullstack_api_sdk_has_hey_api_config(tmp_path):
    """openapi-ts.config.ts 应配置 client-fetch + openapi input。"""
    target = _create_project_with_cli(
        tmp_path,
        "heyapi",
        extra_args=["--frontend", "--database", "--orm", "tortoise", "--db-dialect", "sqlite"],
    )
    cfg = (target / "frontend" / "packages" / "api-sdk" / "openapi-ts.config.ts").read_text(encoding="utf-8")
    assert "@hey-api/client-fetch" in cfg
    assert "openapi.json" in cfg


def test_fullstack_pnpm_install_smoke(tmp_path):
    """真实 pnpm install 冒烟（需 pnpm 可用；CI 可跳过）。无默认 app，仅验证 install。"""
    import subprocess

    target = _create_project_with_cli(
        tmp_path,
        "pnpmproj",
        extra_args=["--frontend", "--database", "--orm", "tortoise", "--db-dialect", "sqlite"],
    )
    try:
        r = subprocess.run(["pnpm", "install"], cwd=str(target), capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        pytest.skip("pnpm 不可用")
    assert r.returncode == 0, r.stderr


# --- static e2e ---


def test_static_project_has_yaml_section_and_extension(tmp_path):
    """static 启用的生成项目含 yaml static section + app_factory 装配 StaticExtension。"""
    project_dir = _create_project_programmatic(tmp_path, "st_ext", static=True)
    yaml_text = (project_dir / "easy-fastapi.yaml").read_text(encoding="utf-8")
    assert "static:" in yaml_text

    factory_text = (project_dir / "app" / "bootstrap" / "app_factory.py").read_text(encoding="utf-8")
    assert ".use(static)" in factory_text
    # static 扩展实例化在 app/extensions/static.py
    static_text = (project_dir / "app" / "extensions" / "static.py").read_text(encoding="utf-8")
    assert "StaticExtension" in static_text
    # static 不再生成 index.html（变更③：纯开关，默认值在 yaml 里）


def test_static_project_no_mount_py(tmp_path):
    """static 启用的项目不再生成 app/core/static_mount.py。"""
    project_dir = _create_project_programmatic(tmp_path, "st_nomount", static=True)
    assert not (project_dir / "app" / "core" / "static_mount.py").exists()
