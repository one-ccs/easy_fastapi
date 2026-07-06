"""write_manifest 落盘测试（渲染+拷贝+建目录，≥8 用例）。"""

from pathlib import Path

from easy_fastapi_cli.scaffold.manifest import Fragment, Manifest
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.write import write_manifest


def _templates_root() -> Path:
    return Path(__file__).parent / "fixtures" / "templates"


def _ensure_template(rel: str, content: str, *, binary: bool = False) -> Path:
    """在测试 fixtures 下创建模板文件。"""
    p = _templates_root() / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    else:
        p.write_text(content, encoding="utf-8")
    return p


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. 渲染模板 fragment ──


def test_render_template_fragment(tmp_path):
    _ensure_template("common/hello.txt.j2", "hi {{ options.project_name }}")
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/hello.txt.j2", dest="out/hello.txt")])
    written = write_manifest(m, o, tmp_path, _templates_root())
    assert (tmp_path / "out" / "hello.txt").read_text(encoding="utf-8") == "hi demo"
    assert len(written) == 1


# ── 2. 原样拷贝非模板 fragment ──


def test_copy_non_template_fragment(tmp_path):
    _ensure_template("common/raw.bin", "RAW")
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/raw.bin", dest="data/raw.bin", is_template=False)])
    written = write_manifest(m, o, tmp_path, _templates_root())
    assert (tmp_path / "data" / "raw.bin").read_text(encoding="utf-8") == "RAW"
    assert len(written) == 1


# ── 3. 自动创建嵌套目录 ──


def test_creates_nested_dirs(tmp_path):
    _ensure_template("common/deep.txt.j2", "{{ options.project_name }}")
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/deep.txt.j2", dest="a/b/c/deep.txt")])
    write_manifest(m, o, tmp_path, _templates_root())
    assert (tmp_path / "a" / "b" / "c" / "deep.txt").exists()


# ── 4. 多 fragment 一次性落盘 ──


def test_multiple_fragments(tmp_path):
    _ensure_template("common/f1.txt.j2", "1{{ options.project_name }}")
    _ensure_template("common/f2.txt.j2", "2{{ options.package_name }}")
    o = _mk()
    m = Manifest(
        fragments=[
            Fragment(src="common/f1.txt.j2", dest="a/f1.txt"),
            Fragment(src="common/f2.txt.j2", dest="b/f2.txt"),
        ]
    )
    written = write_manifest(m, o, tmp_path, _templates_root())
    assert len(written) == 2
    assert (tmp_path / "a" / "f1.txt").read_text(encoding="utf-8") == "1demo"
    assert (tmp_path / "b" / "f2.txt").read_text(encoding="utf-8") == "2demo"


# ── 5. 返回写入的绝对路径列表 ──


def test_returns_absolute_paths(tmp_path):
    _ensure_template("common/hello.txt.j2", "hi")
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/hello.txt.j2", dest="out/hello.txt")])
    written = write_manifest(m, o, tmp_path, _templates_root())
    assert len(written) == 1
    assert written[0].is_absolute()
    assert written[0].exists()


# ── 6. 二进制原样拷贝（字节一致）──


def test_binary_copy_bytes(tmp_path):
    _ensure_template("common/data.bin", b"\x00\x01\x02FF", binary=True)
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/data.bin", dest="d/data.bin", is_template=False)])
    write_manifest(m, o, tmp_path, _templates_root())
    assert (tmp_path / "d" / "data.bin").read_bytes() == b"\x00\x01\x02FF"


# ── 7. 模板渲染含 layout 变量 ──


def test_render_with_layout(tmp_path):
    _ensure_template("common/layout.txt.j2", "layout={{ layout }}")
    o = _mk(frontend=True)
    m = Manifest(fragments=[Fragment(src="common/layout.txt.j2", dest="out/layout.txt")])
    write_manifest(m, o, tmp_path, _templates_root())
    assert (tmp_path / "out" / "layout.txt").read_text(encoding="utf-8") == "layout=fullstack"


# ── 8. 空 manifest 返回空列表 ──


def test_empty_manifest(tmp_path):
    o = _mk()
    written = write_manifest(Manifest(), o, tmp_path, _templates_root())
    assert written == []


# ── 9. 覆盖已存在文件 ──


def test_overwrites_existing(tmp_path):
    _ensure_template("common/hello.txt.j2", "new {{ options.project_name }}")
    dest = tmp_path / "out" / "hello.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("old", encoding="utf-8")
    o = _mk()
    m = Manifest(fragments=[Fragment(src="common/hello.txt.j2", dest="out/hello.txt")])
    write_manifest(m, o, tmp_path, _templates_root())
    assert dest.read_text(encoding="utf-8") == "new demo"
