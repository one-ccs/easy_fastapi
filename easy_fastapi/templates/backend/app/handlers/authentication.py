#!/usr/bin/env python
# -*- coding: utf-8 -*-
from easy_fastapi import (
    FailureException,
)
from easy_fastapi.authentication import (
    AuthHandler,
)

from ..models import User


class MyAuthHandler(AuthHandler):

    async def load_user(self, username: str) -> User:
        if not (user := await User.by_username_or_email(username)):
            raise FailureException('用户名或邮箱不存在')
        return user
