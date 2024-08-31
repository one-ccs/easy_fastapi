#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel


class Result(BaseModel):
    code: int
    message: str
    data: dict | None = None
