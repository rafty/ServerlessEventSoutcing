# -*- coding: utf-8 -*-
import datetime
import logging
from functools import reduce
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    JSONAttribute
)
from exception_handler import (
    raise_for_save_exception,
    raise_for_query_exception,
    raise_with_no_snapshot_exception)
from error import ItemDoesNotExist, IntegrityError
from retrying import retry
from retry_handler import is_integrity_error

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# --------------------------
# snapshot Table
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
        splited = event['event_type'].lower().split('_')
        return splited[-1]


class Snapshot:

    __snapshot_suffix = '-snapshot'
    __initial_snapshot_form = {
        'item_id': '-snapshot',
        'version': 0,
        'name': '',
        'from_version': 0,
        'state': {
            'available': 0,
            'reserved': 0,
            'bought': 0
        },
        'saved_at': ''
    }

    def __init__(self, event):
        self.__event = event
        self.__model = SnapshotModel
        self.__state = State()
        self.__current_snapshot = {}

    @retry(wait_exponential_multiplier=100,
           wait_exponential_max=1000,
           retry_on_exception=is_integrity_error)
    def update(self):
        self.__get_current_snapshot()
        next_snapshot = self.__get_next_snapshot()
        self.__persist(next_snapshot)
        return

    def __get_current_snapshot(self):
        try:
            snapshot_item_id = self.item_id
            with raise_for_query_exception(snapshot_item_id):
                snapshot = self.__model.query(
                    snapshot_item_id,
                    self.__model.version > 0,
                    limit=1,
                    scan_index_forward=False).next()
                self.current_snapshot = snapshot.attribute_values

        except ItemDoesNotExist:
            self.current_snapshot = self.initial_snapshot

    def __persist(self, next_snapshot):
        snapshot = self.__model(**next_snapshot)
        logger.info('__persist: {}'.format(snapshot.attribute_values))
        with raise_with_no_snapshot_exception(snapshot.item_id):
            snapshot.save(
                condition=(self.__model.item_id != snapshot.item_id) &
                          (self.__model.version != snapshot.version)
            )

    def __get_next_snapshot(self):
        logger.info('__get_next_snapshot: {}'.format(self.current_snapshot))
        next_snapshot = self.current_snapshot
        next_snapshot['version'] += 1
        next_snapshot['from_version'] = self.__event['version']
        next_snapshot['saved_at'] = str(datetime.datetime.utcnow())
        next_snapshot['state'] = reduce(self.__calculate_state,
                                        [self.__event],
                                        self.current_snapshot['state'])
        return next_snapshot

    def __calculate_state(self, current_state, next_event):
        return self.__state.apply(current_state, next_event)

    @property
    def initial_snapshot(self):
        initial_snapshot = self.__initial_snapshot_form
        initial_snapshot['item_id'] = self.item_id
        initial_snapshot['name'] = self.__event['name']
        return initial_snapshot

    @property
    def item_id(self):
        return self.__event['item_id'] + self.__snapshot_suffix


# --------------------------
# snapshot Table
# --------------------------
class DeduplicateEventModel(Model):
    class Meta:
        table_name = 'EventStore'
        region = 'ap-northeast-1'
        max_retry_attempts = 8
        base_backoff_ms = 297

    item_id = UnicodeAttribute(hash_key=True)
    version = NumberAttribute(range_key=True)


class DeduplicateEvent:

    __item_suffix = '-deduplication'

    def __init__(self, event):
        self.model = DeduplicateEventModel
        self.event = event

    def is_duplicate_event(self):
        try:
            deduplicate = self.model(
                self.event['event_id'] + self.__item_suffix,
                0)
            with raise_for_save_exception(self.event['event_id']):
                deduplicate.save(
                    condition=(self.model.item_id != self.event_id) &
                              (self.model.version != 0)
                )
            return False
        except IntegrityError:
            logger.info('is_duplicate_event: {}'.format(self.event))
            return True

    @property
    def event_id(self):
        return self.event['event_id'] + self.__item_suffix
