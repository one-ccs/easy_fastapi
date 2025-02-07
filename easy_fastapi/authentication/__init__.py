#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .global_var import (
    AUTH_HEADER_NAME,
    AUTH_TYPE,
)
from .authentication import EasyAuthentication
from .models import UserMixin
from .schemas import (
    Token,
    BaseUser,
)
from .utils import (
    encrypt_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from .handlers import (
    AuthenticationHandler,
    AuthHandler,
)

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import computed_field
from jwt import (
    ExpiredSignatureError,
    InvalidSignatureError,
    DecodeError,
    InvalidTokenError,
    PyJWTError,
)

__all__ = [
    'AUTH_HEADER_NAME',
    'AUTH_TYPE',
    'EasyAuthentication',
    'UserMixin',
    'Token',
    'BaseUser',
    'encrypt_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',
    'AuthenticationHandler',
    'AuthHandler',

    'OAuth2PasswordRequestForm',
    'computed_field',
    'ExpiredSignatureError',
    'InvalidSignatureError',
    'DecodeError',
    'InvalidTokenError',
    'PyJWTError',
]
