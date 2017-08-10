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

    def load_body(self):
        decoded_body = self.body
        return json.loads(decoded_body or '{}')

    def error(self, type_, message='', status=400):
        headers = self.response_headers
        headers['status'] = status
        return json.dumps({'__type': type_, 'message': message}), headers,

    def delete_rule(self):
        body = self.load_body()
        name = body.get('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')
        events_backend.delete_rule(name)

        return '', self.response_headers

    def describe_rule(self):
        body = self.load_body()
        name = body.get('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        rule = events_backend.describe_rule(name)

        if not rule:
            return self.error('ResourceNotFoundException', 'Rule test does not exist.')

        rule_dict = self._generate_rule_dict(rule)
        return json.dumps(rule_dict), self.response_headers

    def disable_rule(self):
        body = self.load_body()
        name = body.get('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        if not events_backend.disable_rule(name):
            return self.error('ResourceNotFoundException', 'Rule ' + name + ' does not exist.')

        return '', self.response_headers

    def enable_rule(self):
        body = self.load_body()
        name = body.get('Name')

        if not name:
            return self.error('ValidationException', 'Parameter Name is required.')

        if not events_backend.enable_rule(name):
            return self.error('ResourceNotFoundException', 'Rule ' + name + ' does not exist.')

        return '', self.response_headers

    def generate_presigned_url(self):
        pass

    def list_rule_names_by_target(self):
        body = self.load_body()
        target_arn = body.get('TargetArn')
        next_token = body.get('NextToken')
        limit = body.get('Limit')

        if not target_arn:
            return self.error('ValidationException', 'Parameter TargetArn is required.')

        rule_names = events_backend.list_rule_names_by_target(
            target_arn, next_token, limit)

        return json.dumps(rule_names), self.response_headers

    def list_rules(self):
        body = self.load_body()
        prefix = body.get('NamePrefix')
        next_token = body.get('NextToken')
        limit = body.get('Limit')

        rules = events_backend.list_rules(prefix, next_token, limit)
        rules_obj = {'Rules': []}

        for rule in rules['Rules']:
            rules_obj['Rules'].append(self._generate_rule_dict(rule))

        if rules.get('NextToken'):
            rules_obj['NextToken'] = rules['NextToken']

        return json.dumps(rules_obj), self.response_headers

    def list_targets_by_rule(self):
        body = self.load_body()
        rule_name = body.get('Rule')
        next_token = body.get('NextToken')
        limit = body.get('Limit')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        try:
            targets = events_backend.list_targets_by_rule(
                rule_name, next_token, limit)
        except KeyError:
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return json.dumps(targets), self.response_headers

    def put_events(self):
        return '', self.response_headers

    def put_rule(self):
        body = self.load_body()
        name = body.get('Name')
        event_pattern = body.get('EventPattern')
        sched_exp = body.get('ScheduleExpression')

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
            State=body.get('State'),
            Description=body.get('Description'),
            RoleArn=body.get('RoleArn')
        )

        return json.dumps({'RuleArn': rule_arn}), self.response_headers

    def put_targets(self):
        body = self.load_body()
        rule_name = body.get('Rule')
        targets = body.get('Targets')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        if not targets:
            return self.error('ValidationException', 'Parameter Targets is required.')

        if not events_backend.put_targets(rule_name, targets):
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return '', self.response_headers

    def remove_targets(self):
        body = self.load_body()
        rule_name = body.get('Rule')
        ids = body.get('Ids')

        if not rule_name:
            return self.error('ValidationException', 'Parameter Rule is required.')

        if not ids:
            return self.error('ValidationException', 'Parameter Ids is required.')

        if not events_backend.remove_targets(rule_name, ids):
            return self.error('ResourceNotFoundException', 'Rule ' + rule_name + ' does not exist.')

        return '', self.response_headers

    def test_event_pattern(self):
        pass
