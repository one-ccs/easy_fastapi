#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional, Any
from abc import ABC, abstractmethod

from redis import StrictRedis, Redis

from .config import Config


class BasePersistence(ABC):
    _instance: Optional['BasePersistence'] = None

    @abstractmethod
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @abstractmethod
    def get(self, key) -> Any:
        pass

    @abstractmethod
    def set(self, key, value, ex) -> Any:
        pass

    @abstractmethod
    def delete(self, key) -> Any:
        pass


class MemoryPersistence(BasePersistence):
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = {}
        return cls._instance

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex):
        self.data[key] = value

    def delete(self, key):
        del self.data[key]


class RedisPersistence(Redis, BasePersistence):
    def __new__(cls):
        if cls._instance is None:
            config = Config()

            cls._instance = StrictRedis(
                host=config.redis.host,
                port=config.redis.port,
                password=config.redis.password,
                db=config.redis.db,
                decode_responses=config.redis.decode_responses,
            )
        return cls._instance


class Persistence(BasePersistence):
    def __new__(cls):
        if cls._instance is None:
            config = Config()

            cls._instance = (
                RedisPersistence()
                if config.redis.enabled else
                MemoryPersistence()
            )
        return cls._instance
