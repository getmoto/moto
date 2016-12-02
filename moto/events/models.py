import os
import re
from collections import OrderedDict

from moto.core import BaseBackend


class Rule(object):

    def _generate_arn(self, name):
        return 'arn:aws:events:us-west-2:111111111111:rule/' + name

    def __init__(self, name, **kwargs):
        self.name = name
        self.arn = kwargs.get('Arn') or self._generate_arn(name)
        self.event_pattern = kwargs.get('EventPattern')
        self.schedule_exp = kwargs.get('ScheduleExpression')
        self.state = kwargs.get('State') or 'ENABLED'
        self.description = kwargs.get('Description')
        self.role_arn = kwargs.get('RoleArn')
        self.targets = {}

    def enable(self):
        self.state = 'ENABLED'

    def disable(self):
        self.state = 'DISABLED'

    def put_targets(self, targets):
        # Not testing for valid ARNs.
        for target in targets:
            self.targets[target['Id']] = target

    def remove_targets(self, ids):
        for target in ids:
            if target in self.targets:
                self.targets.pop(target)


class EventsBackend(BaseBackend):

    def __init__(self):
        self.rules = OrderedDict()
        self.next_tokens = {}

    def _gen_next_token(self, index):
        token = os.urandom(128).encode('base64')
        self.next_tokens[token] = index
        return token

    def _process_token_and_limits(self, array_len, next_token=None, limit=None):
        start_index = 0
        end_index = array_len
        new_next_token = None

        if next_token:
            start_index = self.next_tokens.pop(next_token, 0)

        if limit is not None:
            new_end_index = start_index + int(limit)
            if new_end_index < end_index:
                end_index = new_end_index
                new_next_token = self._gen_next_token(end_index)

        return start_index, end_index, new_next_token

    def delete_rule(self, name):
        return self.rules.pop(name) is not None

    def describe_rule(self, name):
        return self.rules.get(name)

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
            for target in rule.targets:
                if rule.targets[target]['Arn'] == target_arn:
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
        rule = self.rules.get(name)

        if rule:
            rule.put_targets(targets)
            return True

        return False

    def remove_targets(self, name, ids):
        rule = self.rules.get(name)

        if rule:
            rule.remove_targets(ids)
            return True

        return False

    def test_event_pattern(self):
        raise NotImplementedError()

events_backend = EventsBackend()
