# -*- coding: utf-8 -*-
from contextlib import contextmanager
from botocore.exceptions import ClientError
from pynamodb.exceptions import (
    PutError,
    QueryError)
import logging
from error import ItemDoesNotExist, IntegrityError


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def is_conditional_check_failed(e):
    """ConditionalCheckFailedException or not"""
    if isinstance(e.cause, ClientError):
        code = e.cause.response['Error'].get('Code')
        if code == 'ConditionalCheckFailedException':
            return True
    return False


@contextmanager
def raise_for_save_exception(event_id=None):
    try:
        yield
    except PutError as e:
        if is_conditional_check_failed(e):
            message = 'ConditionalCheckFailedException: id={}'.format(event_id)
            raise IntegrityError(message)
        else:
            message = 'PutError: {}'.format(e)
            logger.exception(message)


@contextmanager
def raise_for_query_exception(event_id=None):
    try:
        yield
    except QueryError as e:
        error_message = 'QueryError: {}'.format(e)
        logger.exception(error_message)
        raise e
    except StopIteration as e:
        error_message = 'get_latest_item() no event: ' \
                        '{}'.format(event_id)
        logging.warning(error_message)
        raise ItemDoesNotExist(error_message)


@contextmanager
def raise_with_no_snapshot_exception(event_id=None):
    try:
        yield
    except IndexError as e:
        error_message = 'item not exist: id={}'.format(event_id)
        logger.warning(error_message)
        raise e
    except PutError as e:
        if is_conditional_check_failed(e):
            message = 'ConditionalCheckFailedException: id={}'.format(event_id)
            logger.warning(message)
            raise IntegrityError
        else:
            message = 'PutError: {}'.format(e)
            logger.exception(message)
