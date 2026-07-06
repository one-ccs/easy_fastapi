"""_add_frontend 完整片段清单测试（≥8 用例）。

适配 base+pnpm 双子树遍历：
- base/frontend/{apps/.gitkeep, packages/api-sdk/{README.md.j2, src/index.ts}}
- pnpm/{.npmrc, package.json.j2, pnpm-workspace.yaml.j2,
        frontend/packages/api-sdk/{openapi-ts.config.ts.j2, package.json.j2}}
"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _frontend_manifest(**kw):
    defaults = {"project_name": "demo", "package_name": "demo", "frontend": True}
    defaults.update(kw)
    o = CreateOptions(**defaults)
    m = build_manifest(o)
    return m


def _all_dests(**kw):
    m = _frontend_manifest(**kw)
    return {f.dest for f in m.fragments}


def _frontend_dests(**kw):
    return {d for d in _all_dests(**kw) if d.startswith("frontend/")}


# ── 1. 根级 workspace 文件（pyproject + package.json + pnpm-workspace + .npmrc）──


def test_fullstack_root_has_workspace_files():
    d = _all_dests()
    assert "pyproject.toml" in d
    assert "package.json" in d
    assert "pnpm-workspace.yaml" in d
    assert ".npmrc" in d
    assert ".gitignore" in d


# ── 2. frontend/apps/.gitkeep 存在 ──


def test_frontend_has_apps_gitkeep():
    d = _frontend_dests()
    assert "frontend/apps/.gitkeep" in d


# ── 3. api-sdk 配置文件（pnpm 子树）──


def test_frontend_has_api_sdk_configs():
    d = _frontend_dests()
    assert "frontend/packages/api-sdk/openapi-ts.config.ts" in d
    assert "frontend/packages/api-sdk/package.json" in d


# ── 4. api-sdk 静态文件（base 子树）──


def test_frontend_has_api_sdk_static():
    d = _frontend_dests()
    assert "frontend/packages/api-sdk/README.md" in d
    assert "frontend/packages/api-sdk/src/index.ts" in d


# ── 5. 旧 admin 结构不存在 ──


def test_frontend_admin_absent():
    d = _frontend_dests()
    assert not any("frontend/admin" in dest for dest in d), "不应再有 admin 目录"
    assert "frontend/tsconfig.json" not in d
    assert "frontend/vite.config.ts" not in d


# ── 6. 旧 shared 结构不存在 ──


def test_frontend_shared_absent():
    d = _frontend_dests()
    assert not any("frontend/shared" in dest for dest in d), "不应再有 shared 目录"


# ── 7. package.json/pnpm-workspace 在根级不在 frontend/ 下 ──


def test_workspace_files_at_root_not_frontend():
    d = _all_dests()
    assert "package.json" in d
    assert "frontend/package.json" not in d
    assert "pnpm-workspace.yaml" in d
    assert "frontend/pnpm-workspace.yaml" not in d


# ── 8. post_messages 含 pnpm ──


def test_frontend_post_messages_contain_pnpm():
    m = _frontend_manifest()
    joined = " ".join(m.post_messages)
    assert "pnpm" in joined


# ── 9. post_messages 含 sdk 生成提示 ──


def test_frontend_post_messages_contain_sdk_gen():
    m = _frontend_manifest()
    joined = " ".join(m.post_messages)
    assert "sdk" in joined.lower() or "SDK" in joined


# ── 10. backend-only 无 frontend/ 片段 ──


def test_no_frontend_fragments_when_backend_only():
    o = CreateOptions(project_name="demo", package_name="demo", frontend=False)
    m = build_manifest(o)
    assert not any(f.dest.startswith("frontend/") for f in m.fragments)
    # backend-only 也不应有 .npmrc/package.json
    d = {f.dest for f in m.fragments}
    assert ".npmrc" not in d
    assert "package.json" not in d
