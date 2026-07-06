"""api-sdk 包测试（@hey-api/openapi-ts 配置+sdk:gen 脚本，≥8 用例）。

适配扁平化迁移：shared/api-sdk/ → packages/api-sdk/，脚本名 gen → sdk:gen。
模板位于 templates/frontend/{base,pnpm}/frontend/packages/api-sdk/。
"""

import json

from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.renderer import Renderer


def _render(rel, **kw):
    """渲染 frontend 子树内模板（base 或 pnpm）。rel 相对 templates/frontend/。"""
    from importlib.resources import files
    from pathlib import Path

    defaults = {"project_name": "demo", "package_name": "demo", "frontend": True}
    defaults.update(kw)
    o = CreateOptions(**defaults)
    base = Path(str(files("easy_fastapi_cli") / "templates" / "frontend"))
    return Renderer(o).render((base / rel).read_text(encoding="utf-8"))


# ── 1. sdk package.json 命名空间 @demo/api-sdk ──


def test_sdk_package_name_namespaced():
    pkg = json.loads(_render("pnpm/frontend/packages/api-sdk/package.json.j2"))
    assert pkg["name"] == "@demo/api-sdk"


# ── 2. sdk package.json 含 sdk:gen 脚本 ──


def test_sdk_has_gen_sdk_script():
    pkg = json.loads(_render("pnpm/frontend/packages/api-sdk/package.json.j2"))
    assert "sdk:gen" in pkg["scripts"]


# ── 3. sdk package.json 含 hey-api 依赖 ──


def test_sdk_has_hey_api_deps():
    pkg = json.loads(_render("pnpm/frontend/packages/api-sdk/package.json.j2"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert "@hey-api/client-fetch" in deps
    assert "@hey-api/openapi-ts" in deps


# ── 4. sdk openapi-ts.config.ts 含 client 配置 ──


def test_sdk_has_hey_api_config():
    cfg = _render("pnpm/frontend/packages/api-sdk/openapi-ts.config.ts.j2")
    assert "@hey-api/client-fetch" in cfg


# ── 5. sdk openapi-ts.config.ts 含 input（openapi.json URL）──


def test_sdk_hey_api_has_input():
    cfg = _render("pnpm/frontend/packages/api-sdk/openapi-ts.config.ts.j2")
    assert "openapi.json" in cfg


# ── 6. sdk index.ts 含 export ──


def test_sdk_index_exports():
    out = _render("base/frontend/packages/api-sdk/src/index.ts")
    assert "export" in out


# ── 7. sdk package.json 含 private=true ──


def test_sdk_is_private():
    pkg = json.loads(_render("pnpm/frontend/packages/api-sdk/package.json.j2"))
    assert pkg.get("private") is True


# ── 8. sdk package.json 含 type=module ──


def test_sdk_is_module():
    pkg = json.loads(_render("pnpm/frontend/packages/api-sdk/package.json.j2"))
    assert pkg.get("type") == "module"


# ── 9. sdk README 含使用说明（按语言）──


def test_sdk_readme_zh():
    out = _render("base/frontend/packages/api-sdk/README.md.j2", language="zh")
    assert "api-sdk" in out
    assert "sdk:gen" in out


def test_sdk_readme_en():
    out = _render("base/frontend/packages/api-sdk/README.md.j2", language="en")
    assert "api-sdk" in out
    assert "sdk:gen" in out


# ── 10. 不同 package_name 渲染正确命名空间 ──


def test_sdk_custom_namespace():
    out = _render("pnpm/frontend/packages/api-sdk/package.json.j2", package_name="myapp")
    pkg = json.loads(out)
    assert pkg["name"] == "@myapp/api-sdk"
