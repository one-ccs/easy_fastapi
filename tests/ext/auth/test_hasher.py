"""PwdlibPasswordHasher 测试。"""

from easy_fastapi.core.protocols import PasswordHasher
from easy_fastapi.ext.auth.hasher import PwdlibPasswordHasher


def test_hasher_satisfies_protocol():
    assert isinstance(PwdlibPasswordHasher(), PasswordHasher)


def test_hash_returns_non_plain():
    h = PwdlibPasswordHasher()
    hashed = h.hash("secret123")
    assert hashed != "secret123"
    assert len(hashed) > 20


def test_hash_and_verify_argon2():
    h = PwdlibPasswordHasher()
    hashed = h.hash("secret123")
    assert h.verify("secret123", hashed) is True
    assert h.verify("wrong", hashed) is False


def test_hash_is_random_salt():
    """两次 hash 同一密码应不同（盐随机）。"""
    h = PwdlibPasswordHasher()
    a = h.hash("samepw")
    b = h.hash("samepw")
    assert a != b
    assert h.verify("samepw", a)
    assert h.verify("samepw", b)


def test_hash_empty_password():
    h = PwdlibPasswordHasher()
    hashed = h.hash("")
    assert h.verify("", hashed) is True
    assert h.verify("x", hashed) is False


def test_hash_unicode_password():
    h = PwdlibPasswordHasher()
    hashed = h.hash("密码🔐123")
    assert h.verify("密码🔐123", hashed) is True


def test_verify_bcrypt_legacy_hash():
    import bcrypt

    h = PwdlibPasswordHasher()
    real_bcrypt = bcrypt.hashpw(b"password", bcrypt.gensalt(rounds=4)).decode()
    assert h.verify("password", real_bcrypt) is True
    assert h.verify("wrong", real_bcrypt) is False


def test_verify_bcrypt_legacy_with_unicode():
    import bcrypt

    h = PwdlibPasswordHasher()
    real_bcrypt = bcrypt.hashpw("密码123".encode(), bcrypt.gensalt(rounds=4)).decode()
    assert h.verify("密码123", real_bcrypt) is True


def test_verify_garbage_returns_false():
    """verify 乱码 hash 不抛异常，返回 False。"""
    h = PwdlibPasswordHasher()
    assert h.verify("anything", "not-a-valid-hash") is False


def test_verify_none_returns_false():
    h = PwdlibPasswordHasher()
    assert h.verify("x", "") is False
