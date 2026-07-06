"""efa create 命令测试（向导/参数→校验→manifest→落盘→marker，≥8 用例）。"""

import json

from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


# ── 1. 非交互 create 新目录 ──


def test_create_non_interactive_new_dir(tmp_path):
    target = tmp_path / "myproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "myproj",
            "--package-name",
            "myproj",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (target / "pyproject.toml").exists()
    assert (target / "app" / "main.py").exists()
    assert (target / ".easy-fastapi.json").exists()


# ── 2. 非交互 create in_place ──


def test_create_in_place(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "create",
            ".",
            "--no-interactive",
            "--project-name",
            "inplaceproj",
            "--package-name",
            "inplaceproj",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / ".easy-fastapi.json").exists()


# ── 3. 带 ORM + auth 的 marker ──


def test_create_with_orm(tmp_path):
    target = tmp_path / "dbproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "dbproj",
            "--package-name",
            "dbproj",
            "--database",
            "--orm",
            "tortoise",
            "--db-dialect",
            "mysql",
            "--migration",
            "--auth",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads((target / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert "orm.tortoise" in data["registered_extensions"]
    assert "auth" in data["registered_extensions"]


# ── 4. 非空目标目录报错 ──


def test_create_non_empty_target_raises(tmp_path):
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "existing.txt").write_text("x")
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "x",
            "--package-name",
            "x",
        ],
    )
    assert result.exit_code != 0


# ── 5. 校验失败（database=True 无 orm）报错 ──


def test_create_validation_error(tmp_path):
    target = tmp_path / "badproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "x",
            "--package-name",
            "x",
            "--database",  # 但不给 orm → 铁律 B 报错
        ],
    )
    assert result.exit_code != 0


# ── 6. sqlalchemy ORM ──


def test_create_sqlalchemy(tmp_path):
    target = tmp_path / "saproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "saproj",
            "--package-name",
            "saproj",
            "--database",
            "--orm",
            "sqlalchemy",
            "--db-dialect",
            "sqlite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert not (target / "app" / "core" / "db_config.py").exists()


# ── 7. redis 启用 ──


def test_create_redis(tmp_path):
    target = tmp_path / "redisproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "redisproj",
            "--package-name",
            "redisproj",
            "--redis",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads((target / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert "redis" in data["registered_extensions"]


# ── 8. 生成的 pyproject.toml 含项目名 ──


def test_create_pyproject_contains_name(tmp_path):
    target = tmp_path / "nameproj"
    runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "nameproj",
            "--package-name",
            "nameproj",
        ],
    )
    content = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "nameproj" in content


# ── 9. 生成的 main.py 可编译 ──


def test_create_main_compilable(tmp_path):
    target = tmp_path / "compileproj"
    runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "compileproj",
            "--package-name",
            "compileproj",
        ],
    )
    main_py = target / "app" / "main.py"
    compile(main_py.read_text(encoding="utf-8"), str(main_py), "exec")


# ── 10. fullstack 模式落盘 backend/ + frontend/ ──


def test_create_fullstack(tmp_path):
    target = tmp_path / "fsproj"
    result = runner.invoke(
        app,
        [
            "create",
            str(target),
            "--no-interactive",
            "--project-name",
            "fsproj",
            "--package-name",
            "fsproj",
            "--frontend",
            "--database",
            "--orm",
            "tortoise",
            "--db-dialect",
            "mysql",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (target / "backend" / "app" / "main.py").exists()
    assert (target / "frontend").exists()


# ── 11. 未传 --project-name 时从目标目录名推导 ──


def test_create_derives_project_name_from_target_dir(tmp_path):
    """efa create <dir> 不传 --project-name，应从目录名推导，不崩溃。"""
    target = tmp_path / "derivedproj"
    result = runner.invoke(
        app,
        ["create", str(target), "--no-interactive"],
    )
    assert result.exit_code == 0, result.output
    content = (target / "pyproject.toml").read_text(encoding="utf-8")
    assert "derivedproj" in content


# ── 12. in_place 未传 --project-name 时从 cwd 名推导 ──


def test_create_in_place_derives_project_name_from_cwd(tmp_path, monkeypatch):
    """efa create . 不传 --project-name，应从 cwd 名推导。"""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["create", ".", "--no-interactive"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "pyproject.toml").exists()


# ── 13. 默认进入交互向导（interactive 默认 True）──


def test_create_defaults_to_interactive(tmp_path, monkeypatch):
    """efa create <dir> 不带 --no-interactive 应进入交互向导，
    且把目标目录名作为项目名默认值传给向导。"""
    captured = {"called": False, "default_project_name": None}

    def fake_run_wizard(*, default_project_name=None):
        captured["called"] = True
        captured["default_project_name"] = default_project_name
        from easy_fastapi_cli.scaffold.options import CreateOptions

        name = default_project_name or "wizproj"
        return CreateOptions(project_name=name, package_name=name)

    def fake_confirm_options(options):
        return True  # 确认

    import easy_fastapi_cli.commands.create as create_mod

    monkeypatch.setattr(create_mod, "run_wizard", fake_run_wizard)
    monkeypatch.setattr(create_mod, "confirm_options", fake_confirm_options)

    target = tmp_path / "wizproj"
    result = runner.invoke(app, ["create", str(target)])
    assert result.exit_code == 0, result.output
    assert captured["called"], "应调用 run_wizard（交互模式）"
    assert captured["default_project_name"] == "wizproj", "应把目标目录名作为默认项目名传给向导"
