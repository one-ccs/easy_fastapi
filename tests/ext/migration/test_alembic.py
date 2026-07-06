"""alembic 迁移实现测试。"""

import easy_fastapi.ext.migration.alembic_impl as mod
import pytest
from easy_fastapi.ext.migration import alembic_impl


class _FakeConfig:
    def __init__(self):
        self.options = {}

    def set_main_option(self, key, val):
        self.options[key] = val


def _patch_alembic(monkeypatch):
    """用 FakeConfig 替换 Config，并返回 command 子模块供进一步 patch。"""
    monkeypatch.setattr(mod, "Config", _FakeConfig)
    return mod.command


async def test_alembic_unsupported_op_raises():
    with pytest.raises(ValueError, match="不支持的操作"):
        await alembic_impl.run(None, "bogus", orm="sqlalchemy")


async def test_alembic_sync_sqlmodel_creates_tables(tmp_path, monkeypatch):
    """sync + orm=sqlmodel → SQLModel.metadata.create_all → 指定模块的表被建出。

    框架不再持有内置模型，需传入 models 指定项目模型模块路径。
    """
    monkeypatch.chdir(tmp_path)
    # 临时创建一个含 SQLModel 的项目模块
    mod_file = tmp_path / "sm_proj.py"
    mod_file.write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class User(SQLModel, table=True):\n"
        "    __tablename__ = 'alembic_sm_user'\n"
        "    __table_args__ = {'extend_existing': True}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    username: str | None = Field(default=None, index=True)\n",
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))
    db_path = tmp_path / "test.db"
    await alembic_impl.run(None, "sync", orm="sqlmodel", db_url=f"sqlite+aiosqlite:///{db_path}", models=["sm_proj"])
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "alembic_sm_user" in tables
    sys.path.remove(str(tmp_path))
    sys.modules.pop("sm_proj", None)


async def test_alembic_sync_sqlalchemy_creates_tables(tmp_path, monkeypatch):
    """sync + orm=sqlalchemy → 从项目模型模块提取 metadata 后 create_all。

    框架不再持有内置模型，需传入 models 指定项目模型模块路径。
    """
    monkeypatch.chdir(tmp_path)
    mod_file = tmp_path / "sa_proj.py"
    mod_file.write_text(
        "from sqlalchemy import Column, Integer, String\n"
        "from sqlalchemy.orm import DeclarativeBase\n"
        "class Base(DeclarativeBase):\n    pass\n"
        "class User(Base):\n"
        "    __tablename__ = 'alembic_sa_user'\n"
        "    id = Column(Integer, primary_key=True)\n"
        "    username = Column(String(32), unique=True)\n",
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))
    db_path = tmp_path / "test.db"
    await alembic_impl.run(None, "sync", orm="sqlalchemy", db_url=f"sqlite+aiosqlite:///{db_path}", models=["sa_proj"])
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "alembic_sa_user" in tables
    sys.path.remove(str(tmp_path))
    sys.modules.pop("sa_proj", None)


async def test_alembic_init_calls_command(monkeypatch):
    """init 调用 alembic.command.init。"""
    cmd = _patch_alembic(monkeypatch)
    calls = []
    monkeypatch.setattr(cmd, "init", lambda cfg, name: calls.append(name), raising=False)
    await alembic_impl.run(None, "init", orm="sqlalchemy", db_url="sqlite+aiosqlite:///:memory:")
    assert calls == ["alembic"]


async def test_alembic_migrate_calls_revision(monkeypatch):
    cmd = _patch_alembic(monkeypatch)
    calls = []

    def fake_revision(cfg, autogenerate=False, message=""):
        calls.append((autogenerate, message))

    monkeypatch.setattr(cmd, "revision", fake_revision, raising=False)
    await alembic_impl.run(None, "migrate", orm="sqlalchemy", db_url="sqlite+aiosqlite:///:memory:")
    assert calls == [(True, "auto")]


async def test_alembic_upgrade_calls_upgrade(monkeypatch):
    cmd = _patch_alembic(monkeypatch)
    calls = []
    monkeypatch.setattr(cmd, "upgrade", lambda cfg, rev: calls.append(rev), raising=False)
    await alembic_impl.run(None, "upgrade", orm="sqlalchemy", db_url="sqlite+aiosqlite:///:memory:")
    assert calls == ["head"]


async def test_alembic_sync_default_db_url(tmp_path, monkeypatch):
    """sync 不传 db_url → 使用默认 sqlite 路径并真实建表。"""
    monkeypatch.chdir(tmp_path)
    # 临时创建含 SQLModel 的项目模块
    mod_file = tmp_path / "sm_default_proj.py"
    mod_file.write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class User(SQLModel, table=True):\n"
        "    __tablename__ = 'alembic_default_user'\n"
        "    __table_args__ = {'extend_existing': True}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n",
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))
    await alembic_impl.run(None, "sync", orm="sqlmodel", models=["sm_default_proj"])
    assert (tmp_path / "db.sqlite").exists()
    sys.path.remove(str(tmp_path))
    sys.modules.pop("sm_default_proj", None)


async def test_alembic_op_passes_db_url_to_config(monkeypatch):
    """init/migrate/upgrade 时 db_url 写入 Config。"""
    captured = {}

    class Cfg:
        def set_main_option(self, key, val):
            captured[key] = val

    monkeypatch.setattr(mod, "Config", Cfg)
    cmd = mod.command
    monkeypatch.setattr(cmd, "init", lambda cfg, name: None, raising=False)
    await alembic_impl.run(None, "init", orm="sqlalchemy", db_url="postgresql://x")
    assert captured.get("sqlalchemy.url") == "postgresql://x"
    assert captured.get("script_location") == "./alembic"
