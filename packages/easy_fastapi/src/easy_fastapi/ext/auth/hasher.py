"""密码哈希（pwdlib argon2 默认 + bcrypt 兼容验证）。

hash() 始终用 argon2（recommended）。
verify() 先尝试 argon2；若 argon2 不识别则回退 bcrypt 验证。
任何异常都返回 False（认证路径防御性：调用方只关心密码对不对，
不期望被 pwdlib 的内部异常打断——垃圾 hash / 空串 / 类型错误统一判失败）。
"""

from __future__ import annotations

from easy_fastapi.core.extras import require

_pwdlib = require("pwdlib", "pwdlib")
PasswordHash = _pwdlib.PasswordHash

_BcryptHasher = require("pwdlib", "pwdlib.hashers.bcrypt").BcryptHasher

# argon2 不识别 hash 格式时抛此异常（如 bcrypt hash），需捕获以回退
_argon2_error = getattr(_pwdlib.exceptions, "UnknownHashError", Exception)


class PwdlibPasswordHasher:
    def __init__(self) -> None:
        self._argon2 = PasswordHash.recommended()
        self._bcrypt = _BcryptHasher()

    def hash(self, password: str) -> str:
        return self._argon2.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        # 先尝试 argon2
        try:
            return self._argon2.verify(password, hashed_password)
        except (ValueError, TypeError, _argon2_error):
            pass
        # 回退 bcrypt（legacy）
        try:
            return self._bcrypt.verify(password, hashed_password)
        except (ValueError, TypeError):
            return False
