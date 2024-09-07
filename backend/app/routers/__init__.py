#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .authorize_router import authorization_router
from .user_router import user_router
from .role_router import role_router


__all__ = [
    'authorize_router',
    'user_router',
    'role_router',
]
