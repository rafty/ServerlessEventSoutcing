# -*- coding: utf-8 -*-
import logging
from error import IntegrityError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def is_integrity_error(e):
    return isinstance(e, IntegrityError)
