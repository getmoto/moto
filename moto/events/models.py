import os
import re
import json

from moto.core.exceptions import JsonRESTError
from moto.core import BaseBackend, BaseModel


class Rule(BaseModel):

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
        self.targets = []

    def enable(self):
        self.state = 'ENABLED'

    def disable(self):
        self.state = 'DISABLED'

    # This song and dance for targets is because we need order for Limits and NextTokens, but can't use OrderedDicts
    # with Python 2.6, so tracking it with an array it is.
    def _check_target_exists(self, target_id):
        for i in range(0, len(self.targets)):
            if target_id == self.targets[i]['Id']:
                return i
        return None

    def put_targets(self, targets):
        # Not testing for valid ARNs.
        for target in targets:
            index = self._check_target_exists(target['Id'])
            if index is not None:
                self.targets[index] = target
            else:
                self.targets.append(target)

    def remove_targets(self, ids):
        for target_id in ids:
            index = self._check_target_exists(target_id)
            if index is not None:
                self.targets.pop(index)


class EventsBackend(BaseBackend):
    ACCOUNT_ID = re.compile(r'^(\d{1,12}|\*)$')
    STATEMENT_ID = re.compile(r'^[a-zA-Z0-9-_]{1,64}$')

    def __init__(self):
        self.rules = {}
        # This array tracks the order in which the rules have been added, since
        # 2.6 doesn't have OrderedDicts.
        self.rules_order = []
        self.next_tokens = {}

        self.permissions = {}

    def _get_rule_by_index(self, i):
        return self.rules.get(self.rules_order[i])

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
        self.rules_order.pop(self.rules_order.index(name))
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

    def list_rule_names_by_target(self, target_arn, next_token=None, limit=None):
        matching_rules = []
        return_obj = {}

        start_index, end_index, new_next_token = self._process_token_and_limits(
            len(self.rules), next_token, limit)

        for i in range(start_index, end_index):
            rule = self._get_rule_by_index(i)
            for target in rule.targets:
                if target['Arn'] == target_arn:
                    matching_rules.append(rule.name)

        return_obj['RuleNames'] = matching_rules
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def list_rules(self, prefix=None, next_token=None, limit=None):
        match_string = '.*'
        if prefix is not None:
            match_string = '^' + prefix + match_string

        match_regex = re.compile(match_string)

        matching_rules = []
        return_obj = {}

        start_index, end_index, new_next_token = self._process_token_and_limits(
            len(self.rules), next_token, limit)

        for i in range(start_index, end_index):
            rule = self._get_rule_by_index(i)
            if match_regex.match(rule.name):
                matching_rules.append(rule)

        return_obj['Rules'] = matching_rules
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def list_targets_by_rule(self, rule, next_token=None, limit=None):
        # We'll let a KeyError exception be thrown for response to handle if
        # rule doesn't exist.
        rule = self.rules[rule]

        start_index, end_index, new_next_token = self._process_token_and_limits(
            len(rule.targets), next_token, limit)

        returned_targets = []
        return_obj = {}

        for i in range(start_index, end_index):
            returned_targets.append(rule.targets[i])

        return_obj['Targets'] = returned_targets
        if new_next_token is not None:
            return_obj['NextToken'] = new_next_token

        return return_obj

    def put_rule(self, name, **kwargs):
        rule = Rule(name, **kwargs)
        self.rules[rule.name] = rule
        self.rules_order.append(rule.name)
        return rule.arn

    def put_targets(self, name, targets):
        rule = self.rules.get(name)

        if rule:
            rule.put_targets(targets)
            return True

        return False

    def put_events(self, events):
        num_events = len(events)

        if num_events < 1:
            raise JsonRESTError('ValidationError', 'Need at least 1 event')
        elif num_events > 10:
            raise JsonRESTError('ValidationError', 'Can only submit 10 events at once')

        # We dont really need to store the events yet
        return []

    def remove_targets(self, name, ids):
        rule = self.rules.get(name)

        if rule:
            rule.remove_targets(ids)
            return True

        return False

    def test_event_pattern(self):
        raise NotImplementedError()

    def put_permission(self, action, principal, statement_id):
        if action is None or action != 'events:PutEvents':
            raise JsonRESTError('InvalidParameterValue', 'Action must be PutEvents')

        if principal is None or self.ACCOUNT_ID.match(principal) is None:
            raise JsonRESTError('InvalidParameterValue', 'Principal must match ^(\d{1,12}|\*)$')

        if statement_id is None or self.STATEMENT_ID.match(statement_id) is None:
            raise JsonRESTError('InvalidParameterValue', 'StatementId must match ^[a-zA-Z0-9-_]{1,64}$')

        self.permissions[statement_id] = {'action': action, 'principal': principal}

    def remove_permission(self, statement_id):
        try:
            del self.permissions[statement_id]
        except KeyError:
            raise JsonRESTError('ResourceNotFoundException', 'StatementId not found')

    def describe_event_bus(self):
        arn = "arn:aws:events:us-east-1:000000000000:event-bus/default"
        statements = []
        for statement_id, data in self.permissions.items():
            statements.append({
                'Sid': statement_id,
                'Effect': 'Allow',
                'Principal': {'AWS': 'arn:aws:iam::{0}:root'.format(data['principal'])},
                'Action': data['action'],
                'Resource': arn
            })
        policy = {'Version': '2012-10-17', 'Statement': statements}
        policy_json = json.dumps(policy)
        return {
            'Policy': policy_json,
            'Name': 'default',
            'Arn': arn
        }


events_backend = EventsBackend()
