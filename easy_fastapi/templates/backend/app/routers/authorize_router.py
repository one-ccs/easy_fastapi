#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends


authorize_router = APIRouter()


@authorize_router.post('/auth/register')
async def register(user_data: dict):
    pass


@authorize_router.get('/auth/logout')
async def logout():
    pass
