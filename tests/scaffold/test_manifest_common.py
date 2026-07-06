"""build_manifest common 片段测试（≥8 用例）。"""

from easy_fastapi_cli.scaffold.manifest import Manifest, build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. common 三文件存在 ──


def test_common_fragments_present_minimal():
    m = build_manifest(_mk())
    dests = {f.dest for f in m.fragments}
    assert "pyproject.toml" in dests
    assert "app/main.py" in dests
    assert "easy-fastapi.yaml" in dests


# ── 2. common 含 __init__.py（非模板拷贝）──


def test_common_init_py_fragment():
    m = build_manifest(_mk())
    inits = [f for f in m.fragments if f.dest == "app/__init__.py"]
    assert len(inits) == 1
    assert inits[0].is_template is True


# ── 3. core 依赖 ──


def test_core_dependencies():
    m = build_manifest(_mk())
    assert "fastapi" in m.dependencies
    assert "uvicorn" in m.dependencies


# ── 4. 无 ORM 时不混入 ORM 依赖 ──


def test_no_orm_deps_when_minimal():
    m = build_manifest(_mk())
    joined = " ".join(m.dependencies)
    assert "tortoise-orm" not in joined
    assert "sqlalchemy" not in joined
    assert "sqlmodel" not in joined


# ── 5. 返回 Manifest 实例 ──


def test_build_manifest_returns_manifest():
    m = build_manifest(_mk())
    assert isinstance(m, Manifest)


# ── 6. fragments 非空 ──


def test_fragments_not_empty():
    m = build_manifest(_mk())
    assert len(m.fragments) > 0


# ── 7. 每个 fragment src 非空 ──


def test_fragment_src_not_empty():
    m = build_manifest(_mk())
    for f in m.fragments:
        assert f.src, f"fragment dest={f.dest} has empty src"


# ── 8. common 片段 src 以 backend/base/backend/ 开头 ──


def test_common_fragment_src_prefix():
    m = build_manifest(_mk())
    base_frags = [f for f in m.fragments if f.src.startswith("backend/base/backend/")]
    assert len(base_frags) >= 3  # pyproject/main/config + __init__


# ── 9. 依赖列表含 pydantic ──


def test_dependencies_include_pydantic():
    m = build_manifest(_mk())
    assert "pydantic" in m.dependencies


# ── 10. 依赖列表含 easy-pyoc ──


def test_dependencies_include_easy_pyoc():
    m = build_manifest(_mk())
    assert "easy-pyoc" in m.dependencies


# ── 11. common 含 bootstrap 三件套（app_factory + routers + __init__）──


def test_common_bootstrap_fragments_present():
    m = build_manifest(_mk())
    dests = {f.dest for f in m.fragments}
    assert "app/bootstrap/__init__.py" in dests
    assert "app/bootstrap/app_factory.py" in dests
    assert "app/bootstrap/routers.py" in dests


# ── 12. bootstrap 片段 src 指向 backend/base/backend/app/bootstrap/ ──


def test_common_bootstrap_fragment_src():
    m = build_manifest(_mk())
    bootstrap_frags = [f for f in m.fragments if "bootstrap" in f.dest]
    srcs = {f.src for f in bootstrap_frags}
    assert "backend/base/backend/app/bootstrap/__init__.py.j2" in srcs
    assert "backend/base/backend/app/bootstrap/app_factory.py.j2" in srcs
    assert "backend/base/backend/app/bootstrap/routers.py.j2" in srcs
