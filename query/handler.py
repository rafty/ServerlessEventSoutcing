# -*- coding: utf-8 -*-
import logging
from functools import reduce
from model import EventStore, Snapshot

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class Handler:

    def __init__(self, request):
        self.__request = request
        self.__es = EventStore(request)
        self.__ss = Snapshot(request)

    def apply(self):
        handler = getattr(self, '_{}'.format(self.request_type), None)
        if handler:
            return handler()
        return None

    def _get(self):
        snapshot = self.__ss.get_snapshot()
        events = self.__es.get_events_from(snapshot['from_version'])

        if len(events):
            snapshot['state'] = reduce(self.__ss.calculate_state,
                                       events,
                                       self.__ss.get_state(snapshot))
        return {
            'item_id': snapshot['item_id'],
            'name': snapshot['name'],
            'state': snapshot['state'],
        }

    @property
    def request_type(self):
        keys = self.__request['http_method'].lower().split('_')
        return keys[-1]
