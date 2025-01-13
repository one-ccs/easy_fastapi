#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Generic, TypeVar
from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel


_T = TypeVar('_T')


@dataclass
class PageQuery():
    page: int   = Query(1)
    size: int   = Query(10)
    query: str  = Query('')


class PageQueryOut(BaseModel, Generic[_T]):
    total: int
    items: list[_T]
    finished: bool
