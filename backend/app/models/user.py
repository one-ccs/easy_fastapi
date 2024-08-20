#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.utils import DateTimeUtil
from .db import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(64), unique=True, index=True)
    username = Column(String(32), unique=True, index=True)
    password = Column(String(255))
    created_at = Column(DateTime, default=DateTimeUtil.now())

    roles = relationship('Role', back_populates='owner')
