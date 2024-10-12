#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel


class RoleBase(BaseModel):
    role: str
    role_desc: str


class Role(RoleBase): ...


class RoleCreate(RoleBase): ...


class RoleModify(RoleBase):
    id: int
