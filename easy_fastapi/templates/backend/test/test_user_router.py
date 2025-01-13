#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient
import pytest


@pytest.mark.usefixtures('login_client')
def test_user(client: TestClient):
    response = client.get(
        '/user',
        params={'id': 1},
    )
    assert response.status_code == 200
