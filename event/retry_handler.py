# -*- coding: utf-8 -*-
from error import ItemRanShort, IntegrityError


def is_integrity_error(e):
    return isinstance(e, IntegrityError)


def is_not_item_ran_short(e):
    return isinstance(e, IntegrityError)
