"""pnpm workspace 骨架 + 根 package.json 测试（≥8 用例）。

适配扁平化：package.json.j2 / pnpm-workspace.yaml.j2 迁入
templates/frontend/pnpm/ 子树。根 package.json 精简为仅 sdk:gen 脚本。
"""

import json

import yaml
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.renderer import Renderer


def _render(path, **kw):
    from importlib.resources import files
    from pathlib import Path

    defaults = {"project_name": "demo", "package_name": "demo", "frontend": True}
    defaults.update(kw)
    o = CreateOptions(**defaults)
    r = Renderer(o)
    tpl = Path(str(files("easy_fastapi_cli") / "templates" / "frontend" / path)).read_text(encoding="utf-8")
    return r.render(tpl)


# ── 1. workspace yaml 含 packages/* 和 apps/* ──


def test_workspace_yaml_lists_apps_and_packages():
    out = _render("pnpm/pnpm-workspace.yaml.j2")
    data = yaml.safe_load(out)
    assert "frontend/packages/*" in data["packages"]
    assert "frontend/apps/*" in data["packages"]


# ── 2. workspace yaml 不含旧 shared/* ──


def test_workspace_yaml_no_shared():
    out = _render("pnpm/pnpm-workspace.yaml.j2")
    data = yaml.safe_load(out)
    assert "frontend/shared/*" not in data["packages"]
    assert "frontend/*" not in data["packages"]


# ── 3. 根 package.json 含 name = <pkg>-workspace ──


def test_root_package_json_name():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    assert pkg["name"] == "demo-workspace"


# ── 4. 根 package.json 含 sdk:gen 脚本 ──


def test_root_package_json_has_sdk_gen():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    assert "sdk:gen" in pkg["scripts"]


# ── 5. 根 package.json 不含 admin 相关脚本 ──


def test_root_package_json_no_admin_scripts():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    for s in ("dev", "build", "admin:dev", "preview"):
        assert s not in pkg["scripts"], f"不应再含 admin 脚本 {s}"


# ── 6. 根 package.json 不含根级 typescript 依赖 ──


def test_root_package_json_no_root_typescript():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    assert "devDependencies" not in pkg or "typescript" not in pkg.get("devDependencies", {})


# ── 7. 根 package.json 含 packageManager ──


def test_root_package_json_has_package_manager():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    assert "packageManager" in pkg
    assert "pnpm" in pkg["packageManager"]


# ── 8. 根 package.json 含 private=true ──


def test_root_package_json_is_private():
    pkg = json.loads(_render("pnpm/package.json.j2"))
    assert pkg.get("private") is True


# ── 9. workspace yaml 合法且只有 packages 键 ──


def test_workspace_yaml_valid():
    out = _render("pnpm/pnpm-workspace.yaml.j2")
    data = yaml.safe_load(out)
    assert isinstance(data, dict)
    assert "packages" in data
    assert len(data["packages"]) == 2


# ── 10. 不同 package_name 渲染正确 ──


def test_root_package_json_custom_name():
    out = _render("pnpm/package.json.j2", package_name="myapp")
    pkg = json.loads(out)
    assert pkg["name"] == "myapp-workspace"
