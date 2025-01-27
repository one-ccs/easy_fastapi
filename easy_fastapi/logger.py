#!/usr/bin/env python
# -*- coding: utf-8 -*-
from easy_pyoc import Logger


logger = Logger(name='easy_fastapi', fmt='%(levelname)-8s : %(message)s')
uvicorn_logger = Logger(name='uvicorn.logging', fmt=None)
