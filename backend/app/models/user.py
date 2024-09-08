#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship, or_
from pydantic import EmailStr

from .rel_user_role import RelUserRole
from .role import Role
from app.core import BaseCRUD
from app.utils import DateTimeUtil


class User(BaseCRUD, SQLModel, table=True):
    __tablename__ = 'user'

    id: int | None          = Field(None, primary_key=True)
    email: EmailStr | None  = Field(None, unique=True, index=True, max_length=64)
    username: str | None    = Field(None, unique=True, index=True, max_length=32)
    hashed_password: str | None = Field(None, max_length=64)
    token: str | None       = Field(None, max_length=64)
    avatar_url: str | None  = Field(None, max_length=256)
    is_active: bool | None  = Field(True)
    created_at: datetime    = Field(default_factory=DateTimeUtil.now)

    roles: list[Role]       = Relationship(back_populates='users', link_model=RelUserRole)

    @staticmethod
    def by_username(username: str) -> Optional['User']:
        return User.query(User.username == username).first()

    @staticmethod
    def by_email(email: str) -> Optional['User']:
        return User.query(User.email == email).first()

    @staticmethod
    def by_username_or_email(username_or_email: str) -> Optional['User']:
        return User.query(
            or_(
                User.username == username_or_email,
                User.email == username_or_email,
            ),
        ).first()

    @staticmethod
    def get_roles(id: int) -> list[Role]:
        return Role.query(RelUserRole.user_id == id) \
            .join(RelUserRole) \
            .all()
