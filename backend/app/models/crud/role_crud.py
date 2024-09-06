#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import Session, select

from app import models, schemas


def get_roles(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.Role).offset(skip).limit(limit)
    return db.exec(statement).all()


def create_user_role(db: Session, role: schemas.RoleCreate, user_id: int):
    db_role = models.Role(**role.model_dump())
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role
