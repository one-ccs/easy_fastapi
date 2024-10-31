#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from logging import (
    CRITICAL as CRITICAL,
    FATAL as FATAL,
    ERROR as ERROR,
    WARNING as WARNING,
    WARN as WARN,
    INFO as INFO,
    DEBUG as DEBUG,
    NOTSET as NOTSET,
)

logger = logging.getLogger('easy_fastapi')
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)7s : %(message)s'))

logger.addHandler(handler)
