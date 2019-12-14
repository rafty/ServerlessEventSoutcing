# -*- coding: utf-8 -*-
import decimal
import logging
from boto3.dynamodb.types import TypeDeserializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""
DynamoDB Streams Record to dict
"""


class DynamoDBStreamsRecord:
    def __init__(self, record):
        try:
            self.region = record['awsRegion']
            self.source = record['eventSource']
            self.event_type = record['eventName']
            self._image = record['dynamodb'].get('NewImage')
            self.source_table = record['eventSourceARN'].split('/')[1]
            self.raw = record
        except KeyError as e:
            logger.exception(e, extra={'record': record})
            raise e

    @property
    def image(self):
        """deserialized data"""
        des = {}
        if self._image:
            for key in self._image:
                des[key] = TypeDeserializer().deserialize(self._image[key])
        n = 0
        des = self.__decimal_to_integer_or_float(n, **des)
        logger.info('deserialized: {}'.format(des))
        return des

    def __decimal_to_integer_or_float(self, n, **kwargs):
        if n > 10:
            # limit of Recursive function
            raise ValueError
        n += 1
        for key in kwargs.keys():
            if isinstance(kwargs[key], dict):
                kwargs[key] = \
                    self._decimal_to_integer_or_float(n, **kwargs[key])
            elif isinstance(kwargs[key], decimal.Decimal):
                if kwargs[key] % 1 == 0:  # in case int
                    kwargs[key] = int(kwargs[key])
                else:  # in case float
                    kwargs[key] = float(kwargs[key])
        return kwargs
