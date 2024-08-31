#!/usr/bin/env python
# -*- coding: utf-8 -*-
from redis import StrictRedis

from . import config

redis_conn = StrictRedis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    db=config.REDIS_DB,
    decode_responses=config.REDIS_DECODE_RESPONSES,
)
