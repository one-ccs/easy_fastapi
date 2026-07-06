"""create 端到端冒烟测试（marker 自洽 + main 可编译 + 多组合，≥8 用例）。"""

import json

from easy_fastapi.project import read_marker
from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _create(target, **flags):
    args = [
        "create",
        str(target),
        "--no-interactive",
        "--project-name",
        flags.get("name", "e2e"),
        "--package-name",
        flags.get("name", "e2e"),
    ]
    for k, v in flags.items():
        if k == "name":
            continue
        if isinstance(v, bool):
            args.append(f"--{k}" if v else f"--no-{k}")
        else:
            args.extend([f"--{k.replace('_', '-')}", str(v)])
    return runner.invoke(app, args)


# ── 1. tortoise + auth 项目 e2e：marker 自洽 + main 可编译 ──


def test_create_e2e_tortoise_auth(tmp_path):
    target = tmp_path / "e2eproj"
    result = _create(target, name="e2eproj", database=True, orm="tortoise", db_dialect="sqlite", auth=True)
    assert result.exit_code == 0, result.output

    marker = json.loads((target / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert marker["options"]["project_name"] == "e2eproj"
    assert set(marker["registered_extensions"]) >= {"orm.tortoise", "auth"}

    main_py = target / "app" / "main.py"
    compile(main_py.read_text(encoding="utf-8"), str(main_py), "exec")

    # user router 参数名不得遮蔽 user 服务模块名
    user_router = target / "app" / "routers" / "user.py"
    content = user_router.read_text(encoding="utf-8")
    assert "user_data: schemas.UserCreate" in content
    assert "user_data: schemas.UserModify" in content

    # bootstrap 目录结构
    assert (target / "app" / "bootstrap" / "__init__.py").exists()
    assert (target / "app" / "bootstrap" / "app_factory.py").exists()
    assert (target / "app" / "bootstrap" / "routers.py").exists()


# ── 2. read_marker 往返一致 ──


def test_create_e2e_marker_roundtrip(tmp_path):
    target = tmp_path / "rtproj"
    _create(target, name="rtproj", database=True, orm="sqlalchemy", db_dialect="sqlite")
    data = read_marker(target)
    assert data["marker_schema_version"] == 1
    assert data["options"]["orm"] == "sqlalchemy"
    assert "orm.sqlalchemy" in data["registered_extensions"]


# ── 3. backend-only 无 backend/ 前缀 ──


def test_create_e2e_backend_only_no_prefix(tmp_path):
    target = tmp_path / "bopproj"
    _create(target, name="bopproj", database=True, orm="sqlalchemy", db_dialect="sqlite")
    assert (target / "app" / "main.py").exists()
    assert not (target / "backend").exists()


# ── 4. fullstack 项目落 backend/ + frontend/ ──


def test_create_e2e_fullstack(tmp_path):
    target = tmp_path / "fsproj"
    result = _create(
        target,
        name="fsproj",
        frontend=True,
        database=True,
        orm="tortoise",
        db_dialect="mysql",
    )
    assert result.exit_code == 0, result.output
    assert (target / "backend" / "app" / "main.py").exists()
    assert (target / "package.json").exists()
    data = read_marker(target)
    assert data["project_layout"] == "fullstack"


# ── 5. 生成的 pyproject.toml 含真实依赖（fastapi/uvicorn）──


def test_create_e2e_pyproject_dependencies(tmp_path):
    target = tmp_path / "depproj"
    _create(target, name="depproj")
    content = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "fastapi" in content


# ── 6. ORM 项目不再生成 db_config.py ──


def test_create_e2e_orm_db_config(tmp_path):
    target = tmp_path / "ormproj"
    _create(target, name="ormproj", database=True, orm="tortoise", db_dialect="mysql")
    assert not (target / "app" / "core" / "db_config.py").exists()
    assert (target / "app" / "models" / "user.py").exists()
    # repository 模板已删除（框架不再持有 repository）


def test_create_e2e_tortoise_models_are_project_local(tmp_path):
    target = tmp_path / "localmodels"
    _create(target, name="localmodels", database=True, orm="tortoise", db_dialect="sqlite")

    user_model = (target / "app" / "models" / "user.py").read_text(encoding="utf-8")
    role_model = (target / "app" / "models" / "role.py").read_text(encoding="utf-8")

    assert "class User(" in user_model
    assert "class Role(" in role_model
    assert "easy_fastapi.ext.orm.tortoise.user_models" not in user_model
    assert "easy_fastapi.ext.orm.tortoise.role_models" not in role_model


# ── 7. auth 项目含 auth 路由/handler 但不再生成 auth_config ──


def test_create_e2e_auth_files(tmp_path):
    target = tmp_path / "authproj"
    _create(
        target,
        name="authproj",
        database=True,
        orm="tortoise",
        db_dialect="sqlite",
        auth=True,
    )
    assert (target / "app" / "routers" / "auth.py").exists()
    assert (target / "app" / "handlers" / "auth_handler.py").exists()
    assert not (target / "app" / "core" / "auth_config.py").exists()


# ── 8. redis 项目不再生成 redis_config ──


def test_create_e2e_redis_files(tmp_path):
    target = tmp_path / "redisproj"
    _create(target, name="redisproj", redis=True)
    assert not (target / "app" / "core" / "redis_config.py").exists()
    data = read_marker(target)
    assert "redis" in data["registered_extensions"]


# ── 9. migration 项目含迁移配置（tortoise→aerich）──


def test_create_e2e_migration_aerich(tmp_path):
    target = tmp_path / "migproj"
    _create(
        target,
        name="migproj",
        database=True,
        orm="tortoise",
        db_dialect="sqlite",
        migration=True,
    )
    # tortoise migration 用 aerich
    assert (target / "pyproject.toml.aerich").exists()


# ── 10. sqlalchemy migration 用 alembic ──


def test_create_e2e_migration_alembic(tmp_path):
    target = tmp_path / "alemproj"
    _create(
        target,
        name="alemproj",
        database=True,
        orm="sqlalchemy",
        db_dialect="sqlite",
        migration=True,
    )
    assert (target / "alembic" / "env.py").exists()
    assert (target / "alembic" / "script.py.mako").exists()


# ── 11. bootstrap 目录存在（app_factory + routers 拆分）──


def test_create_e2e_bootstrap_dir(tmp_path):
    target = tmp_path / "bsproj"
    _create(target, name="bsproj", database=True, orm="sqlalchemy", db_dialect="sqlite", auth=True)
    assert (target / "app" / "bootstrap" / "__init__.py").exists()
    assert (target / "app" / "bootstrap" / "app_factory.py").exists()
    assert (target / "app" / "bootstrap" / "routers.py").exists()
    # app_factory.py 内容应含 create_app + EasyFastAPI
    app_factory = (target / "app" / "bootstrap" / "app_factory.py").read_text(encoding="utf-8")
    assert "def create_app" in app_factory
    assert "EasyFastAPI" in app_factory
    # routers.py 内容应含 register_routers + register_health
    routers_py = (target / "app" / "bootstrap" / "routers.py").read_text(encoding="utf-8")
    assert "def register_routers" in routers_py
    assert "def register_health" in routers_py
    # main.py 精简后应从 bootstrap 导入 create_app（不再含路由注册）
    main_py = (target / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.bootstrap.app_factory import create_app" in main_py
    assert "create_app()" in main_py
    # app_factory.py 应在 create_app 内调用 register_routers + register_health（在 auth 之后）
    assert "register_routers(app)" in app_factory
    assert "register_health(app)" in app_factory
    # app/__init__.py 不再在模块级注册路由（已移至 create_app）
    init_py = (target / "app" / "__init__.py").read_text(encoding="utf-8")
    assert "register_routers" not in init_py
    assert "register_health" not in init_py


# ── 12. 最小项目（无 auth）bootstrap 仍存在且 routers 为 no-op ──


def test_create_e2e_bootstrap_minimal_no_auth(tmp_path):
    target = tmp_path / "bsmin"
    _create(target, name="bsmin")
    assert (target / "app" / "bootstrap" / "app_factory.py").exists()
    routers_py = (target / "app" / "bootstrap" / "routers.py").read_text(encoding="utf-8")
    # 无 auth 时 register_routers 仍定义，但体内无 include_router
    assert "def register_routers" in routers_py
    assert "include_router" not in routers_py
    assert "def register_health" in routers_py
