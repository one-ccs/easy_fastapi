#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .authorize import (
    AUTH_HEADER_NAME,
    AUTH_TYPE,
    Token,
    TokenUser,
    UserMixin,
    EasyFastAPIAuthorize,
    encrypt_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    AuthenticationError,
)
from starlette.middleware.authentication import AuthenticationMiddleware
from fastapi.security import OAuth2PasswordRequestForm
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
    'Token',
    'TokenUser',
    'UserMixin',
    'EasyFastAPIAuthorize',
    'encrypt_password',
    'verify_password',
    'create_access_token',
    'create_refresh_token',
    'decode_token',

    'AuthenticationBackend',
    'AuthCredentials',
    'AuthenticationError',
    'AuthenticationMiddleware',
    'OAuth2PasswordRequestForm',
    'ExpiredSignatureError',
    'InvalidSignatureError',
    'DecodeError',
    'InvalidTokenError',
    'PyJWTError',
]
