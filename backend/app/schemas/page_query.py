#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Generic, TypeVar

from pydantic import BaseModel


_T = TypeVar('_T')


class PageQueryIn(BaseModel):
    page: int | None = 1
    size: int | None = 10
    query: str | None = ''


class PageQueryOut(BaseModel, Generic[_T]):
    total: int
    items: list[_T]
    finished: bool
