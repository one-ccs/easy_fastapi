#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .authorization_router import authorization_router
from .user_router import user_router
from .role_router import role_router


__all__ = [
    'authorization_router',
    'user_router',
    'role_router',
]
