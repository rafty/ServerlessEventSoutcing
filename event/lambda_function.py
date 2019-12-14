# -*- coding: utf-8 -*-
import logging
from error import ItemRanShort
from event_handler import EventHandler
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()


def extract_event(event):
    return event


def publish(event):
    """
    dummy function
    notify to the client
    """
    pass
    logger.info('publish RanShort - Item: {}'.format(event['item_id']))


def event_controller(event):
    try:
        handler = EventHandler(event)
        handler.apply()
        return None
    except ItemRanShort as e:
        """
        AWS Stepfunctionsの場合、CustomErrorをraiseする
        raise e
        または
        AWS AppSyncなどでErrorをpublish()するなど
        """
        publish(event)
        return None
    except Exception as e:
        logger.exception('Event Save Exception: {}'.format(e))
        raise e


def lambda_handler(event, context):
    event = extract_event(event)
    logger.info('EVENT Inventory: {}'.format(event))
    event_controller(event)
    return
