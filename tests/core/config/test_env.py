"""env 覆盖层 apply_env_overlay 测试。

覆盖：跳过非 EFA_ 前缀、顶层标量、两层/三层嵌套、不修改入参、
大小写不敏感、JSON 值转换、空 environ、多键合并。
"""

from easy_fastapi.core.config.env import apply_env_overlay

# ---- 前缀过滤（正常路径 + 边界） ----


def test_overlay_skips_non_prefixed():
    raw = {"a": 1}
    out = apply_env_overlay(raw, {"NOT_EFA": "x", "OTHER": "y"})
    assert out == {"a": 1}


def test_overlay_empty_environ_returns_copy():
    raw = {"a": 1}
    out = apply_env_overlay(raw, {})
    assert out == {"a": 1}
    assert out is not raw  # 返回副本，非同一对象


# ---- 标量与多层嵌套（正常路径） ----


def test_overlay_top_level_scalar():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_FOO": "bar"})
    assert out == {"foo": "bar"}


def test_overlay_nested_two_levels():
    raw = {"fastapi": {"root_path": "/old"}}
    out = apply_env_overlay(raw, {"EFA_FASTAPI__ROOT_PATH": "/api"})
    assert out["fastapi"]["root_path"] == "/api"


def test_overlay_nested_three_levels():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_FASTAPI__MIDDLEWARE__CORS__ENABLED": "true"})
    assert out["fastapi"]["middleware"]["cors"]["enabled"] is True


def test_overlay_nested_four_levels():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_A__B__C__D": "val"})
    assert out["a"]["b"]["c"]["d"] == "val"


# ---- 不变性（边界） ----


def test_overlay_does_not_mutate_input():
    raw = {"fastapi": {"root_path": "/old"}}
    apply_env_overlay(raw, {"EFA_FASTAPI__ROOT_PATH": "/api"})
    assert raw == {"fastapi": {"root_path": "/old"}}


def test_overlay_does_not_mutate_input_deep():
    raw = {"fastapi": {"middleware": {"cors": {"enabled": False}}}}
    apply_env_overlay(raw, {"EFA_FASTAPI__MIDDLEWARE__CORS__ENABLED": "true"})
    assert raw["fastapi"]["middleware"]["cors"]["enabled"] is False


# ---- 大小写不敏感（边界） ----


def test_overlay_case_insensitive_key():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_Database__Host": "db.local"})
    assert out["database"]["host"] == "db.local"


def test_overlay_case_insensitive_prefix():
    raw = {}
    # 仅 value 注入，key 统一小写
    out = apply_env_overlay(raw, {"EFA_API__TokenURL": "/oauth/token"})
    assert out["api"]["tokenurl"] == "/oauth/token"


# ---- JSON 值转换（边界 / 集成意图） ----


def test_overlay_coerces_int_value():
    out = apply_env_overlay({}, {"EFA_PORT": "8080"})
    assert out["port"] == 8080
    assert isinstance(out["port"], int)


def test_overlay_coerces_bool_true():
    out = apply_env_overlay({}, {"EFA_FLAG": "true"})
    assert out["flag"] is True


def test_overlay_coerces_bool_false():
    out = apply_env_overlay({}, {"EFA_FLAG": "false"})
    assert out["flag"] is False


def test_overlay_coerces_json_list():
    out = apply_env_overlay({}, {"EFA_ORIGINS": '["https://a.com","https://b.com"]'})
    assert out["origins"] == ["https://a.com", "https://b.com"]


def test_overlay_keeps_plain_string_when_not_json():
    out = apply_env_overlay({}, {"EFA_HOST": "db.local"})
    assert out["host"] == "db.local"


def test_overlay_keeps_pathlike_string():
    # '/var/uploads' 不是合法 JSON → 保留原串
    out = apply_env_overlay({}, {"EFA_UPLOAD_DIR": "/var/uploads"})
    assert out["upload_dir"] == "/var/uploads"


# ---- JSON 类型转换边界 ----
# 规则：全部走 json.loads 自然行为——
# 数字→int、true/false→bool、list/dict→容器；非法 JSON 保留原字符串交消费方处理。


def test_overlay_json_list_value():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_FASTAPI__MIDDLEWARE__CORS__ALLOW_ORIGINS": '["http://localhost:5173"]'})
    assert out["fastapi"]["middleware"]["cors"]["allow_origins"] == ["http://localhost:5173"]


def test_overlay_json_dict_value():
    raw = {}
    out = apply_env_overlay(raw, {"EFA_SOMETHING": '{"k": 1}'})
    assert out["something"] == {"k": 1}


def test_overlay_number_coerced_to_int():
    # 经裁决：json.loads('6379') 成功 → int 6379（消费方 Pydantic 字段若为 int 直接收；
    # 若为 str 字段则 Pydantic 会按需处理）。env overlay 不强行保留字符串。
    out = apply_env_overlay({}, {"EFA_REDIS__PORT": "6379"})
    assert out["redis"]["port"] == 6379
    assert isinstance(out["redis"]["port"], int)


def test_overlay_float_coerced():
    out = apply_env_overlay({}, {"EFA_RATIO": "0.75"})
    assert out["ratio"] == 0.75


def test_overlay_json_bool_value_parsed():
    out = apply_env_overlay({}, {"EFA_X": "true"})
    assert out["x"] is True


def test_overlay_json_null_value_parsed():
    out = apply_env_overlay({}, {"EFA_X": "null"})
    assert out["x"] is None


def test_overlay_plain_text_with_spaces_kept():
    # 含空格纯文本不是合法 JSON → 保留原串
    out = apply_env_overlay({}, {"EFA_DB__PASSWORD": "p@ss w0rd"})
    assert out["db"]["password"] == "p@ss w0rd"


def test_overlay_nested_list_overrides_existing():
    raw = {"redis": {"allow_origins": ["old"]}}
    out = apply_env_overlay(raw, {"EFA_REDIS__ALLOW_ORIGINS": '["new"]'})
    assert out["redis"]["allow_origins"] == ["new"]


# ---- 多键合并（集成意图） ----


def test_overlay_merges_multiple_keys():
    raw = {"fastapi": {"swagger": {"title": "Old"}}}
    out = apply_env_overlay(
        raw,
        {
            "EFA_FASTAPI__ROOT_PATH": "/api",
            "EFA_FASTAPI__SWAGGER__TITLE": "New",
            "UNRELATED": "skip",
        },
    )
    assert out["fastapi"]["root_path"] == "/api"
    assert out["fastapi"]["swagger"]["title"] == "New"
    assert "UNRELATED" not in out
