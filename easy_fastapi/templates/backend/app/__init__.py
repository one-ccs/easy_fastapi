#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .main import app, auth


__all__ = ['app', 'auth']


# 绑定错误处理
# from app.handlers import xxx

# app.add_exception_handler(xxx, xxx_handler)


# 导入路由
from .routers import user_router as user_router
from .routers import role_router as role_router

app.include_router(user_router, prefix='/user', tags=['用户'])
app.include_router(role_router, prefix='/role', tags=['角色'])
