#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import Session, SQLModel, create_engine

from app.utils import ObjectUtil
from . import config


engine = create_engine(config.DATABASE_URI)

SQLModel.metadata.create_all(engine)


# Dependency
def get_db():
    db = Session(engine)
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
