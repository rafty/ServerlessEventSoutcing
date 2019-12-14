# -*- coding: utf-8 -*-
import os
import json
import uuid
import datetime
import logging
import boto3
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()

lmbd = boto3.client('lambda')

# environment variable
EVENT_FUNCTION = os.environ['EVENT_FUNCTION']


def base_event(data):
    event = dict(
        item_id=str(data['item_id']).zfill(8),
        event_type=data['event_type'],
        name='Product {}'.format(data['item_id']),
        quantity=data['quantity'],
        fired_at=str(datetime.datetime.utcnow())
    )
    if data['event_type'] != 'stock_add':
        event['order_id'] = str(uuid.uuid4())

    event['event_id'] = data.get('event_id', str(uuid.uuid4()))

    return event


events1 = [
    dict(item_id=1, event_type='stock_add', quantity=20),
]


def make_duplication_events():
    event_id = str(uuid.uuid4())
    _events = list()
    for _ in range(3):
        _events.append(dict(item_id=1, event_type='item_reserve', quantity=1, event_id=event_id))
    _events.append(dict(item_id=1, event_type='item_reserve_complete', quantity=1))
    return _events


events3 = [
    dict(item_id=1, event_type='item_reserve', quantity=3),
    dict(item_id=1, event_type='item_reserve_complete', quantity=3)
]

events4 = [
    dict(item_id=1, event_type='item_reserve', quantity=5),
    dict(item_id=1, event_type='item_reserve_cancel', quantity=5)
]

events5 = [
    dict(item_id=1, event_type='item_reserve', quantity=5),
    dict(item_id=1, event_type='item_reserve_complete', quantity=5)
]


def lambda_handler(event, context):
    events2 = make_duplication_events()
    events = events1 + events2 + events3 + events4 + events5

    for e in map(base_event, events):
        lmbd.invoke(
            FunctionName=EVENT_FUNCTION,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps(e))
