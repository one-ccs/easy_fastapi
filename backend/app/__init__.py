#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .main import app


__all__ = ['app']


# 导入错误处理模块
from app.exceptions import exception_handler
# 最后导入路由
from app.routers import user_router


app.include_router(user_router, prefix='/api')
