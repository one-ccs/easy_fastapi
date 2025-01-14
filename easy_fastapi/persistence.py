#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Type, Any
from abc import ABC, abstractmethod

from redis import StrictRedis, Redis

from .config import config


class Persistence(ABC):

    @abstractmethod
    def get(self, key) -> Any:
        pass

    @abstractmethod
    def set(self, key, value, ex) -> Any:
        pass

    @abstractmethod
    def delete(self, key) -> Any:
        pass


class MemoryPersistence(Persistence):
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex):
        self.data[key] = value

    def delete(self, key):
        del self.data[key]


class RedisPersistence(Redis, Persistence):
    def __new__(cls):
        return StrictRedis(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            db=config.redis.db,
            decode_responses=config.redis.decode_responses,
        )


persistence: Type[Persistence] = (
    RedisPersistence()
    if config.redis.enabled else
    MemoryPersistence()
)
