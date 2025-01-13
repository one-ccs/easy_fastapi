#!/usr/bin/env python
# -*- coding: utf-8 -*-
from logging import getLogger, ERROR

from easy_pyoc import Logger


logger = Logger(name='easy_fastapi', formatter='%(message)s')
uvicorn_logger = getLogger('uvicorn.logging')
