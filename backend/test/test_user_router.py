#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime

from . import client, login


access_token, refresh_token = login()


def test_add_user():
    username = str(datetime.now().microsecond)

    response = client.post(
        '/api/user',
        json={'username': username, 'password': '123'},
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert response.status_code == 200
    assert response.json().get('data', {}).get('username') == username


def test_modify_user():
    response = client.put(
        '/api/user',
        json={
            'id': 3,
            'email': 'new_email@123.com',
        },
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert response.status_code == 200
    assert response.json().get('data', {}).get('email') == 'new_email@123.com'


def test_get_user():
    response = client.get(
        '/api/user',
        params={'id': 1},
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert response.status_code == 200
    assert response.json().get('data', {}).get('username') == 'user'


def test_delete_user():
    response = client.delete(
        '/api/user',
        params={'ids': [29, 30, 31]},
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert response.status_code == 200
    assert response.json().get('data') == 3


def test_delete_not_found_user():
    response = client.delete(
        '/api/user',
        params={'ids': [97, 98, 99]},
        headers={'Authorization': f'Bearer {access_token}'},
    )
    assert response.status_code == 200
    assert response.json().get('data') == 0
