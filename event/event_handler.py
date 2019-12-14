# -*- coding: utf-8 -*-
import logging
from functools import reduce
from retrying import retry
from model import EventStore, Snapshot
from error import ItemRanShort, IntegrityError
from retry_handler import is_integrity_error, is_not_item_ran_short

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class EventHandler:

    def __init__(self, event):
        self.__event = event
        self.__es = EventStore(event)
        self.__ss = Snapshot(event)

    def apply(self):
        handler = getattr(self, '_{}'.format(self.event_type), None)
        if handler:
            return handler()
        return None

    def _reserve(self):
        self.__persist_with_check_stock()

    def _add(self):
        self.__persist_with_optimistic_lock()

    def _complete(self):
        self.__persist_with_optimistic_lock()

    def _cancel(self):
        self.__persist_with_optimistic_lock()

    @retry(wait_exponential_multiplier=100,
           wait_exponential_max=1000,
           retry_on_exception=is_integrity_error)
    def __persist_with_optimistic_lock(self):
        latest_event = self.__es.get_latest_event()
        self.__es.persist(latest_event['version'])

    @retry(wait_exponential_multiplier=100,
           wait_exponential_max=1000,
           retry_on_exception=is_not_item_ran_short)
    def __persist_with_check_stock(self):
        state, current_version = self.__get_latest_state()
        if self.__is_item_available(state):
            self.__es.persist(current_version)
        else:
            raise ItemRanShort

    def __get_latest_state(self):
        snapshot = self.__ss.get_snapshot()
        events = self.__es.get_events_from(snapshot['from_version'])

        if len(events):
            state = reduce(self.__ss.calculate_state,
                           events,
                           self.__ss.get_state(snapshot))
            current_version = events[-1]['version']
            return state, current_version
        else:
            return snapshot['state'], snapshot['from_version']

    def __is_item_available(self, state):
        if state['available'] >= self.__event['quantity']:
            return True
        else:
            return False

    @property
    def event_type(self):
        keys = self.__event['event_type'].lower().split('_')
        return keys[-1]
