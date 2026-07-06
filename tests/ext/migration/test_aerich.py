"""aerich 迁移实现测试。"""

import pytest
from easy_fastapi.ext.migration import aerich_impl


async def test_aerich_unsupported_op_raises():
    with pytest.raises(ValueError, match="不支持的操作"):
        await aerich_impl.run(None, "bogus", db_url="sqlite://db.sqlite", models=[])


async def test_aerich_init_non_idempotent(tmp_path, monkeypatch):
    """已存在 [tool.aerich] 段 → init 报 RuntimeError。"""
    (tmp_path / "pyproject.toml").write_text('[tool.aerich]\ntortoisetest = "x"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="已初始化"):
        await aerich_impl.run(None, "init", db_url="sqlite://db.sqlite", models=[])


async def test_aerich_init_calls_command_init(tmp_path, monkeypatch):
    """init 正常调用 aerich.Command().init()。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    calls = []

    class FakeCommand:
        def __init__(self, tortoise_config, app="models", location="./migrations"):
            calls.append(("init_config", tortoise_config))

        async def init(self):
            calls.append(("init",))

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.Command", FakeCommand)
    await aerich_impl.run(None, "init", db_url="sqlite://my.db", models=["app.models"])
    assert ("init",) in calls


async def test_aerich_migrate_calls_command_migrate(tmp_path, monkeypatch):
    calls = []

    class FakeCommand:
        def __init__(self, **kw):
            pass

        async def init(self):
            calls.append(("init",))

        async def migrate(self):
            calls.append(("migrate",))

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.Command", FakeCommand)
    await aerich_impl.run(None, "migrate", db_url="sqlite://db.sqlite", models=[])
    assert ("migrate",) in calls
    assert ("init",) in calls  # migrate 前必须先 init Migrate 类状态


async def test_aerich_upgrade_calls_command_upgrade(tmp_path, monkeypatch):
    calls = []

    class FakeCommand:
        def __init__(self, **kw):
            pass

        async def init(self):
            calls.append(("init",))

        async def upgrade(self):
            calls.append(("upgrade",))

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.Command", FakeCommand)
    await aerich_impl.run(None, "upgrade", db_url="sqlite://db.sqlite", models=[])
    assert ("upgrade",) in calls
    assert ("init",) in calls  # upgrade 前必须先 init Migrate 类状态


async def test_aerich_is_initialized_true(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.aerich]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert aerich_impl._is_initialized() is True


async def test_aerich_is_initialized_false_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert aerich_impl._is_initialized() is False


async def test_aerich_is_initialized_false_no_section(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[tool.other]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert aerich_impl._is_initialized() is False


async def test_aerich_init_config_contains_models(tmp_path, monkeypatch):
    """验证 aerich Command 构造接收 models 列表。"""
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    configs = []

    class FakeCommand:
        def __init__(self, tortoise_config, app="models", location="./migrations"):
            configs.append(tortoise_config)

        async def init(self):
            pass

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.Command", FakeCommand)
    await aerich_impl.run(None, "init", db_url="sqlite://db.sqlite", models=["app.models", "app.extra"])
    cfg = configs[0]
    assert "app.models" in cfg["apps"]["models"]["models"]
    assert "app.extra" in cfg["apps"]["models"]["models"]
