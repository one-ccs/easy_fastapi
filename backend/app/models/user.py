#!/usr/bin/env python
# -*- coding: utf-8 -*-
from dataclasses import dataclass

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core import Base, ToolClass
from app.utils import DateTimeUtil


class User(Base, ToolClass):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(64), unique=True, index=True)
    username = Column(String(32), unique=True, index=True)
    hashed_password = Column(String(60))
    token = Column(String(255))
    avatar_url = Column(String(255))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=DateTimeUtil.now())

    role = relationship('Role', back_populates='owner')
