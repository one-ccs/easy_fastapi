#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 将后端项目的根目录 添加到 sys.path 中
import sys
sys.path.append(__file__[:__file__.index('backend') + len('backend')])

from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def login(username = 'user', password = '123'):
    response = client.post(
        '/api/login',
        data={'username': 'user', 'password': '123'},
    )
    access_token = response.json().get('data', {}).get('access_token')
    refresh_token = response.json().get('data', {}).get('refresh_token')

    return access_token, refresh_token
