"""冲突检查 + in_place 白名单测试（≥8 用例）。

check_target 返回 ConflictResult（status/offenders/whitelisted）：
- empty：目录空，可直接创建
- whitelist_only：仅白名单条目，警告并询问
- blocked：含非白名单条目，禁止
"""

from easy_fastapi_cli.scaffold.conflict import (
    WHITELIST_IN_PLACE,
    ConflictResult,
    check_target,
)

# ── 1. 不存在的新目标 → empty ──


def test_new_nonexistent_target_ok(tmp_path):
    target = tmp_path / "doesnotexist"
    r = check_target(target, in_place=False)
    assert r.status == "empty"


# ── 2. 存在但空的新目标 → empty ──


def test_new_empty_target_ok(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    r = check_target(target, in_place=False)
    assert r.status == "empty"


# ── 3. 存在且有文件的新目标 → blocked ──


def test_new_target_with_existing_files_blocked(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    (target / "somefile.txt").write_text("x")
    r = check_target(target, in_place=False)
    assert r.status == "blocked"


# ── 4. in_place 空目录 → empty ──


def test_in_place_empty_ok(tmp_path):
    r = check_target(tmp_path, in_place=True)
    assert r.status == "empty"


# ── 5. in_place 白名单文件共存 → whitelist_only ──


def test_in_place_whitelist_only(tmp_path):
    (tmp_path / "README.md").write_text("x")
    (tmp_path / ".git").mkdir()
    r = check_target(tmp_path, in_place=True)
    assert r.status == "whitelist_only"
    assert "README.md" in r.whitelisted


# ── 6. in_place 非白名单文件 → blocked ──


def test_in_place_unexpected_file_blocked(tmp_path):
    (tmp_path / "mystery.py").write_text("x")
    r = check_target(tmp_path, in_place=True)
    assert r.status == "blocked"
    assert "mystery.py" in r.offenders


# ── 7. 白名单常量内容 ──


def test_whitelist_contents():
    assert ".git" in WHITELIST_IN_PLACE
    assert "README.md" in WHITELIST_IN_PLACE
    assert ".easy-fastapi.json" in WHITELIST_IN_PLACE
    assert "LICENSE" in WHITELIST_IN_PLACE


# ── 8. in_place 多个白名单文件共存 → whitelist_only ──


def test_in_place_multiple_whitelist_ok(tmp_path):
    (tmp_path / "README.md").write_text("x")
    (tmp_path / "LICENSE").write_text("x")
    (tmp_path / ".gitignore").write_text("x")
    (tmp_path / "pyproject.toml").write_text("x")
    r = check_target(tmp_path, in_place=True)
    assert r.status == "whitelist_only"


# ── 9. in_place 白名单+非白名单混合 → blocked ──


def test_in_place_mixed_blocked(tmp_path):
    (tmp_path / "README.md").write_text("x")
    (tmp_path / "app.py").write_text("x")  # 非白名单
    r = check_target(tmp_path, in_place=True)
    assert r.status == "blocked"
    assert "app.py" in r.offenders
    assert "README.md" in r.whitelisted


# ── 10. blocked 结果含具体冲突文件名 ──


def test_in_place_blocked_has_offenders(tmp_path):
    (tmp_path / "app.py").write_text("x")
    r = check_target(tmp_path, in_place=True)
    assert "app.py" in r.offenders


# ── 11. 非 in_place 非空 blocked 提示信息含目录 ──


def test_new_target_blocked_has_entries(tmp_path):
    target = tmp_path / "newproj"
    target.mkdir()
    (target / "f.txt").write_text("x")
    r = check_target(target, in_place=False)
    assert r.status == "blocked"
    assert "f.txt" in r.offenders


# ── 12. in_place 下 package.json 存在时 → blocked ──


def test_in_place_package_json_blocks(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    r = check_target(tmp_path, in_place=True)
    assert r.status == "blocked"
    assert "package.json" in r.offenders


# ── 13. package.json 不在白名单 ──


def test_package_json_not_in_whitelist():
    assert "package.json" not in WHITELIST_IN_PLACE


# ── 14. ConflictResult 是 Pydantic 模型 ──


def test_conflict_result_is_model():
    r = ConflictResult(status="empty")
    assert r.model_dump() == {"status": "empty", "offenders": [], "whitelisted": []}
