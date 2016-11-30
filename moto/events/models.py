from moto.core import BaseBackend


class EventsBackend(BaseBackend):

    def __init__(self):
        self.events = {}
        self.rules = {}

    def can_paginate(self):
        pass

    def delete_rule(self):
        pass

    def describe_rule(self, name):
        event = self.events['name']

    def disable_rule(self):
        pass

    def enable_rule(self):
        pass

    def generate_presigned_url(self):
        pass

    def get_paginator(self):
        pass

    def get_waiter(self):
        pass

    def list_rule_names_by_target(self):
        pass

    def list_rules(self):
        pass

    def list_targets_by_rule(self):
        pass

    def put_events(self):
        pass

    def put_rule(self, name, **kwargs):
        pass

    def put_targets(self):
        pass

    def remove_targets(self):
        pass

    def test_event_pattern(self):
        pass

events_backend = EventsBackend()
