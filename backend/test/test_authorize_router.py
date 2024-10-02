#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from . import client


def test_login_success():
    response = client.post(
        '/api/login',
        data={'username': 'user', 'password': '123'},
    )
    assert response.status_code == 200
    assert 'access_token' in response.json().get('data', {})
    assert 'refresh_token' in response.json().get('data', {})


def test_login_unknown_username():
    response = client.post(
        '/api/login',
        data={'username': 'unknown', 'password': '123'},
    )
    assert response.status_code == 400
    assert response.json() == {'code': 400,'message': '用户名或邮箱不存在', 'data': None}


def test_login_bad_password():
    response = client.post(
        '/api/login',
        data={'username': 'user', 'password': '456'},
    )
    assert response.status_code == 400
    assert response.json() == {'code': 400,'message': '密码错误', 'data': None}


def test_register_success():
    global access_token, refresh_token

    username = str(datetime.now().microsecond)
    response = client.post(
        '/api/register',
        data={'username': username, 'password': '123456'},
    )
    assert response.status_code == 200
    assert response.json() == {'code': 200, 'message': '注册成功', 'data': {'username': username}}



def test_register_username_exists():
    response = client.post(
        '/api/register',
        data={'username': 'user', 'password': '123'},
    )
    assert response.status_code == 400
    assert response.json() == {'code': 400, 'message': '用户名已存在', 'data': None}


def test_register_invalid_data():
    response = client.post(
        '/api/register',
        data={'username': '', 'password': '123'},
    )
    assert response.status_code == 400
    assert response.json() == {'code': 400, 'message': '用户名和邮箱不能同时为空', 'data': None}