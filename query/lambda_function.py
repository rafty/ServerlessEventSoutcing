# -*- coding: utf-8 -*-
import json
import logging
from handler import Handler
from aws_xray_sdk.core import patch_all

logger = logging.getLogger()
logger.setLevel(logging.INFO)
patch_all()

'''
クエリ文字列
'''


def extract_event(event):
    """
    'path': '/inventory',
    'httpMethod': 'GET',
    'queryStringParameters': {'item_id': '00000001'},
    """
    return dict(
        path=event['path'],
        http_method=event['httpMethod'],
        item_id=event['queryStringParameters']['item_id']
    )


def controller(request):
    try:
        handler = Handler(request)
        return handler.apply()

    except Exception as e:
        logger.exception('GET: Inventories Exception: {}'.format(e))
        raise e


def lambda_handler(event, context):
    logger.info('GET: Inventories: {}'.format(event))
    request = extract_event(event)
    logger.info('GET: Inventories - request{}'.format(request))
    response = controller(request)
    return {
        'statusCode': 200,
        "headers": {"Content-Type": "text/html"},
        'body': json.dumps(response)
    }
