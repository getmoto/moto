import json
import re

from moto.core.responses import BaseResponse
from moto.events import events_backend


class EventsHandler(BaseResponse):

    def _generate_rule_dict(self, rule):
        return {
            'Name': rule.name,
            'Arn': rule.arn,
            'EventPattern': rule.event_pattern,
            'State': rule.state,
            'Description': rule.description,
            'ScheduleExpression': rule.schedule_exp,
            'RoleArn': rule.role_arn
        }

    @property
    def request_params(self):
        if not hasattr(self, '_json_body'):
            try:
                self._json_body = json.loads(self.body)
            except ValueError:
                self._json_body = {}
        return self._json_body

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def error(self, type_, message='', status=400):
        headers = self.response_headers
        headers['status'] = status
        return json.dumps({'__type': type_, 'message': message}), headers,

    def delete_rule(self):
        name = self._get_param('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')
        events_backend.delete_rule(name)

        return '', self.response_headers

    def describe_rule(self):
        name = self._get_param('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        rule = events_backend.describe_rule(name)

        if not rule:
            return self.error('ResourceNotFoundException', 'Rule test does not exist.')

        rule_dict = self._generate_rule_dict(rule)
        return json.dumps(rule_dict), self.response_headers

    def disable_rule(self):
        name = self._get_param('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        if not events_backend.disable_rule(name):
            return self.error('ResourceNotFoundException', 'Rule ' + name + ' does not exist.')

        return '', self.response_headers

    def enable_rule(self):
        name = self._get_param('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        if not events_backend.enable_rule(name):
            return self.error('ResourceNotFoundException', 'Rule ' + name + ' does not exist.')

        return '', self.response_headers

    def generate_presigned_url(self):
        pass

    def list_rule_names_by_target(self):
        target_arn = self._get_param('TargetArn')
        next_token = self._get_param('NextToken')
        limit = self._get_param('Limit')

        if not target_arn:
            return self.error('ValidationException', 'Parameter TargetArn is required.')

        rule_names = events_backend.list_rule_names_by_target(
            target_arn, next_token, limit)

        return json.dumps(rule_names), self.response_headers

    def list_rules(self):
        prefix = self._get_param('NamePrefix')
        next_token = self._get_param('NextToken')
        limit = self._get_param('Limit')

        rules = events_backend.list_rules(prefix, next_token, limit)
        rules_obj = {'Rules': []}

        for rule in rules['Rules']:
            rules_obj['Rules'].append(self._generate_rule_dict(rule))

        if rules.get('NextToken'):
            rules_obj['NextToken'] = rules['NextToken']

        return json.dumps(rules_obj), self.response_headers

    def list_targets_by_rule(self):
        rule_name = self._get_param('Rule')
        next_token = self._get_param('NextToken')
        limit = self._get_param('Limit')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        try:
            targets = events_backend.list_targets_by_rule(
                rule_name, next_token, limit)
        except KeyError:
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return json.dumps(targets), self.response_headers

    def put_events(self):
        events = self._get_param('Entries')

        failed_entries = events_backend.put_events(events)

        if failed_entries:
            return json.dumps({
                'FailedEntryCount': len(failed_entries),
                'Entries': failed_entries
            })

        return '', self.response_headers

    def put_rule(self):
        name = self._get_param('Name')
        event_pattern = self._get_param('EventPattern')
        sched_exp = self._get_param('ScheduleExpression')
        state = self._get_param('State')
        desc = self._get_param('Description')
        role_arn = self._get_param('RoleArn')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        if event_pattern:
            try:
                json.loads(event_pattern)
            except ValueError:
                # Not quite as informative as the real error, but it'll work
                # for now.
                return self.error('InvalidEventPatternException', 'Event pattern is not valid.')

        if sched_exp:
            if not (re.match('^cron\(.*\)', sched_exp) or
                    re.match('^rate\(\d*\s(minute|minutes|hour|hours|day|days)\)', sched_exp)):
                return self.error('ValidationException', 'Parameter ScheduleExpression is not valid.')

        rule_arn = events_backend.put_rule(
            name,
            ScheduleExpression=sched_exp,
            EventPattern=event_pattern,
            State=state,
            Description=desc,
            RoleArn=role_arn
        )

        return json.dumps({'RuleArn': rule_arn}), self.response_headers

    def put_targets(self):
        rule_name = self._get_param('Rule')
        targets = self._get_param('Targets')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        if not targets:
            return self.error('ValidationException', 'Parameter Targets is required.')

        if not events_backend.put_targets(rule_name, targets):
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return '', self.response_headers

    def remove_targets(self):
        rule_name = self._get_param('Rule')
        ids = self._get_param('Ids')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        if not ids:
            return self.error('ValidationException', 'Parameter Ids is required.')

        if not events_backend.remove_targets(rule_name, ids):
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return '', self.response_headers

    def test_event_pattern(self):
        pass

    def put_permission(self):
        action = self._get_param('Action')
        principal = self._get_param('Principal')
        statement_id = self._get_param('StatementId')

        events_backend.put_permission(action, principal, statement_id)

        return ''

    def remove_permission(self):
        statement_id = self._get_param('StatementId')

        events_backend.remove_permission(statement_id)

        return ''

    def describe_event_bus(self):
        return json.dumps(events_backend.describe_event_bus())
