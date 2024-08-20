#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel


class RoleBase(BaseModel):
    role: str


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    id: int
    owner_id : int

    class Config:
        from_attributes = True
