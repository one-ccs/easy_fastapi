#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from . import config
from app.utils import ObjectUtil


engine = create_engine(config.DATABASE_URI)

SessionLocal = sessionmaker(autoflush=False, bind=engine)

Base = declarative_base()

Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ToolClass:
    ignore_properties = ('_sa_instance_state',)

    def __repr__(self):
        return ObjectUtil.repr(self, ignore=self.ignore_properties)

    def __str__(self):
        return ObjectUtil.repr(self, ignore=self.ignore_properties)

    def vars(self, ignore=None):
        return ObjectUtil.vars(self, ignore or self.ignore_properties, style='camel')

    def with_dict(self, **kw):
        return ObjectUtil.update_with_dict(self, **kw, ignore=('_sa_instance_state',), is_snake=True)
