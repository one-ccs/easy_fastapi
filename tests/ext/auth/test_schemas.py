"""auth schemas 测试。"""

import pytest
from easy_fastapi.ext.auth.schemas import LoginRequest, TokenPayload, TokenResponse
from pydantic import ValidationError


def test_login_request_valid():
    r = LoginRequest(username="alice", password="secret")
    assert r.username == "alice"
    assert r.password == "secret"


def test_login_request_missing_password():
    with pytest.raises(ValidationError):
        LoginRequest(username="alice")  # type: ignore[call-arg]


def test_login_request_missing_username():
    with pytest.raises(ValidationError):
        LoginRequest(password="secret")  # type: ignore[call-arg]


def test_login_request_empty():
    with pytest.raises(ValidationError):
        LoginRequest()  # type: ignore[call-arg]


def test_login_request_forbid_extra():
    with pytest.raises(ValidationError):
        LoginRequest(username="a", password="b", extra="no")  # type: ignore[call-arg]


def test_login_request_empty_strings_ok():
    """空串不算缺失（str 默认不 strip），允许构造。"""
    r = LoginRequest(username="", password="")
    assert r.username == ""
    assert r.password == ""


def test_token_response_default_type():
    t = TokenResponse(access_token="a", refresh_token="r")
    assert t.token_type == "bearer"


def test_token_response_custom_type():
    t = TokenResponse(access_token="a", refresh_token="r", token_type="custom")
    assert t.token_type == "custom"


def test_token_response_missing_token():
    with pytest.raises(ValidationError):
        TokenResponse(refresh_token="r")  # type: ignore[call-arg]


def test_token_response_refresh_optional():
    """refresh_token 可选（access-only 模式下为 None）。"""
    t = TokenResponse(access_token="a")
    assert t.refresh_token is None
    assert t.access_token == "a"
    assert t.token_type == "bearer"


# ── TokenPayload ──


def test_token_payload_defaults():
    """TokenPayload 全部字段默认为 None。"""
    p = TokenPayload()
    assert p.iss is None
    assert p.sub is None
    assert p.aud is None
    assert p.exp is None
    assert p.nbf is None
    assert p.iat is None
    assert p.jti is None
    assert p.type is None
    assert p.scopes is None


def test_token_payload_from_jwt_payload():
    """从 JWT decode 的 dict 构造 TokenPayload。"""
    p = TokenPayload(sub="42", type="access", jti="abc", exp=9999999, iat=1000)
    assert p.sub == "42"
    assert p.type == "access"
    assert p.jti == "abc"
    assert p.exp == 9999999


def test_token_payload_accepts_extra_fields():
    """TokenPayload 忽略未声明的额外字段（pydantic v2 默认 ignore）。"""
    p = TokenPayload(sub="1", type="access", extra_field="ignored")
    assert p.sub == "1"
    # 额外字段不报错，也不保留
