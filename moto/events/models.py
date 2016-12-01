import binascii
import os
import re
from collections import OrderedDict

from moto.core import BaseBackend


class Rule(object):

    def _generate_arn(self, name):
        return 'arn:aws:events:us-west-2:111111111111:rule/' + name

    def __init__(self, name, **kwargs):
        self.name = name
        self.arn = kwargs['arn'] if 'arn' in kwargs else self._generate_arn(name)
        self.event_pattern = kwargs['event_pattern'] if 'event_pattern' in kwargs else None
        self.schedule_exp = kwargs['schedule_exp'] if 'schedule_exp' in kwargs else None
        self.state = kwargs['state'] if 'state' in kwargs else 'ENABLED'
        self.description = kwargs['description'] if 'description' in kwargs else None
        self.role_arn = kwargs['role_arn'] if 'role_arn' in kwargs else None
        self.targets = {}

    def enable(self):
        self.state = 'ENABLED'

    def disable(self):
        self.state = 'DISABLED'

    def put_targets(self, targets):
        # TODO: Will need to test for valid ARNs.
        for target in targets:
            self.targets[target['TargetId']] = target

    def remove_targets(self, ids):
        for target in ids:
            if target in self.targets:
                self.targets.pop(target)


class EventsBackend(BaseBackend):

    def __init__(self):
        self.rules = OrderedDict()
        self.next_tokens = {}

    def _gen_next_token(self, index):
        token = binascii.hexlify(os.urandom(16))
        self.next_tokens[token] = index
        return token

    def _process_token_and_limits(self, array_len, next_token=None, limit=None):
        start_index = 0
        end_index = array_len
        new_next_token = None

        if next_token is not None:
            if next_token in self.next_tokens:
                start_index = self.next_tokens[next_token]

        if limit is not None:
            new_end_index = start_index + int(limit)
            if new_end_index < end_index:
                end_index = new_end_index
                new_next_token = self._gen_next_token(end_index - 1)

        return start_index, end_index, new_next_token

    def delete_rule(self, name):
        return self.rules.pop(name) is not None

    def describe_rule(self, name):
        if name in self.rules:
            return self.rules[name]

        return None

    def disable_rule(self, name):
        if name in self.rules:
            self.rules[name].disable()
            return True

        return False

    def enable_rule(self, name):
        if name in self.rules:
            self.rules[name].enable()
            return True

        return False

    def generate_presigned_url(self):
        pass

    def list_rule_names_by_target(self, target_arn, next_token=None, limit=None):
        rules_array = self.rules.values()

        matching_rules = []
        return_obj = {}

        start_index, end_index, new_next_token = self._process_token_and_limits(len(rules_array), next_token, limit)

        for i in range(start_index, end_index):
            rule = rules_array[i]
            if target_arn in rule.targets:
                matching_rules.append(rule.name)

        return_obj['RuleNames'] = matching_rules
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def list_rules(self, prefix=None, next_token=None, limit=None):
        rules_array = self.rules.values()

        match_string = '.*'
        if prefix is not None:
            match_string = '^' + prefix + match_string

        match_regex = re.compile(match_string)

        matching_rules = []
        return_obj = {}

        start_index, end_index, new_next_token = self._process_token_and_limits(len(rules_array), next_token, limit)

        for i in range(start_index, end_index):
            rule = rules_array[i]
            if match_regex.match(rule.name):
                matching_rules.append(rule)

        return_obj['Rules'] = matching_rules
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def list_targets_by_rule(self, rule, next_token=None, limit=None):
        # We'll let a KeyError exception be thrown for response to handle if rule doesn't exist.
        targets = self.rules[rule].targets.values()

        start_index, end_index, new_next_token = self._process_token_and_limits(len(targets), next_token, limit)

        returned_targets = []
        return_obj = {}

        for i in range(start_index, end_index):
            returned_targets.append(targets[i])

        return_obj['Targets'] = returned_targets
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def put_events(self):
        # For the purposes of this mock, there is no backend action for putting an event.
        # Response module will deal with replying.
        pass

    def put_rule(self, name, **kwargs):
        rule = Rule(name, **kwargs)
        self.rules[rule.name] = rule
        return rule.arn

    def put_targets(self, name, targets):
        self.rules[name].put_targets(targets)

    def remove_targets(self, name, ids):
        self.rules[name].remove_targets(ids)

    def test_event_pattern(self):
        raise NotImplementedError()

events_backend = EventsBackend()
