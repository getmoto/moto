from __future__ import unicode_literals

import datetime

from moto.core.utils import iso_8601_datetime_with_milliseconds
from ..exceptions import InvalidParameterCombination
from .base import BaseRDSBackend, BaseRDSModel


EVENT_MAP = {
    "DB_INSTANCE_BACKUP_START": {
        "Categories": ["backup"],
        "Message": "Backing up DB instance",
    },
    "DB_INSTANCE_BACKUP_FINISH": {
        "Categories": ["backup"],
        "Message": "Finished DB instance backup",
    },
    "DB_INSTANCE_CREATE": {
        "Categories": ["creation"],
        "Message": "DB instance created",
    },
    "DB_SNAPSHOT_CREATE_AUTOMATED_START": {
        "Categories": ["creation"],
        "Message": "Creating automated snapshot",
    },
    "DB_SNAPSHOT_CREATE_AUTOMATED_FINISH": {
        "Categories": ["creation"],
        "Message": "Automated snapshot created",
    },
    "DB_SNAPSHOT_CREATE_MANUAL_START": {
        "Categories": ["creation"],
        "Message": "Creating manual snapshot",
    },
    "DB_SNAPSHOT_CREATE_MANUAL_FINISH": {
        "Categories": ["creation"],
        "Message": "Manual snapshot created",
    },
}


class EventMixin(BaseRDSModel):
    @property
    def events(self):
        return self.backend.list_events_for_resource(self.arn)

    def add_event(self, event_type):
        self.backend.add_event(event_type, self)

    def delete_events(self):
        self.backend.delete_events(self.arn)


class Event(object):
    def __init__(self, event_type, resource):
        event_metadata = EVENT_MAP[event_type]
        self.source_identifier = resource.resource_id
        self.source_type = resource.event_source_type
        self.message = event_metadata["Message"]
        self.event_categories = event_metadata["Categories"]
        self.source_arn = resource.arn
        self.date = iso_8601_datetime_with_milliseconds(datetime.datetime.now())

    @property
    def resource_id(self):
        return "{}-{}-{}".format(self.source_identifier, self.source_type, self.date)


class EventBackend(BaseRDSBackend):
    def __init__(self):
        super(EventBackend, self).__init__()
        self.events = []

    def add_event(self, event_type, resource):
        event = Event(event_type, resource)
        self.events.append(event)

    def list_events_for_resource(self, arn):
        return [e for e in self.events if e.source_arn == arn]

    def describe_events(self, source_identifier=None, source_type=None, **kwargs):
        if source_identifier is not None and source_type is None:
            raise InvalidParameterCombination(
                "Cannot specify source identifier without source type"
            )
        events = self.events
        if source_identifier is not None:
            events = [e for e in events if e.source_identifier == source_identifier]
        if source_type is not None:
            events = [e for e in events if e.source_type == source_type]
        return events

    def delete_events(self, arn):
        self.events = [event for event in self.events if event.source_arn != arn]
