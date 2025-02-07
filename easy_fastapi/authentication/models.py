#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional


class UserMixin:
    """用户基类，期望由用户实体类继承"""

    @property
    def identity(self) -> str:
        """用户名"""
        raise NotImplementedError()

    @property
    def h_pwd(self) -> str:
        """密码哈希值"""
        raise NotImplementedError()

    @property
    def scopes(self) -> Optional[list[str]]:
        """用户权限列表"""
        raise NotImplementedError()
