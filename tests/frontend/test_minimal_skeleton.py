"""前端最小骨架端到端测试（需求 §十四）。

验证 fullstack 生成后：存在最小骨架文件、不存在旧 admin/shared 结构、
workspace globs 正确、根 package.json 无 admin 脚本与根级 typescript。
"""

import json

import yaml
from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _create_fullstack(tmp_path, name="skel"):
    target = tmp_path / name
    args = [
        "create",
        str(target),
        "--no-interactive",
        "--project-name",
        name,
        "--package-name",
        name,
        "--frontend",
    ]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return target


# ── 存在性：最小骨架文件清单 ──


def test_minimal_files_exist(tmp_path):
    t = _create_fullstack(tmp_path)
    assert (t / ".npmrc").exists()
    assert (t / "package.json").exists()
    assert (t / "pnpm-workspace.yaml").exists()
    assert (t / "frontend" / "apps" / ".gitkeep").exists()
    sdk = t / "frontend" / "packages" / "api-sdk"
    assert (sdk / "openapi-ts.config.ts").exists()
    assert (sdk / "package.json").exists()
    assert (sdk / "README.md").exists()
    assert (sdk / "src" / "index.ts").exists()


# ── 不存在性：旧 admin/shared 结构 ──


def test_old_admin_structure_absent(tmp_path):
    t = _create_fullstack(tmp_path)
    assert not (t / "frontend" / "admin").exists()
    assert not (t / "frontend" / "tsconfig.json").exists()
    assert not (t / "frontend" / "vite.config.ts").exists()
    assert not (t / "frontend" / "shared").exists()


# ── workspace globs 正确 ──


def test_workspace_globs(tmp_path):
    t = _create_fullstack(tmp_path)
    data = yaml.safe_load((t / "pnpm-workspace.yaml").read_text(encoding="utf-8"))
    assert "frontend/packages/*" in data["packages"]
    assert "frontend/apps/*" in data["packages"]
    assert "frontend/shared/*" not in data["packages"]


# ── 根 package.json 无 admin 脚本与根级 typescript ──


def test_root_package_json_clean(tmp_path):
    t = _create_fullstack(tmp_path)
    pkg = json.loads((t / "package.json").read_text(encoding="utf-8"))
    for s in ("dev", "build", "admin:dev", "preview"):
        assert s not in pkg.get("scripts", {}), f"根包不应含 admin 脚本 {s}"
    assert "typescript" not in pkg.get("devDependencies", {})


# ── api-sdk 包名命名空间 ──


def test_api_sdk_package_name(tmp_path):
    t = _create_fullstack(tmp_path, "mysdk")
    pkg = json.loads((t / "frontend" / "packages" / "api-sdk" / "package.json").read_text(encoding="utf-8"))
    assert pkg["name"] == "@mysdk/api-sdk"


# ── .npmrc 内容 ──


def test_npmrc_content(tmp_path):
    t = _create_fullstack(tmp_path)
    content = (t / ".npmrc").read_text(encoding="utf-8")
    assert "link-workspace-packages=true" in content
    assert "prefer-workspace-packages=true" in content
    assert "save-workspace-protocol=true" in content


# ── openapi-ts.config.ts 配置 ──


def test_hey_api_config(tmp_path):
    t = _create_fullstack(tmp_path)
    cfg = (t / "frontend" / "packages" / "api-sdk" / "openapi-ts.config.ts").read_text(encoding="utf-8")
    assert "@hey-api/client-fetch" in cfg
    assert "openapi.json" in cfg
    assert "src" in cfg


# ── sdk:gen 脚本链路 ──


def test_gen_sdk_chain(tmp_path):
    t = _create_fullstack(tmp_path)
    root_pkg = json.loads((t / "package.json").read_text(encoding="utf-8"))
    sdk_pkg = json.loads((t / "frontend" / "packages" / "api-sdk" / "package.json").read_text(encoding="utf-8"))
    # 根包 sdk:gen filter 到 api-sdk 的 sdk:gen
    assert "api-sdk" in root_pkg["scripts"]["sdk:gen"]
    assert "sdk:gen" in sdk_pkg["scripts"]
