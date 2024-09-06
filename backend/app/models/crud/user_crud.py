#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sqlmodel import Session, select, or_

from app.core import (
    encrypt_password,
)
from app import models, schemas


def get_user(db: Session, user_id: int):
    statement = select(models.User).where(models.User.id == user_id)
    return db.exec(statement).first()


def get_user_by_username(db: Session, username: str):
    statement = select(models.User).where(models.User.username == username)
    return db.exec(statement).first()


def get_user_by_email(db: Session, email: str):
    statement = select(models.User).where(models.User.email == email)
    return db.exec(statement).first()


def get_user_by_username_or_email(db: Session, username_or_email: str):
    statement = select(models.User).where(
        or_(
            models.User.username == username_or_email,
            models.User.email == username_or_email,
        ),
    )
    return db.exec(statement).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    statement = select(models.User).offset(skip).limit(limit)
    return db.exec(statement).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=encrypt_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
