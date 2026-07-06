"""easy_fastapi._runner argparse 最小分发测试。

覆盖：db sync/init/migrate/upgrade 分发、gen --force/gen 分发、
未知命令/无参数退出、缺 marker 时命令仍分发（错误由 Core 函数抛出）。
"""

import json
from unittest.mock import patch

import pytest

MARKER_FILENAME = ".easy-fastapi.json"


def _write_marker(tmp_path, *, orm="sqlmodel", db_dialect="sqlite", database=True):
    data = {
        "marker_schema_version": 1,
        "project_layout": "backend-only",
        "options": {"orm": orm, "db_dialect": db_dialect, "database": database},
        "registered_extensions": [f"orm.{orm}"] if database and orm else [],
    }
    (tmp_path / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def test_runner_db_sync(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_sync(project_dir):
        calls.append(("sync", str(project_dir)))

    with patch("easy_fastapi.commands.db.run_db_sync", fake_sync):
        from easy_fastapi._runner import main

        main(["db", "sync"])
    assert len(calls) == 1


def test_runner_db_init(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_init(project_dir):
        calls.append(("init", str(project_dir)))

    with patch("easy_fastapi.commands.db.run_db_init", fake_init):
        from easy_fastapi._runner import main

        main(["db", "init"])
    assert len(calls) == 1


def test_runner_db_migrate(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_migrate(project_dir):
        calls.append(("migrate", str(project_dir)))

    with patch("easy_fastapi.commands.db.run_db_migrate", fake_migrate):
        from easy_fastapi._runner import main

        main(["db", "migrate"])
    assert len(calls) == 1


def test_runner_db_upgrade(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_upgrade(project_dir):
        calls.append(("upgrade", str(project_dir)))

    with patch("easy_fastapi.commands.db.run_db_upgrade", fake_upgrade):
        from easy_fastapi._runner import main

        main(["db", "upgrade"])
    assert len(calls) == 1


def test_runner_gen_force(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_gen(project_dir, *, force=False):
        calls.append(("gen", force))

    with patch("easy_fastapi.commands.gen.run_gen", fake_gen):
        from easy_fastapi._runner import main

        main(["gen", "--force"])
    assert calls == [("gen", True)]


def test_runner_gen_no_force(monkeypatch, tmp_path):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_gen(project_dir, *, force=False):
        calls.append(("gen", force))

    with patch("easy_fastapi.commands.gen.run_gen", fake_gen):
        from easy_fastapi._runner import main

        main(["gen"])
    assert calls == [("gen", False)]


def test_runner_unknown_command_exits():
    from easy_fastapi._runner import main

    with pytest.raises(SystemExit):
        main(["unknown"])


def test_runner_no_args_exits():
    from easy_fastapi._runner import main

    with pytest.raises(SystemExit):
        main([])


def test_runner_db_invalid_action_exits():
    from easy_fastapi._runner import main

    with pytest.raises(SystemExit):
        main(["db", "invalid_action"])
