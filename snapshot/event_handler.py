# -*- coding: utf-8 -*-
from model import Snapshot, DeduplicateEvent


class EventHandler:

    def __init__(self, event):
        self.snapshot = Snapshot(event)
        self.deduplication = DeduplicateEvent(event)
        self.event = event

    def update(self):

        if self.deduplication.is_duplicate_event():
            return

        self.snapshot.update()
