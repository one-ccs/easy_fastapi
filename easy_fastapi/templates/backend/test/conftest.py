#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture(scope='package')
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope='package')
def login_client(client: TestClient):
    response = client.post(
        '/token',
        data={'grant_type': 'password', 'username': 'user', 'password': '123'},
    )
    access_token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    client.headers.update(headers)
    yield client


def pytest_terminal_summary():
    import os
    if os.path.exists('temp'):
        os.remove('temp')
