import json

from moto.core.responses import BaseResponse


class EventsHandler(BaseResponse):

    def error(self, type_, message='', status=400):
        return status, self.response_headers, json.dumps({'__type': type_, 'message': message})

    def can_paginate(self):
        pass

    def delete_rule(self):
        pass

    def describe_rule(self):
        pass

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

    def put_rule(self):
        if 'Name' not in self.body:
            return self.error('ValidationException', 'Parameter Name is required.')
        pass

    def put_targets(self):
        pass

    def remove_targets(self):
        pass

    def test_event_pattern(self):
        pass
