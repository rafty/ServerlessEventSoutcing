# -*- coding: utf-8 -*-
import logging
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    JSONAttribute
)
from exception_handler import raise_for_query_exception
from error import ItemDoesNotExist


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# --------------------------
# Event Store Model
# --------------------------
class EventStoreModel(Model):
    class Meta:
        table_name = 'EventStore'
        region = 'ap-northeast-1'
        max_retry_attempts = 8
        base_backoff_ms = 297

    item_id = UnicodeAttribute(hash_key=True)
    version = NumberAttribute(range_key=True)
    event_id = UnicodeAttribute()
    event_type = UnicodeAttribute()
    name = UnicodeAttribute()
    quantity = NumberAttribute()
    fired_at = UnicodeAttribute()
    saved_at = UnicodeAttribute()
    order_id = UnicodeAttribute(null=True)


class EventStore:

    __initial_event = {
          "item_id": '',
          "version": 0,
          "event_id": '',
          "event_type": '',
          "name": '',
          "quantity": 0,
          "fired_at": '',
          "order_id": ''
        }

    def __init__(self, request):
        self.__request = request
        self.__model = EventStoreModel

    def get_events_from(self, from_version):
        # 強整合性
        with raise_for_query_exception(self.__request['item_id']):
            event_list = list()
            for event in self.__model.query(
                    self.__request['item_id'],
                    self.__model.version > from_version,
                    consistent_read=True,
                    scan_index_forward=False):
                event_list.append(event.attribute_values)
            event_list.reverse()
            return event_list

    def __query_latest_event(self):
        with raise_for_query_exception(self.__request['item_id']):
            event = self.__model.query(self.__request['item_id'],
                                       self.__model.version > 0,
                                       limit=1,
                                       scan_index_forward=False).next()
            return event

    def __get_initial_event(self):
        initial_event = self.__initial_event
        initial_event['item_id'] = self.__request['item_id']
        return initial_event


# --------------------------
# Snapshot Model
# --------------------------
class SnapshotModel(Model):
    class Meta:
        table_name = 'EventStore'
        region = 'ap-northeast-1'
        max_retry_attempts = 8
        base_backoff_ms = 297

    item_id = UnicodeAttribute(hash_key=True)
    version = NumberAttribute(range_key=True)
    from_version = NumberAttribute()
    name = UnicodeAttribute()
    state = JSONAttribute()
    saved_at = UnicodeAttribute()
    order_id = UnicodeAttribute(null=True)


class State:

    __initial_state = {
        'available': 0,
        'reserved': 0,
        'bought': 0
    }

    def __init__(self):
        pass

    def apply(self, current_state, next_event):
        event_type = self.__get_event_type(next_event)
        handler = getattr(self, '_on_{}'.format(event_type))
        if handler:
            return handler(current_state, next_event)
        return self.__initial_state

    @staticmethod
    def _on_add(state, event):
        state['available'] += event['quantity']
        return state

    @staticmethod
    def _on_reserve(state, event):
        state['available'] -= event['quantity']
        state['reserved'] += event['quantity']
        return state

    @staticmethod
    def _on_complete(state, event):
        state['reserved'] -= event['quantity']
        state['bought'] += event['quantity']
        return state

    @staticmethod
    def _on_cancel(state, event):
        state['available'] += event['quantity']
        state['reserved'] -= event['quantity']
        return state

    @staticmethod
    def __get_event_type(event):
        logger.info('_get_event_type: {}'.format(event))
        splited = event['event_type'].lower().split('_')
        return splited[-1]


class Snapshot:

    __snapshot_suffix = '-snapshot'
    __initial_snapshot = {
        'item_id': '',
        'version': 0,
        'event_id': '',
        'event_type': '',
        'name': '',
        'from_version': 0,
        'state': {
            'available': 0,
            'reserved': 0,
            'bought': 0
        },
        'saved_at': ''
    }

    def __init__(self, request):
        self.__request = request
        self.__model = SnapshotModel
        self.__state = State()

    def get_snapshot(self):
        try:
            snapshot = self.__get_latest_snapshot()
            item = snapshot.attribute_values
            item['item_id'] = item['item_id'].rstrip(self.__snapshot_suffix)
            return item
        except ItemDoesNotExist:
            logger.warning('No Snapshot')
            return self.__get_initial_snapshot()

    def calculate_state(self, current_state, next_event):
        return self.__state.apply(current_state, next_event)

    @staticmethod
    def get_state(snapshot):
        return snapshot['state']

    def __get_latest_snapshot(self):
        with raise_for_query_exception(self.__request['item_id']):
            snapshot_item_id = self.__request[
                                   'item_id'] + self.__snapshot_suffix
            snapshot = self.__model.query(snapshot_item_id,
                                          self.__model.version > 0,
                                          limit=1,
                                          scan_index_forward=False).next()
        return snapshot

    def __get_initial_snapshot(self):
        initial_snapshot = self.__initial_snapshot
        initial_snapshot['item_id'] = self.__request['item_id']
        return initial_snapshot
