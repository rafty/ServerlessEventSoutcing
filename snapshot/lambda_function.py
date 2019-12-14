# -*- coding: utf-8 -*-
import logging
from aws_xray_sdk.core import patch_all
from event_handler import EventHandler
from dynamodb_stream_derecord import DynamoDBStreamsRecord

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()


def extract_event(event):
    stream_record = DynamoDBStreamsRecord(event['Records'][0])
    record = stream_record.image
    logger.info('Stream Deserialze: {}'.format(record))
    return record


def is_insert_event(event):
    # INSERT | MODIFY | REMOVE
    return True if event['Records'][0]['eventName'] == 'INSERT' else False


def is_snapshot_event(event):
    return True if event['item_id'].endswith('-snapshot') else False


def is_deduplication_event(event):
    return True if event['item_id'].endswith('-deduplication') else False


def filtering_event(event):
    if not is_insert_event(event):
        return None
    event = extract_event(event)
    if is_snapshot_event(event):
        return None
    if is_deduplication_event(event):
        return None
    return event


def snapshot_controller(event):
    try:
        handler = EventHandler(event)
        handler.update()
        return
    except Exception as e:
        logger.exception('Event Save Exception: {}'.format(e))
        raise e


def lambda_handler(event, context):
    event = filtering_event(event)
    if not event:
        return

    logger.info('######## SNAPSHOT Inventory: {}'.format(event))
    snapshot_controller(event)
    return
