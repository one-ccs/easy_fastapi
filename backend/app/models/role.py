#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core import Base, ToolClass


class Role(Base, ToolClass):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    role = Column(String(16))
    owner_id = Column(Integer, ForeignKey('user.id'))

    owner = relationship('User', back_populates='role')
