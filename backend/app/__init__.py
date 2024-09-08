#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 设置 sys.path 以便在任何工作目录启动后端时，都能正确导入模块
import sys
sys.path.append(__file__[:__file__.index('backend') + len('backend')])


# 初始化配置文件
from app.core import config

from .main import app


__all__ = ['app']


# 导入错误处理模块
from app.core import exception_handler
# 最后导入路由
from app.routers import authorization_router
from app.routers import user_router
from app.routers import role_router


app.include_router(authorization_router, prefix='', tags=['用户认证'])
app.include_router(user_router, prefix='/user', tags=['用户'])
app.include_router(role_router, prefix='/role', tags=['角色'])
