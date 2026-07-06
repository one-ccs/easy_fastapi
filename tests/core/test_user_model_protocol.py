"""UserModelProtocol / RoleModelProtocol 契约测试。"""

from easy_fastapi.core.protocols import RoleModelProtocol, UserModelProtocol

# ---- UserModelProtocol ----


class _FakeUserModel:
    """满足 UserModelProtocol 的最小假模型（classmethod 风格）。"""

    @classmethod
    async def get_by_username(cls, username):
        return None

    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_email(cls, email):
        return None

    @classmethod
    async def get_by_username_or_email(cls, username_or_email):
        return None

    @classmethod
    async def create_user(cls, username, hashed_password, **extra):
        pass

    @classmethod
    async def update_password(cls, id, hashed_password):
        pass


def test_user_model_protocol_accepts_compliant_class():
    assert isinstance(_FakeUserModel, UserModelProtocol)


def test_user_model_protocol_rejects_missing_get_by_username():
    class Bad:
        @classmethod
        async def get_by_id(cls, id):
            return None

        @classmethod
        async def create_user(cls, username, hashed_password, **extra):
            pass

        @classmethod
        async def update_password(cls, id, hashed_password):
            pass

    assert not isinstance(Bad, UserModelProtocol)


def test_user_model_protocol_rejects_missing_create_user():
    class Bad:
        @classmethod
        async def get_by_username(cls, username):
            return None

        @classmethod
        async def update_password(cls, id, hashed_password):
            pass

    assert not isinstance(Bad, UserModelProtocol)


def test_user_model_protocol_rejects_plain_object():
    assert not isinstance(object, UserModelProtocol)


# ---- RoleModelProtocol ----


class _FakeRoleModel:
    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_role(cls, role):
        return None

    @classmethod
    async def create_role(cls, role, role_desc, **extra):
        pass


def test_role_model_protocol_accepts_compliant_class():
    assert isinstance(_FakeRoleModel, RoleModelProtocol)


def test_role_model_protocol_rejects_missing_get_by_role():
    class Bad:
        @classmethod
        async def get_by_id(cls, id):
            return None

        @classmethod
        async def create_role(cls, role, role_desc, **extra):
            pass

    assert not isinstance(Bad, RoleModelProtocol)


def test_role_model_protocol_rejects_plain_object():
    assert not isinstance(object, RoleModelProtocol)
