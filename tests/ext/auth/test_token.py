"""TokenService 测试。"""

import jwt as pyjwt
import pytest
from easy_fastapi.ext.auth.schemas import TokenPayload
from easy_fastapi.ext.auth.token import TokenService


def test_create_and_decode_access_token():
    svc = TokenService(secret="test-secret", access_expire_minutes=30, refresh_expire_days=7)
    token = svc.create_access_token(sub="42")
    payload = svc.decode(token)
    assert isinstance(payload, TokenPayload)
    assert payload.sub == "42"
    assert payload.type == "access"
    assert payload.exp is not None
    assert payload.jti is not None
    assert payload.iat is not None


def test_create_and_decode_refresh_token():
    svc = TokenService(secret="s", access_expire_minutes=1, refresh_expire_days=7)
    token = svc.create_refresh_token(sub="42")
    payload = svc.decode(token)
    assert payload.type == "refresh"
    assert payload.sub == "42"
    assert payload.jti is not None


def test_decode_invalid_token_raises_decode_error():
    svc = TokenService(secret="s", access_expire_minutes=1, refresh_expire_days=1)
    with pytest.raises(pyjwt.DecodeError):
        svc.decode("not.a.jwt")


def test_decode_expired_token_raises_expired_signature():
    svc = TokenService(secret="s", access_expire_minutes=-1, refresh_expire_days=-1)
    token = svc.create_access_token(sub="42")
    with pytest.raises(pyjwt.ExpiredSignatureError):
        svc.decode(token)


def test_decode_wrong_secret_raises_invalid_signature():
    svc = TokenService(secret="secret-a")
    token = svc.create_access_token(sub="1")
    other = TokenService(secret="secret-b")
    with pytest.raises(pyjwt.InvalidSignatureError):
        other.decode(token)


def test_access_and_refresh_tokens_differ():
    svc = TokenService(secret="s")
    access = svc.create_access_token(sub="1")
    refresh = svc.create_refresh_token(sub="1")
    assert access != refresh


def test_token_is_three_part_jwt():
    svc = TokenService(secret="s")
    token = svc.create_access_token(sub="1")
    assert token.count(".") == 2


def test_default_expire_values():
    svc = TokenService(secret="s")
    assert svc._access_minutes > 0
    assert svc._refresh_days > 0


def test_refresh_max_age_property():
    svc = TokenService(secret="s", refresh_expire_days=7)
    assert svc.refresh_max_age == 7 * 86400


def test_jti_is_unique_per_token():
    svc = TokenService(secret="s")
    t1 = svc.create_access_token(sub="1")
    t2 = svc.create_access_token(sub="1")
    assert svc.decode(t1).jti != svc.decode(t2).jti


def test_sub_preserves_string():
    svc = TokenService(secret="s")
    token = svc.create_access_token(sub="user-123")
    assert svc.decode(token).sub == "user-123"


@pytest.mark.parametrize("alg", ["HS256", "HS384", "HS512"])
def test_custom_algorithm(alg):
    svc = TokenService(secret="s", algorithm=alg)
    token = svc.create_access_token(sub="1")
    payload = svc.decode(token)
    assert isinstance(payload, TokenPayload)
