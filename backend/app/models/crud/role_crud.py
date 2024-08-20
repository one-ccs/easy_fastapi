#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlalchemy.orm import Session

from app import models, schemas


def get_roles(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Role).offset(skip).limit(limit).all()


def create_user_role(db: Session, role: schemas.RoleCreate, user_id: int):
    db_role = models.Role(**role.model_dump(), owner_id=user_id)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role
