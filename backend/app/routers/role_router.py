#!/usr/bin/env python
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core import (
    TokenData,
    get_db,
    get_current_user,
)
from app.services import role_service
from app import schemas


role_router = APIRouter()
