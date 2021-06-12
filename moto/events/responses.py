import json
import re

from moto.core.responses import BaseResponse
from moto.events import events_backends


class EventsHandler(BaseResponse):
    @property
    def events_backend(self):
        """
        Events Backend

        :return: Events Backend object
        :rtype: moto.events.models.EventsBackend
        """
        return events_backends[self.region]

    def _generate_rule_dict(self, rule):
        return {
            "Name": rule.name,
            "Arn": rule.arn,
            "EventPattern": str(rule.event_pattern),
            "State": rule.state,
            "Description": rule.description,
            "ScheduleExpression": rule.schedule_exp,
            "RoleArn": rule.role_arn,
            "ManagedBy": rule.managed_by,
            "EventBusName": rule.event_bus_name,
            "CreatedBy": rule.created_by,
        }

    @property
    def request_params(self):
        if not hasattr(self, "_json_body"):
            try:
                self._json_body = json.loads(self.body)
            except ValueError:
                self._json_body = {}
        return self._json_body

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def error(self, type_, message="", status=400):
        headers = self.response_headers
        headers["status"] = status
        return json.dumps({"__type": type_, "message": message}), headers

    def delete_rule(self):
        name = self._get_param("Name")

        if not name:
            return self.error("ValidationException", "Parameter Name is required.")
        self.events_backend.delete_rule(name)

        return "", self.response_headers

    def describe_rule(self):
        name = self._get_param("Name")

        if not name:
            return self.error("ValidationException", "Parameter Name is required.")

        rule = self.events_backend.describe_rule(name)

        if not rule:
            return self.error(
                "ResourceNotFoundException", "Rule " + name + " does not exist."
            )

        rule_dict = self._generate_rule_dict(rule)
        return json.dumps(rule_dict), self.response_headers

    def disable_rule(self):
        name = self._get_param("Name")

        if not name:
            return self.error("ValidationException", "Parameter Name is required.")

        if not self.events_backend.disable_rule(name):
            return self.error(
                "ResourceNotFoundException", "Rule " + name + " does not exist."
            )

        return "", self.response_headers

    def enable_rule(self):
        name = self._get_param("Name")

        if not name:
            return self.error("ValidationException", "Parameter Name is required.")

        if not self.events_backend.enable_rule(name):
            return self.error(
                "ResourceNotFoundException", "Rule " + name + " does not exist."
            )

        return "", self.response_headers

    def generate_presigned_url(self):
        pass

    def list_rule_names_by_target(self):
        target_arn = self._get_param("TargetArn")
        next_token = self._get_param("NextToken")
        limit = self._get_param("Limit")

        if not target_arn:
            return self.error("ValidationException", "Parameter TargetArn is required.")

        rule_names = self.events_backend.list_rule_names_by_target(
            target_arn, next_token, limit
        )

        return json.dumps(rule_names), self.response_headers

    def list_rules(self):
        prefix = self._get_param("NamePrefix")
        next_token = self._get_param("NextToken")
        limit = self._get_param("Limit")

        rules = self.events_backend.list_rules(prefix, next_token, limit)
        rules_obj = {"Rules": []}

        for rule in rules["Rules"]:
            rules_obj["Rules"].append(self._generate_rule_dict(rule))

        if rules.get("NextToken"):
            rules_obj["NextToken"] = rules["NextToken"]

        return json.dumps(rules_obj), self.response_headers

    def list_targets_by_rule(self):
        rule_name = self._get_param("Rule")
        next_token = self._get_param("NextToken")
        limit = self._get_param("Limit")

        if not rule_name:
            return self.error("ValidationException", "Parameter Rule is required.")

        try:
            targets = self.events_backend.list_targets_by_rule(
                rule_name, next_token, limit
            )
        except KeyError:
            return self.error(
                "ResourceNotFoundException", "Rule " + rule_name + " does not exist."
            )

        return json.dumps(targets), self.response_headers

    def put_events(self):
        events = self._get_param("Entries")

        entries = self.events_backend.put_events(events)

        failed_count = len([e for e in entries if "ErrorCode" in e])
        response = {
            "FailedEntryCount": failed_count,
            "Entries": entries,
        }

        return json.dumps(response)

    def put_rule(self):
        name = self._get_param("Name")
        event_pattern = self._get_param("EventPattern")
        sched_exp = self._get_param("ScheduleExpression")
        state = self._get_param("State")
        desc = self._get_param("Description")
        role_arn = self._get_param("RoleArn")
        event_bus_name = self._get_param("EventBusName", "default")

        if event_pattern:
            try:
                json.loads(event_pattern)
            except ValueError:
                # Not quite as informative as the real error, but it'll work
                # for now.
                return self.error(
                    "InvalidEventPatternException", "Event pattern is not valid."
                )

        if sched_exp:
            if not (
                re.match(r"^cron\(.*\)", sched_exp)
                or re.match(
                    r"^rate\(\d*\s(minute|minutes|hour|hours|day|days)\)", sched_exp
                )
            ):
                return self.error(
                    "ValidationException", "Parameter ScheduleExpression is not valid."
                )

        rule = self.events_backend.put_rule(
            name,
            ScheduleExpression=sched_exp,
            EventPattern=event_pattern,
            State=state,
            Description=desc,
            RoleArn=role_arn,
            EventBusName=event_bus_name,
        )

        return json.dumps({"RuleArn": rule.arn}), self.response_headers

    def put_targets(self):
        rule_name = self._get_param("Rule")
        event_bus_name = self._get_param("EventBusName", "default")
        targets = self._get_param("Targets")

        self.events_backend.put_targets(rule_name, event_bus_name, targets)

        return (
            json.dumps({"FailedEntryCount": 0, "FailedEntries": []}),
            self.response_headers,
        )

    def remove_targets(self):
        rule_name = self._get_param("Rule")
        event_bus_name = self._get_param("EventBusName", "default")
        ids = self._get_param("Ids")

        self.events_backend.remove_targets(rule_name, event_bus_name, ids)

        return (
            json.dumps({"FailedEntryCount": 0, "FailedEntries": []}),
            self.response_headers,
        )

    def test_event_pattern(self):
        pass

    def put_permission(self):
        event_bus_name = self._get_param("EventBusName")
        action = self._get_param("Action")
        principal = self._get_param("Principal")
        statement_id = self._get_param("StatementId")

        self.events_backend.put_permission(
            event_bus_name, action, principal, statement_id
        )

        return ""

    def remove_permission(self):
        event_bus_name = self._get_param("EventBusName")
        statement_id = self._get_param("StatementId")

        self.events_backend.remove_permission(event_bus_name, statement_id)

        return ""

    def describe_event_bus(self):
        name = self._get_param("Name")

        event_bus = self.events_backend.describe_event_bus(name)
        response = {"Name": event_bus.name, "Arn": event_bus.arn}

        if event_bus.policy:
            response["Policy"] = event_bus.policy

        return json.dumps(response), self.response_headers

    def create_event_bus(self):
        name = self._get_param("Name")
        event_source_name = self._get_param("EventSourceName")

        event_bus = self.events_backend.create_event_bus(name, event_source_name)

        return json.dumps({"EventBusArn": event_bus.arn}), self.response_headers

    def list_event_buses(self):
        name_prefix = self._get_param("NamePrefix")
        # ToDo: add 'NextToken' & 'Limit' parameters

        response = []
        for event_bus in self.events_backend.list_event_buses(name_prefix):
            event_bus_response = {"Name": event_bus.name, "Arn": event_bus.arn}

            if event_bus.policy:
                event_bus_response["Policy"] = event_bus.policy

            response.append(event_bus_response)

        return json.dumps({"EventBuses": response}), self.response_headers

    def delete_event_bus(self):
        name = self._get_param("Name")

        self.events_backend.delete_event_bus(name)

        return "", self.response_headers

    def list_tags_for_resource(self):
        arn = self._get_param("ResourceARN")

        result = self.events_backend.list_tags_for_resource(arn)

        return json.dumps(result), self.response_headers

    def tag_resource(self):
        arn = self._get_param("ResourceARN")
        tags = self._get_param("Tags")

        result = self.events_backend.tag_resource(arn, tags)

        return json.dumps(result), self.response_headers

    def untag_resource(self):
        arn = self._get_param("ResourceARN")
        tags = self._get_param("TagKeys")

        result = self.events_backend.untag_resource(arn, tags)

        return json.dumps(result), self.response_headers

    def create_archive(self):
        name = self._get_param("ArchiveName")
        source_arn = self._get_param("EventSourceArn")
        description = self._get_param("Description")
        event_pattern = self._get_param("EventPattern")
        retention = self._get_param("RetentionDays")

        archive = self.events_backend.create_archive(
            name, source_arn, description, event_pattern, retention
        )

        return (
            json.dumps(
                {
                    "ArchiveArn": archive.arn,
                    "CreationTime": archive.creation_time,
                    "State": archive.state,
                }
            ),
            self.response_headers,
        )

    def describe_archive(self):
        name = self._get_param("ArchiveName")

        result = self.events_backend.describe_archive(name)

        return json.dumps(result), self.response_headers

    def list_archives(self):
        name_prefix = self._get_param("NamePrefix")
        source_arn = self._get_param("EventSourceArn")
        state = self._get_param("State")

        result = self.events_backend.list_archives(name_prefix, source_arn, state)

        return json.dumps({"Archives": result}), self.response_headers

    def update_archive(self):
        name = self._get_param("ArchiveName")
        description = self._get_param("Description")
        event_pattern = self._get_param("EventPattern")
        retention = self._get_param("RetentionDays")

        result = self.events_backend.update_archive(
            name, description, event_pattern, retention
        )

        return json.dumps(result), self.response_headers

    def delete_archive(self):
        name = self._get_param("ArchiveName")

        self.events_backend.delete_archive(name)

        return "", self.response_headers

    def start_replay(self):
        name = self._get_param("ReplayName")
        description = self._get_param("Description")
        source_arn = self._get_param("EventSourceArn")
        start_time = self._get_param("EventStartTime")
        end_time = self._get_param("EventEndTime")
        destination = self._get_param("Destination")

        result = self.events_backend.start_replay(
            name, description, source_arn, start_time, end_time, destination
        )

        return json.dumps(result), self.response_headers

    def describe_replay(self):
        name = self._get_param("ReplayName")

        result = self.events_backend.describe_replay(name)

        return json.dumps(result), self.response_headers

    def list_replays(self):
        name_prefix = self._get_param("NamePrefix")
        source_arn = self._get_param("EventSourceArn")
        state = self._get_param("State")

        result = self.events_backend.list_replays(name_prefix, source_arn, state)

        return json.dumps({"Replays": result}), self.response_headers

    def cancel_replay(self):
        name = self._get_param("ReplayName")

        result = self.events_backend.cancel_replay(name)

        return json.dumps(result), self.response_headers

    def create_connection(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        authorization_type = self._get_param("AuthorizationType")
        auth_parameters = self._get_param("AuthParameters")

        result = self.events_backend.create_connection(
            name, description, authorization_type, auth_parameters
        )

        return (
            json.dumps(
                {
                    "ConnectionArn": result.arn,
                    "ConnectionState": "AUTHORIZED",
                    "CreationTime": result.creation_time,
                    "LastModifiedTime": result.creation_time,
                }
            ),
            self.response_headers,
        )

    def list_connections(self):
        connections = self.events_backend.list_connections()
        result = []
        for connection in connections:
            result.append(
                {
                    "ConnectionArn": connection.arn,
                    "ConnectionState": "AUTHORIZED",
                    "CreationTime": connection.creation_time,
                    "LastModifiedTime": connection.creation_time,
                    "AuthorizationType": connection.authorization_type,
                }
            )

        return json.dumps({"Connections": result}), self.response_headers

    def create_api_destination(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        connection_arn = self._get_param("ConnectionArn")
        invocation_endpoint = self._get_param("InvocationEndpoint")
        http_method = self._get_param("HttpMethod")

        destination = self.events_backend.create_api_destination(
            name, description, connection_arn, invocation_endpoint, http_method
        )
        return (
            json.dumps(
                {
                    "ApiDestinationArn": destination.arn,
                    "ApiDestinationState": "ACTIVE",
                    "CreationTime": destination.creation_time,
                    "LastModifiedTime": destination.creation_time,
                }
            ),
            self.response_headers,
        )

    def list_api_destinations(self):
        destinations = self.events_backend.list_api_destinations()
        result = []
        for destination in destinations:
            result.append(
                {
                    "ApiDestinationArn": destination.arn,
                    "Name": destination.name,
                    "ApiDestinationState": destination.state,
                    "ConnectionArn": destination.connection_arn,
                    "InvocationEndpoint": destination.invocation_endpoint,
                    "HttpMethod": destination.http_method,
                    "CreationTime": destination.creation_time,
                    "LastModifiedTime": destination.creation_time,
                }
            )

        return json.dumps({"ApiDestinations": result}), self.response_headers

    def describe_api_destination(self):
        name = self._get_param("Name")
        destination = self.events_backend.describe_api_destination(name)

        return (
            json.dumps(
                {
                    "ApiDestinationArn": destination.arn,
                    "Name": destination.name,
                    "ApiDestinationState": destination.state,
                    "ConnectionArn": destination.connection_arn,
                    "InvocationEndpoint": destination.invocation_endpoint,
                    "HttpMethod": destination.http_method,
                    "CreationTime": destination.creation_time,
                    "LastModifiedTime": destination.creation_time,
                }
            ),
            self.response_headers,
        )
