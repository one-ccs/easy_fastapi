#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 设置 sys.path 以便在任何工作目录启动后端时，都能正确导入模块
import sys
sys.path.append(__file__[:__file__.index('backend') + len('backend')])

from .main import app


__all__ = ['app']


# 初始化配置文件
from app.core import config
# 导入错误处理模块
from app.core import exception_handler
# 最后导入路由
from app.routers import authorization_router
from app.routers import user_router


app.include_router(authorization_router, prefix='/api', tags=['用户认证'])
app.include_router(user_router, prefix='/api/user', tags=['用户'])
