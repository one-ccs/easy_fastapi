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
