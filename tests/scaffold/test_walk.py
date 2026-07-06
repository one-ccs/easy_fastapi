"""walk_tree helper 单元测试。"""

import pytest
from easy_fastapi_cli.scaffold.walk import walk_tree


@pytest.fixture
def template_tree(tmp_path):
    """创建测试用模板目录树。"""
    # .j2 模板
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py.j2").write_text("# {{ options.project_name }}", encoding="utf-8")
    # 非模板文件
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    # 嵌套子目录
    (tmp_path / "app" / "core").mkdir()
    (tmp_path / "app" / "core" / "config.py.j2").write_text("x=1", encoding="utf-8")
    return tmp_path


def test_walk_tree_returns_fragments(template_tree):
    frags = walk_tree(template_tree, dest_prefix="")
    assert len(frags) == 3


def test_walk_tree_j2_is_template(template_tree):
    frags = walk_tree(template_tree, dest_prefix="")
    j2_frags = [f for f in frags if f.is_template]
    assert len(j2_frags) == 2
    dests = {f.dest for f in j2_frags}
    assert "app/main.py" in dests
    assert "app/core/config.py" in dests


def test_walk_tree_non_j2_is_copy(template_tree):
    frags = walk_tree(template_tree, dest_prefix="")
    copy_frags = [f for f in frags if not f.is_template]
    assert len(copy_frags) == 1
    assert copy_frags[0].dest == "app/__init__.py"


def test_walk_tree_dest_strips_j2_suffix(template_tree):
    frags = walk_tree(template_tree, dest_prefix="")
    for f in frags:
        assert not f.dest.endswith(".j2")


def test_walk_tree_dest_prefix(template_tree):
    frags = walk_tree(template_tree, dest_prefix="frontend/")
    for f in frags:
        assert f.dest.startswith("frontend/")


def test_walk_tree_src_is_relative_to_root(template_tree):
    frags = walk_tree(template_tree, dest_prefix="frontend/")
    srcs = {f.src for f in frags}
    # src 用相对路径（POSIX 风格），精确匹配
    assert "app/main.py.j2" in srcs


def test_walk_tree_src_relative_to_custom_templates_root(template_tree):
    """templates_root != src_root 时，src 应包含子目录前缀（相对外层 templates_root）。"""
    # 模拟真实用法：walk_tree(fe_root, dest_prefix="frontend/", templates_root=templates_root)
    # 其中 fe_root = templates_root / "frontend"。这里用 sub 子目录验证。
    sub_root = template_tree / "sub"
    sub_root.mkdir()
    (sub_root / "app").mkdir()
    (sub_root / "app" / "main.py.j2").write_text("# {{ options.project_name }}", encoding="utf-8")
    (sub_root / "app" / "__init__.py").write_text("", encoding="utf-8")

    frags = walk_tree(sub_root, dest_prefix="frontend/", templates_root=template_tree)
    srcs = {f.src for f in frags}
    # src 应相对于外层 templates_root，因此带 "sub/" 前缀
    assert "sub/app/main.py.j2" in srcs
    assert "sub/app/__init__.py" in srcs
    # dest 仍相对于 src_root（不含 "sub/" 前缀）
    dests = {f.dest for f in frags}
    assert "frontend/app/main.py" in dests
    assert "frontend/app/__init__.py" in dests


def test_walk_tree_empty_dir(tmp_path):
    (tmp_path / "empty").mkdir()
    frags = walk_tree(tmp_path / "empty", dest_prefix="")
    assert frags == []


def test_walk_tree_ignores_dirs(tmp_path):
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file.txt.j2").write_text("hi", encoding="utf-8")
    frags = walk_tree(tmp_path, dest_prefix="")
    assert len(frags) == 1
    assert frags[0].dest == "subdir/file.txt"
