#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient


def test_login_success(client: TestClient):
    response = client.post(
        '/auth/login',
        data={'grant_type': 'password', 'username': 'user', 'password': '123'},
    )
    assert response.status_code == 200


def test_login_failed(client: TestClient):
    response = client.post(
        '/auth/login',
        data={'grant_type': 'password', 'username': 'user', 'password': '456'},
    )
    assert response.status_code == 400
    assert response.json() == { 'code': 400, 'message': '密码错误', 'data': None }

    response = client.post(
        '/auth/login',
        data={'grant_type': 'password', 'username': 'user2', 'password': '456'},
    )
    assert response.status_code == 400
    assert response.json() == { 'code': 400, 'message': '用户名或邮箱不存在', 'data': None }
