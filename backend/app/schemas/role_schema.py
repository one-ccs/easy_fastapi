#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pydantic import BaseModel, ConfigDict


class RoleBase(BaseModel):
    role: str


class RoleCreate(RoleBase):
    pass


class Role(RoleBase):
    id: int
    owner_id : int

    model_config = ConfigDict(
        from_attributes=True,
    )
