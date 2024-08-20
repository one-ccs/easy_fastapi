#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from .db import Base


class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    role = Column(String(16))
    owner_id = Column(Integer, ForeignKey('users.id'))

    owner = relationship('User', back_populates='roles')
