#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar('T')


class PageQueryIn(BaseModel):
    page: int | None = 1
    size: int | None = 10
    query: str | None = ''


class PageQueryOut(BaseModel, Generic[T]):
    total: int
    items: list[T]
    finished: bool
