"""统一错误处理验收：所有用户面错误经 ConfigError/ExtensionError，消息可读。"""

import pytest
from easy_fastapi.core.exceptions import ConfigError, ExtensionError


# --- require() 可选依赖守卫 ---
def test_require_missing_dependency_translates_to_uv_hint():
    from easy_fastapi.core.extras import require

    err = None
    try:
        require("definitely-not-a-real-pkg-xyz", "definitely_not_a_real_pkg_xyz")
    except ExtensionError as e:
        err = e
    assert err is not None
    assert "uv add" in str(err) or "安装" in str(err)


# --- Config 错误 ---
def test_config_missing_file_raises_configerror(tmp_path):
    from easy_fastapi.core.config.loader import ConfigLoader

    with pytest.raises(ConfigError):
        ConfigLoader.from_yaml(tmp_path / "nope.yaml")


def test_config_extra_forbid_raises_validation_error():
    from easy_fastapi.core.config.models import FastAPIConfig
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FastAPIConfig(bogus_field=1)


# --- 校验铁律错误经 ConfigError ---
def test_validate_b_rule_is_configerror():
    from easy_fastapi_cli.scaffold.options import CreateOptions
    from easy_fastapi_cli.scaffold.validate import validate

    with pytest.raises(ConfigError):
        validate(CreateOptions(project_name="p", package_name="p", database=True))


def test_validate_c_rule_auth_needs_database_is_configerror():
    from easy_fastapi_cli.scaffold.options import CreateOptions
    from easy_fastapi_cli.scaffold.validate import validate

    with pytest.raises(ConfigError):
        validate(CreateOptions(project_name="p", package_name="p", auth=True))


def test_validate_migration_needs_orm_is_configerror():
    from easy_fastapi_cli.scaffold.options import CreateOptions
    from easy_fastapi_cli.scaffold.validate import validate

    with pytest.raises(ConfigError):
        validate(CreateOptions(project_name="p", package_name="p", migration=True))


# --- extension require 缺失经 ExtensionError ---
def test_auth_requires_orm_is_extensionerror(tmp_path):
    from easy_fastapi.core.app import EasyFastAPI
    from easy_fastapi.ext.auth.extension import AuthExtension
    from fastapi import FastAPI

    p = tmp_path / "easy-fastapi.yaml"
    p.write_text(
        'fastapi:\n  root_path: /api\neasy_fastapi:\n  auth:\n    secret: "kXXXXXXXXXXXXXXX"\n',
        encoding="utf-8",
    )
    easy = EasyFastAPI(FastAPI(), config_path=p)
    with pytest.raises(ExtensionError):
        easy.use(AuthExtension())


# --- migration 无 ORM 经 ExtensionError ---
def test_migration_no_orm_is_extensionerror():
    import asyncio

    from easy_fastapi.ext.migration.base import dispatch_migration_op

    with pytest.raises(ExtensionError):
        asyncio.new_event_loop().run_until_complete(dispatch_migration_op(orm=None, op="migrate"))


# --- create 冲突返回 blocked 状态（错误语气，禁止创建） ---
def test_create_conflict_returns_blocked(tmp_path):
    from easy_fastapi_cli.scaffold.conflict import check_target

    target = tmp_path / "x"
    target.mkdir()
    (target / "f.txt").write_text("x")
    r = check_target(target, in_place=False)
    assert r.status == "blocked"
    assert "f.txt" in r.offenders


def test_create_in_place_conflict_returns_blocked(tmp_path):
    from easy_fastapi_cli.scaffold.conflict import check_target

    (tmp_path / "f.txt").write_text("x")
    r = check_target(tmp_path, in_place=True)
    assert r.status == "blocked"
    assert "f.txt" in r.offenders


# --- marker 损坏经 ConfigError ---
def test_marker_corrupt_is_configerror(tmp_path):
    from easy_fastapi.project import read_marker

    (tmp_path / ".easy-fastapi.json").write_text("{bad", encoding="utf-8")
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


def test_marker_missing_is_configerror(tmp_path):
    from easy_fastapi.project import read_marker

    with pytest.raises(ConfigError):
        read_marker(tmp_path)


# --- gen 冲突经 GenConflictError（非静默）---
def test_gen_conflict_not_silent(tmp_path):
    from easy_fastapi.commands.conflict import GenConflictError
    from easy_fastapi.commands.gen import generate_for_model
    from easy_fastapi.core.introspection import FieldMeta, ModelMeta

    meta = ModelMeta(
        name="X",
        fields=[FieldMeta(name="id", type_name="int", primary_key=True, nullable=False, relation=None)],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    with pytest.raises(GenConflictError):
        generate_for_model(meta, project_dir=tmp_path, force=False)


def test_gen_force_overwrites_conflict(tmp_path):
    from easy_fastapi.commands.gen import generate_for_model
    from easy_fastapi.core.introspection import FieldMeta, ModelMeta

    meta = ModelMeta(
        name="Y",
        fields=[FieldMeta(name="id", type_name="int", primary_key=True, nullable=False, relation=None)],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    # force=True 不应抛
    generate_for_model(meta, project_dir=tmp_path, force=True)


# --- require 消息含包名与原始错误 ---
def test_require_error_message_contains_pkg_name():
    from easy_fastapi.core.extras import require

    with pytest.raises(ExtensionError) as exc_info:
        require("some-pkg-name", "some_pkg_name")
    msg = str(exc_info.value)
    assert "some-pkg-name" in msg or "some_pkg_name" in msg
