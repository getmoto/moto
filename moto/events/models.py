import copy
import os
import re
import json
import sys
import warnings
from collections import namedtuple
from datetime import datetime
from enum import Enum, unique
from json import JSONDecodeError
from operator import lt, le, eq, ge, gt

from collections import OrderedDict
from moto.core.exceptions import JsonRESTError
from moto.core import get_account_id, BaseBackend, CloudFormationModel, BaseModel
from moto.core.utils import (
    unix_time,
    unix_time_millis,
    iso_8601_datetime_without_milliseconds,
    BackendDict,
)
from moto.events.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidEventPatternException,
    IllegalStatusException,
)
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService

from uuid import uuid4

from .utils import PAGINATION_MODEL

# Sentinel to signal the absence of a field for `Exists` pattern matching
UNDEFINED = object()


class Rule(CloudFormationModel):
    Arn = namedtuple("Arn", ["service", "resource_type", "resource_id"])

    def __init__(
        self,
        name,
        region_name,
        description,
        event_pattern,
        schedule_exp,
        role_arn,
        event_bus_name,
        state,
        managed_by=None,
        targets=None,
    ):
        self.name = name
        self.region_name = region_name
        self.description = description
        self.event_pattern = EventPattern.load(event_pattern)
        self.scheduled_expression = schedule_exp
        self.role_arn = role_arn
        self.event_bus_name = event_bus_name
        self.state = state or "ENABLED"
        self.managed_by = managed_by  # can only be set by AWS services
        self.created_by = get_account_id()
        self.targets = targets or []

    @property
    def arn(self):
        event_bus_name = (
            ""
            if self.event_bus_name == "default"
            else "{}/".format(self.event_bus_name)
        )

        return (
            "arn:aws:events:{region}:{account_id}:rule/{event_bus_name}{name}".format(
                region=self.region_name,
                account_id=get_account_id(),
                event_bus_name=event_bus_name,
                name=self.name,
            )
        )

    @property
    def physical_resource_id(self):
        return self.name

    # This song and dance for targets is because we need order for Limits and NextTokens, but can't use OrderedDicts
    # with Python 2.6, so tracking it with an array it is.
    def _check_target_exists(self, target_id):
        for i in range(0, len(self.targets)):
            if target_id == self.targets[i]["Id"]:
                return i
        return None

    def enable(self):
        self.state = "ENABLED"

    def disable(self):
        self.state = "DISABLED"

    def delete(self, region_name):
        event_backend = events_backends[region_name]
        event_backend.delete_rule(name=self.name)

    def put_targets(self, targets):
        # Not testing for valid ARNs.
        for target in targets:
            index = self._check_target_exists(target["Id"])
            if index is not None:
                self.targets[index] = target
            else:
                self.targets.append(target)

    def remove_targets(self, ids):
        for target_id in ids:
            index = self._check_target_exists(target_id)
            if index is not None:
                self.targets.pop(index)

    def send_to_targets(self, event_bus_name, event):
        event_bus_name = event_bus_name.split("/")[-1]
        if event_bus_name != self.event_bus_name.split("/")[-1]:
            return

        if not self.event_pattern.matches_event(event):
            return

        # supported targets
        # - CloudWatch Log Group
        # - EventBridge Archive
        # - SQS Queue + FIFO Queue
        for target in self.targets:
            arn = self._parse_arn(target["Arn"])

            if arn.service == "logs" and arn.resource_type == "log-group":
                self._send_to_cw_log_group(arn.resource_id, event)
            elif arn.service == "events" and not arn.resource_type:
                input_template = json.loads(target["InputTransformer"]["InputTemplate"])
                archive_arn = self._parse_arn(input_template["archive-arn"])

                self._send_to_events_archive(archive_arn.resource_id, event)
            elif arn.service == "sqs":
                group_id = target.get("SqsParameters", {}).get("MessageGroupId")
                self._send_to_sqs_queue(arn.resource_id, event, group_id)
            else:
                raise NotImplementedError("Expr not defined for {0}".format(type(self)))

    def _parse_arn(self, arn):
        # http://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html
        # this method needs probably some more fine tuning,
        # when also other targets are supported
        elements = arn.split(":", 5)

        service = elements[2]
        resource = elements[5]

        if ":" in resource and "/" in resource:
            if resource.index(":") < resource.index("/"):
                resource_type, resource_id = resource.split(":", 1)
            else:
                resource_type, resource_id = resource.split("/", 1)
        elif ":" in resource:
            resource_type, resource_id = resource.split(":", 1)
        elif "/" in resource:
            resource_type, resource_id = resource.split("/", 1)
        else:
            resource_type = None
            resource_id = resource

        return self.Arn(
            service=service, resource_type=resource_type, resource_id=resource_id
        )

    def _send_to_cw_log_group(self, name, event):
        from moto.logs import logs_backends

        event_copy = copy.deepcopy(event)
        event_copy["time"] = iso_8601_datetime_without_milliseconds(
            datetime.utcfromtimestamp(event_copy["time"])
        )

        log_stream_name = str(uuid4())
        log_events = [
            {
                "timestamp": unix_time_millis(datetime.utcnow()),
                "message": json.dumps(event_copy),
            }
        ]

        logs_backends[self.region_name].create_log_stream(name, log_stream_name)
        logs_backends[self.region_name].put_log_events(
            name, log_stream_name, log_events
        )

    def _send_to_events_archive(self, resource_id, event):
        archive_name, archive_uuid = resource_id.split(":")
        archive = events_backends[self.region_name].archives.get(archive_name)
        if archive.uuid == archive_uuid:
            archive.events.append(event)

    def _send_to_sqs_queue(self, resource_id, event, group_id=None):
        from moto.sqs import sqs_backends

        event_copy = copy.deepcopy(event)
        event_copy["time"] = iso_8601_datetime_without_milliseconds(
            datetime.utcfromtimestamp(event_copy["time"])
        )

        if group_id:
            queue_attr = sqs_backends[self.region_name].get_queue_attributes(
                queue_name=resource_id, attribute_names=["ContentBasedDeduplication"]
            )
            if queue_attr["ContentBasedDeduplication"] == "false":
                warnings.warn(
                    "To let EventBridge send messages to your SQS FIFO queue, "
                    "you must enable content-based deduplication."
                )
                return

        sqs_backends[self.region_name].send_message(
            queue_name=resource_id,
            message_body=json.dumps(event_copy),
            group_id=group_id,
        )

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Arn"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn

        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-events-rule.html
        return "AWS::Events::Rule"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        properties.setdefault("EventBusName", "default")

        if "EventPattern" in properties:
            properties["EventPattern"] = json.dumps(properties["EventPattern"])

        event_name = resource_name

        event_pattern = properties.get("EventPattern")
        scheduled_expression = properties.get("ScheduleExpression")
        state = properties.get("State")
        desc = properties.get("Description")
        role_arn = properties.get("RoleArn")
        event_bus_name = properties.get("EventBusName")
        tags = properties.get("Tags")

        backend = events_backends[region_name]
        return backend.put_rule(
            event_name,
            scheduled_expression=scheduled_expression,
            event_pattern=event_pattern,
            state=state,
            description=desc,
            role_arn=role_arn,
            event_bus_name=event_bus_name,
            tags=tags,
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        original_resource.delete(region_name)
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        event_backend = events_backends[region_name]
        event_backend.delete_rule(resource_name)

    def describe(self):
        attributes = {
            "Arn": self.arn,
            "CreatedBy": self.created_by,
            "Description": self.description,
            "EventBusName": self.event_bus_name,
            "EventPattern": self.event_pattern.dump(),
            "ManagedBy": self.managed_by,
            "Name": self.name,
            "RoleArn": self.role_arn,
            "ScheduleExpression": self.scheduled_expression,
            "State": self.state,
        }
        attributes = {
            attr: value for attr, value in attributes.items() if value is not None
        }
        return attributes


class EventBus(CloudFormationModel):
    def __init__(self, region_name, name, tags=None):
        self.region = region_name
        self.name = name
        self.tags = tags or []

        self._statements = {}

    @property
    def arn(self):
        return "arn:aws:events:{region}:{account_id}:event-bus/{name}".format(
            region=self.region, account_id=get_account_id(), name=self.name
        )

    @property
    def policy(self):
        if self._statements:
            policy = {
                "Version": "2012-10-17",
                "Statement": [stmt.describe() for stmt in self._statements.values()],
            }
            return json.dumps(policy)
        return None

    def has_permissions(self):
        return len(self._statements) > 0

    def delete(self, region_name):
        event_backend = events_backends[region_name]
        event_backend.delete_event_bus(name=self.name)

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Arn", "Name", "Policy"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        elif attribute_name == "Name":
            return self.name
        elif attribute_name == "Policy":
            return self.policy

        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return "Name"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-events-eventbus.html
        return "AWS::Events::EventBus"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        event_backend = events_backends[region_name]
        event_name = resource_name
        event_source_name = properties.get("EventSourceName")
        return event_backend.create_event_bus(
            name=event_name, event_source_name=event_source_name
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        original_resource.delete(region_name)
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        event_backend = events_backends[region_name]
        event_bus_name = resource_name
        event_backend.delete_event_bus(event_bus_name)

    def _remove_principals_statements(self, *principals):
        statements_to_delete = set()

        for principal in principals:
            for sid, statement in self._statements.items():
                if statement.principal == principal:
                    statements_to_delete.add(sid)

        # This is done separately to avoid:
        # RuntimeError: dictionary changed size during iteration
        for sid in statements_to_delete:
            del self._statements[sid]

    def add_permission(self, statement_id, action, principal, condition):
        self._remove_principals_statements(principal)
        statement = EventBusPolicyStatement(
            sid=statement_id,
            action=action,
            principal=principal,
            condition=condition,
            resource=self.arn,
        )
        self._statements[statement_id] = statement

    def add_policy(self, policy):
        policy_statements = policy["Statement"]

        principals = [stmt["Principal"] for stmt in policy_statements]
        self._remove_principals_statements(*principals)

        for new_statement in policy_statements:
            sid = new_statement["Sid"]
            self._statements[sid] = EventBusPolicyStatement.from_dict(new_statement)

    def remove_statement(self, sid):
        return self._statements.pop(sid, None)

    def remove_statements(self):
        self._statements.clear()


class EventBusPolicyStatement:
    def __init__(
        self, sid, principal, action, resource, effect="Allow", condition=None
    ):
        self.sid = sid
        self.principal = principal
        self.action = action
        self.resource = resource
        self.effect = effect
        self.condition = condition

    def describe(self):
        statement = dict(
            Sid=self.sid,
            Effect=self.effect,
            Principal=self.principal,
            Action=self.action,
            Resource=self.resource,
        )

        if self.condition:
            statement["Condition"] = self.condition
        return statement

    @classmethod
    def from_dict(cls, statement_dict):
        params = dict(
            sid=statement_dict["Sid"],
            effect=statement_dict["Effect"],
            principal=statement_dict["Principal"],
            action=statement_dict["Action"],
            resource=statement_dict["Resource"],
        )
        condition = statement_dict.get("Condition")
        if condition:
            params["condition"] = condition

        return cls(**params)


class Archive(CloudFormationModel):
    # https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_ListArchives.html#API_ListArchives_RequestParameters
    VALID_STATES = [
        "ENABLED",
        "DISABLED",
        "CREATING",
        "UPDATING",
        "CREATE_FAILED",
        "UPDATE_FAILED",
    ]

    def __init__(
        self, region_name, name, source_arn, description, event_pattern, retention
    ):
        self.region = region_name
        self.name = name
        self.source_arn = source_arn
        self.description = description
        self.event_pattern = EventPattern.load(event_pattern)
        self.retention = retention if retention else 0

        self.creation_time = unix_time(datetime.utcnow())
        self.state = "ENABLED"
        self.uuid = str(uuid4())

        self.events = []
        self.event_bus_name = source_arn.split("/")[-1]

    @property
    def arn(self):
        return "arn:aws:events:{region}:{account_id}:archive/{name}".format(
            region=self.region, account_id=get_account_id(), name=self.name
        )

    def describe_short(self):
        return {
            "ArchiveName": self.name,
            "EventSourceArn": self.source_arn,
            "State": self.state,
            "RetentionDays": self.retention,
            "SizeBytes": sys.getsizeof(self.events) if len(self.events) > 0 else 0,
            "EventCount": len(self.events),
            "CreationTime": self.creation_time,
        }

    def describe(self):
        result = {
            "ArchiveArn": self.arn,
            "Description": self.description,
            "EventPattern": self.event_pattern.dump(),
        }
        result.update(self.describe_short())

        return result

    def update(self, description, event_pattern, retention):
        if description:
            self.description = description
        if event_pattern:
            self.event_pattern = EventPattern.load(event_pattern)
        if retention:
            self.retention = retention

    def delete(self, region_name):
        event_backend = events_backends[region_name]
        event_backend.archives.pop(self.name)

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Arn", "ArchiveName"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "ArchiveName":
            return self.name
        elif attribute_name == "Arn":
            return self.arn

        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return "ArchiveName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-events-archive.html
        return "AWS::Events::Archive"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        event_backend = events_backends[region_name]

        source_arn = properties.get("SourceArn")
        description = properties.get("Description")
        event_pattern = properties.get("EventPattern")
        retention = properties.get("RetentionDays")

        return event_backend.create_archive(
            resource_name, source_arn, description, event_pattern, retention
        )

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        if new_resource_name == original_resource.name:
            properties = cloudformation_json["Properties"]

            original_resource.update(
                properties.get("Description"),
                properties.get("EventPattern"),
                properties.get("Retention"),
            )

            return original_resource
        else:
            original_resource.delete(region_name)
            return cls.create_from_cloudformation_json(
                new_resource_name, cloudformation_json, region_name
            )


@unique
class ReplayState(Enum):
    # https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_ListReplays.html#API_ListReplays_RequestParameters
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    CANCELLING = "CANCELLING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Replay(BaseModel):
    def __init__(
        self,
        region_name,
        name,
        description,
        source_arn,
        start_time,
        end_time,
        destination,
    ):
        self.region = region_name
        self.name = name
        self.description = description
        self.source_arn = source_arn
        self.event_start_time = start_time
        self.event_end_time = end_time
        self.destination = destination

        self.state = ReplayState.STARTING
        self.start_time = unix_time(datetime.utcnow())
        self.end_time = None

    @property
    def arn(self):
        return "arn:aws:events:{region}:{account_id}:replay/{name}".format(
            region=self.region, account_id=get_account_id(), name=self.name
        )

    def describe_short(self):
        return {
            "ReplayName": self.name,
            "EventSourceArn": self.source_arn,
            "State": self.state.value,
            "EventStartTime": self.event_start_time,
            "EventEndTime": self.event_end_time,
            "ReplayStartTime": self.start_time,
            "ReplayEndTime": self.end_time,
        }

    def describe(self):
        result = {
            "ReplayArn": self.arn,
            "Description": self.description,
            "Destination": self.destination,
        }

        result.update(self.describe_short())

        return result

    def replay_events(self, archive):
        event_bus_name = self.destination["Arn"].split("/")[-1]

        for event in archive.events:
            for rule in events_backends[self.region].rules.values():
                rule.send_to_targets(
                    event_bus_name,
                    dict(event, **{"id": str(uuid4()), "replay-name": self.name}),
                )

        self.state = ReplayState.COMPLETED
        self.end_time = unix_time(datetime.utcnow())


class Connection(BaseModel):
    def __init__(
        self, name, region_name, description, authorization_type, auth_parameters
    ):
        self.uuid = uuid4()
        self.name = name
        self.region = region_name
        self.description = description
        self.authorization_type = authorization_type
        self.auth_parameters = auth_parameters
        self.creation_time = unix_time(datetime.utcnow())
        self.state = "AUTHORIZED"

    @property
    def arn(self):
        return "arn:aws:events:{0}:{1}:connection/{2}/{3}".format(
            self.region, get_account_id(), self.name, self.uuid
        )

    def describe_short(self):
        """
        Create the short description for the Connection object.

        Taken our from the Response Syntax of this API doc:
            - https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DeleteConnection.html

        Something to consider:
            - The original response also has
                - LastAuthorizedTime (number)
                - LastModifiedTime (number)
            - At the time of implementing this, there was no place where to set/get
            those attributes. That is why they are not in the response.

        Returns:
            dict
        """
        return {
            "ConnectionArn": self.arn,
            "ConnectionState": self.state,
            "CreationTime": self.creation_time,
        }

    def describe(self):
        """
        Create a complete description for the Connection object.

        Taken our from the Response Syntax of this API doc:
            - https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeConnection.html

        Something to consider:
            - The original response also has:
                - LastAuthorizedTime (number)
                - LastModifiedTime (number)
                - SecretArn (string)
                - StateReason (string)
            - At the time of implementing this, there was no place where to set/get
            those attributes. That is why they are not in the response.

        Returns:
            dict
        """
        return {
            "AuthorizationType": self.authorization_type,
            "AuthParameters": self.auth_parameters,
            "ConnectionArn": self.arn,
            "ConnectionState": self.state,
            "CreationTime": self.creation_time,
            "Description": self.description,
            "Name": self.name,
        }


class Destination(BaseModel):
    def __init__(
        self,
        name,
        region_name,
        description,
        connection_arn,
        invocation_endpoint,
        invocation_rate_limit_per_second,
        http_method,
    ):
        self.uuid = uuid4()
        self.name = name
        self.region = region_name
        self.description = description
        self.connection_arn = connection_arn
        self.invocation_endpoint = invocation_endpoint
        self.invocation_rate_limit_per_second = invocation_rate_limit_per_second
        self.creation_time = unix_time(datetime.utcnow())
        self.http_method = http_method
        self.state = "ACTIVE"

    @property
    def arn(self):
        return "arn:aws:events:{0}:{1}:api-destination/{2}/{3}".format(
            self.region, get_account_id(), self.name, self.uuid
        )

    def describe(self):
        """
        Describes the Destination object as a dict

        Docs:
            Response Syntax in
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeApiDestination.html

        Something to consider:
            - The response also has [InvocationRateLimitPerSecond] which was not
            available when implementing this method

        Returns:
            dict
        """
        return {
            "ApiDestinationArn": self.arn,
            "ApiDestinationState": self.state,
            "ConnectionArn": self.connection_arn,
            "CreationTime": self.creation_time,
            "Description": self.description,
            "HttpMethod": self.http_method,
            "InvocationEndpoint": self.invocation_endpoint,
            "InvocationRateLimitPerSecond": self.invocation_rate_limit_per_second,
            "LastModifiedTime": self.creation_time,
            "Name": self.name,
        }

    def describe_short(self):
        return {
            "ApiDestinationArn": self.arn,
            "ApiDestinationState": self.state,
            "CreationTime": self.creation_time,
            "LastModifiedTime": self.creation_time,
        }


class EventPattern:
    def __init__(self, raw_pattern, pattern):
        self._raw_pattern = raw_pattern
        self._pattern = pattern

    def get_pattern(self):
        return self._pattern

    def matches_event(self, event):
        if not self._pattern:
            return True
        event = json.loads(json.dumps(event))
        return self._does_event_match(event, self._pattern)

    def _does_event_match(self, event, pattern):
        items_and_filters = [(event.get(k, UNDEFINED), v) for k, v in pattern.items()]
        nested_filter_matches = [
            self._does_event_match(item, nested_filter)
            for item, nested_filter in items_and_filters
            if isinstance(nested_filter, dict)
        ]
        filter_list_matches = [
            self._does_item_match_filters(item, filter_list)
            for item, filter_list in items_and_filters
            if isinstance(filter_list, list)
        ]
        return all(nested_filter_matches + filter_list_matches)

    def _does_item_match_filters(self, item, filters):
        allowed_values = [value for value in filters if isinstance(value, str)]
        allowed_values_match = item in allowed_values if allowed_values else True
        full_match = isinstance(item, list) and item == allowed_values
        named_filter_matches = [
            self._does_item_match_named_filter(item, pattern)
            for pattern in filters
            if isinstance(pattern, dict)
        ]
        return (full_match or allowed_values_match) and all(named_filter_matches)

    @staticmethod
    def _does_item_match_named_filter(item, pattern):
        filter_name, filter_value = list(pattern.items())[0]
        if filter_name == "exists":
            is_leaf_node = not isinstance(item, dict)
            leaf_exists = is_leaf_node and item is not UNDEFINED
            should_exist = filter_value
            return leaf_exists if should_exist else not leaf_exists
        if filter_name == "prefix":
            prefix = filter_value
            return item.startswith(prefix)
        if filter_name == "numeric":
            as_function = {"<": lt, "<=": le, "=": eq, ">=": ge, ">": gt}
            operators_and_values = zip(filter_value[::2], filter_value[1::2])
            numeric_matches = [
                as_function[operator](item, value)
                for operator, value in operators_and_values
            ]
            return all(numeric_matches)
        else:
            warnings.warn(
                "'{}' filter logic unimplemented. defaulting to True".format(
                    filter_name
                )
            )
            return True

    @classmethod
    def load(cls, raw_pattern):
        parser = EventPatternParser(raw_pattern)
        pattern = parser.parse()
        return cls(raw_pattern, pattern)

    def dump(self):
        return self._raw_pattern


class EventPatternParser:
    def __init__(self, pattern):
        self.pattern = pattern

    def _validate_event_pattern(self, pattern):
        # values in the event pattern have to be either a dict or an array
        for attr, value in pattern.items():
            if isinstance(value, dict):
                self._validate_event_pattern(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    raise InvalidEventPatternException(
                        reason="Empty arrays are not allowed"
                    )
            else:
                raise InvalidEventPatternException(
                    reason=f"'{attr}' must be an object or an array"
                )

    def parse(self):
        try:
            parsed_pattern = json.loads(self.pattern) if self.pattern else dict()
            self._validate_event_pattern(parsed_pattern)
            return parsed_pattern
        except JSONDecodeError:
            raise InvalidEventPatternException(reason="Invalid JSON")


class EventsBackend(BaseBackend):
    """
    When a event occurs, the appropriate targets are triggered for a subset of usecases.

    Supported events: S3:CreateBucket

    Supported targets: AWSLambda functions
    """

    ACCOUNT_ID = re.compile(r"^(\d{1,12}|\*)$")
    STATEMENT_ID = re.compile(r"^[a-zA-Z0-9-_]{1,64}$")
    _CRON_REGEX = re.compile(r"^cron\(.*\)")
    _RATE_REGEX = re.compile(r"^rate\(\d*\s(minute|minutes|hour|hours|day|days)\)")

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.rules = OrderedDict()
        self.next_tokens = {}
        self.event_buses = {}
        self.event_sources = {}
        self.archives = {}
        self.replays = {}
        self.tagger = TaggingService()

        self._add_default_event_bus()
        self.connections = {}
        self.destinations = {}

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "events"
        )

    def _add_default_event_bus(self):
        self.event_buses["default"] = EventBus(self.region_name, "default")

    def _gen_next_token(self, index):
        token = os.urandom(128).encode("base64")
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

    def _get_event_bus(self, name):
        event_bus_name = name.split("/")[-1]

        event_bus = self.event_buses.get(event_bus_name)
        if not event_bus:
            raise ResourceNotFoundException(
                "Event bus {} does not exist.".format(event_bus_name)
            )

        return event_bus

    def _get_replay(self, name):
        replay = self.replays.get(name)
        if not replay:
            raise ResourceNotFoundException("Replay {} does not exist.".format(name))

        return replay

    def put_rule(
        self,
        name,
        *,
        description=None,
        event_bus_name=None,
        event_pattern=None,
        role_arn=None,
        scheduled_expression=None,
        state=None,
        managed_by=None,
        tags=None,
    ):
        event_bus_name = event_bus_name or "default"

        if not event_pattern and not scheduled_expression:
            raise JsonRESTError(
                "ValidationException",
                "Parameter(s) EventPattern or ScheduleExpression must be specified.",
            )

        if scheduled_expression:
            if event_bus_name != "default":
                raise ValidationException(
                    "ScheduleExpression is supported only on the default event bus."
                )

            if not (
                self._CRON_REGEX.match(scheduled_expression)
                or self._RATE_REGEX.match(scheduled_expression)
            ):
                raise ValidationException("Parameter ScheduleExpression is not valid.")

        existing_rule = self.rules.get(name)
        targets = existing_rule.targets if existing_rule else list()
        rule = Rule(
            name,
            self.region_name,
            description,
            event_pattern,
            scheduled_expression,
            role_arn,
            event_bus_name,
            state,
            managed_by,
            targets=targets,
        )
        self.rules[name] = rule

        if tags:
            self.tagger.tag_resource(rule.arn, tags)

        return rule

    def delete_rule(self, name):
        rule = self.rules.get(name)
        if len(rule.targets) > 0:
            raise ValidationException("Rule can't be deleted since it has targets.")

        arn = rule.arn
        if self.tagger.has_tags(arn):
            self.tagger.delete_all_tags_for_resource(arn)
        return self.rules.pop(name) is not None

    def describe_rule(self, name):
        rule = self.rules.get(name)
        if not rule:
            raise ResourceNotFoundException("Rule {} does not exist.".format(name))
        return rule

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

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_rule_names_by_target(self, target_arn):
        matching_rules = []

        for _, rule in self.rules.items():
            for target in rule.targets:
                if target["Arn"] == target_arn:
                    matching_rules.append(rule)

        return matching_rules

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_rules(self, prefix=None):
        match_string = ".*"
        if prefix is not None:
            match_string = "^" + prefix + match_string

        match_regex = re.compile(match_string)

        matching_rules = []

        for name, rule in self.rules.items():
            if match_regex.match(name):
                matching_rules.append(rule)

        return matching_rules

    def list_targets_by_rule(self, rule, next_token=None, limit=None):
        # We'll let a KeyError exception be thrown for response to handle if
        # rule doesn't exist.
        rule = self.rules[rule]

        start_index, end_index, new_next_token = self._process_token_and_limits(
            len(rule.targets), next_token, limit
        )

        returned_targets = []
        return_obj = {}

        for i in range(start_index, end_index):
            returned_targets.append(rule.targets[i])

        return_obj["Targets"] = returned_targets
        if new_next_token is not None:
            return_obj["NextToken"] = new_next_token

        return return_obj

    def put_targets(self, name, event_bus_name, targets):
        # super simple ARN check
        invalid_arn = next(
            (
                target["Arn"]
                for target in targets
                if not re.match(r"arn:[\d\w:\-/]*", target["Arn"])
            ),
            None,
        )
        if invalid_arn:
            raise ValidationException(
                "Parameter {} is not valid. "
                "Reason: Provided Arn is not in correct format.".format(invalid_arn)
            )

        for target in targets:
            arn = target["Arn"]

            if (
                ":sqs:" in arn
                and arn.endswith(".fifo")
                and not target.get("SqsParameters")
            ):
                raise ValidationException(
                    "Parameter(s) SqsParameters must be specified for target: {}.".format(
                        target["Id"]
                    )
                )

        rule = self.rules.get(name)

        if not rule:
            raise ResourceNotFoundException(
                "Rule {0} does not exist on EventBus {1}.".format(name, event_bus_name)
            )

        rule.put_targets(targets)

    def put_events(self, events):
        num_events = len(events)

        if num_events > 10:
            # the exact error text is longer, the Value list consists of all the put events
            raise ValidationException(
                "1 validation error detected: "
                "Value '[PutEventsRequestEntry]' at 'entries' failed to satisfy constraint: "
                "Member must have length less than or equal to 10"
            )

        entries = []
        for event in events:
            if "Source" not in event:
                entries.append(
                    {
                        "ErrorCode": "InvalidArgument",
                        "ErrorMessage": "Parameter Source is not valid. Reason: Source is a required argument.",
                    }
                )
            elif "DetailType" not in event:
                entries.append(
                    {
                        "ErrorCode": "InvalidArgument",
                        "ErrorMessage": "Parameter DetailType is not valid. Reason: DetailType is a required argument.",
                    }
                )
            elif "Detail" not in event:
                entries.append(
                    {
                        "ErrorCode": "InvalidArgument",
                        "ErrorMessage": "Parameter Detail is not valid. Reason: Detail is a required argument.",
                    }
                )
            else:
                try:
                    json.loads(event["Detail"])
                except ValueError:  # json.JSONDecodeError exists since Python 3.5
                    entries.append(
                        {
                            "ErrorCode": "MalformedDetail",
                            "ErrorMessage": "Detail is malformed.",
                        }
                    )
                    continue

                event_id = str(uuid4())
                entries.append({"EventId": event_id})

                # if 'EventBusName' is not especially set, it will be sent to the default one
                event_bus_name = event.get("EventBusName", "default")

                for rule in self.rules.values():
                    rule.send_to_targets(
                        event_bus_name,
                        {
                            "version": "0",
                            "id": event_id,
                            "detail-type": event["DetailType"],
                            "source": event["Source"],
                            "account": get_account_id(),
                            "time": event.get("Time", unix_time(datetime.utcnow())),
                            "region": self.region_name,
                            "resources": event.get("Resources", []),
                            "detail": json.loads(event["Detail"]),
                        },
                    )

        return entries

    def remove_targets(self, name, event_bus_name, ids):
        rule = self.rules.get(name)

        if not rule:
            raise ResourceNotFoundException(
                "Rule {0} does not exist on EventBus {1}.".format(name, event_bus_name)
            )

        rule.remove_targets(ids)

    def test_event_pattern(self):
        raise NotImplementedError()

    @staticmethod
    def _put_permission_from_policy(event_bus, policy):
        try:
            policy_doc = json.loads(policy)
            event_bus.add_policy(policy_doc)
        except JSONDecodeError:
            raise JsonRESTError(
                "ValidationException", "This policy contains invalid Json"
            )

    @staticmethod
    def _condition_param_to_stmt_condition(condition):
        if condition:
            key = condition["Key"]
            value = condition["Value"]
            condition_type = condition["Type"]
            return {condition_type: {key: value}}
        return None

    def _put_permission_from_params(
        self, event_bus, action, principal, statement_id, condition
    ):
        if principal is None:
            raise JsonRESTError(
                "ValidationException", "Parameter Principal must be specified."
            )

        if condition and principal != "*":
            raise JsonRESTError(
                "InvalidParameterValue",
                "Value of the parameter 'principal' must be '*' when the parameter 'condition' is set.",
            )

        if not condition and self.ACCOUNT_ID.match(principal) is None:
            raise JsonRESTError(
                "InvalidParameterValue",
                f"Value {principal} at 'principal' failed to satisfy constraint: "
                r"Member must satisfy regular expression pattern: (\d{12}|\*)",
            )

        if action is None or action != "events:PutEvents":
            raise JsonRESTError(
                "ValidationException",
                "Provided value in parameter 'action' is not supported.",
            )

        if statement_id is None or self.STATEMENT_ID.match(statement_id) is None:
            raise JsonRESTError(
                "InvalidParameterValue", r"StatementId must match ^[a-zA-Z0-9-_]{1,64}$"
            )

        principal = {"AWS": f"arn:aws:iam::{principal}:root"}
        stmt_condition = self._condition_param_to_stmt_condition(condition)
        event_bus.add_permission(statement_id, action, principal, stmt_condition)

    def put_permission(
        self, event_bus_name, action, principal, statement_id, condition, policy
    ):
        if not event_bus_name:
            event_bus_name = "default"

        event_bus = self.describe_event_bus(event_bus_name)

        if policy:
            self._put_permission_from_policy(event_bus, policy)
        else:
            self._put_permission_from_params(
                event_bus, action, principal, statement_id, condition
            )

    def remove_permission(self, event_bus_name, statement_id, remove_all_permissions):
        if not event_bus_name:
            event_bus_name = "default"

        event_bus = self.describe_event_bus(event_bus_name)

        if remove_all_permissions:
            event_bus.remove_statements()
        else:
            if not event_bus.has_permissions():
                raise JsonRESTError(
                    "ResourceNotFoundException", "EventBus does not have a policy."
                )

            statement = event_bus.remove_statement(statement_id)
            if not statement:
                raise JsonRESTError(
                    "ResourceNotFoundException",
                    "Statement with the provided id does not exist.",
                )

    def describe_event_bus(self, name):
        if not name:
            name = "default"

        event_bus = self._get_event_bus(name)

        return event_bus

    def create_event_bus(self, name, event_source_name=None, tags=None):
        if name in self.event_buses:
            raise JsonRESTError(
                "ResourceAlreadyExistsException",
                "Event bus {} already exists.".format(name),
            )

        if not event_source_name and "/" in name:
            raise JsonRESTError(
                "ValidationException", "Event bus name must not contain '/'."
            )

        if event_source_name and event_source_name not in self.event_sources:
            raise JsonRESTError(
                "ResourceNotFoundException",
                "Event source {} does not exist.".format(event_source_name),
            )

        event_bus = EventBus(self.region_name, name, tags=tags)
        self.event_buses[name] = event_bus
        if tags:
            self.tagger.tag_resource(event_bus.arn, tags)

        return self.event_buses[name]

    def list_event_buses(self, name_prefix):
        if name_prefix:
            return [
                event_bus
                for event_bus in self.event_buses.values()
                if event_bus.name.startswith(name_prefix)
            ]

        return list(self.event_buses.values())

    def delete_event_bus(self, name):
        if name == "default":
            raise JsonRESTError(
                "ValidationException", "Cannot delete event bus default."
            )
        event_bus = self.event_buses.pop(name, None)
        if event_bus:
            self.tagger.delete_all_tags_for_resource(event_bus.arn)

    def list_tags_for_resource(self, arn):
        name = arn.split("/")[-1]
        registries = [self.rules, self.event_buses]
        for registry in registries:
            if name in registry:
                return self.tagger.list_tags_for_resource(registry[name].arn)
        raise ResourceNotFoundException(
            "Rule {0} does not exist on EventBus default.".format(name)
        )

    def tag_resource(self, arn, tags):
        name = arn.split("/")[-1]
        registries = [self.rules, self.event_buses]
        for registry in registries:
            if name in registry:
                self.tagger.tag_resource(registry[name].arn, tags)
                return {}
        raise ResourceNotFoundException(
            "Rule {0} does not exist on EventBus default.".format(name)
        )

    def untag_resource(self, arn, tag_names):
        name = arn.split("/")[-1]
        registries = [self.rules, self.event_buses]
        for registry in registries:
            if name in registry:
                self.tagger.untag_resource_using_names(registry[name].arn, tag_names)
                return {}
        raise ResourceNotFoundException(
            "Rule {0} does not exist on EventBus default.".format(name)
        )

    def create_archive(self, name, source_arn, description, event_pattern, retention):
        if len(name) > 48:
            raise ValidationException(
                " 1 validation error detected: "
                "Value '{}' at 'archiveName' failed to satisfy constraint: "
                "Member must have length less than or equal to 48".format(name)
            )

        event_bus = self._get_event_bus(source_arn)

        if name in self.archives:
            raise ResourceAlreadyExistsException(
                "Archive {} already exists.".format(name)
            )

        archive = Archive(
            self.region_name, name, source_arn, description, event_pattern, retention
        )

        rule_event_pattern = json.loads(event_pattern or "{}")
        rule_event_pattern["replay-name"] = [{"exists": False}]

        rule_name = "Events-Archive-{}".format(name)
        rule = self.put_rule(
            rule_name,
            event_pattern=json.dumps(rule_event_pattern),
            event_bus_name=event_bus.name,
            managed_by="prod.vhs.events.aws.internal",
        )
        self.put_targets(
            rule.name,
            rule.event_bus_name,
            [
                {
                    "Id": rule.name,
                    "Arn": "arn:aws:events:{}:::".format(self.region_name),
                    "InputTransformer": {
                        "InputPathsMap": {},
                        "InputTemplate": json.dumps(
                            {
                                "archive-arn": "{0}:{1}".format(
                                    archive.arn, archive.uuid
                                ),
                                "event": "<aws.events.event.json>",
                                "ingestion-time": "<aws.events.event.ingestion-time>",
                            }
                        ),
                    },
                }
            ],
        )

        self.archives[name] = archive

        return archive

    def describe_archive(self, name):
        archive = self.archives.get(name)

        if not archive:
            raise ResourceNotFoundException("Archive {} does not exist.".format(name))

        return archive.describe()

    def list_archives(self, name_prefix, source_arn, state):
        if [name_prefix, source_arn, state].count(None) < 2:
            raise ValidationException(
                "At most one filter is allowed for ListArchives. "
                "Use either : State, EventSourceArn, or NamePrefix."
            )

        if state and state not in Archive.VALID_STATES:
            raise ValidationException(
                "1 validation error detected: "
                "Value '{0}' at 'state' failed to satisfy constraint: "
                "Member must satisfy enum value set: "
                "[{1}]".format(state, ", ".join(Archive.VALID_STATES))
            )

        if [name_prefix, source_arn, state].count(None) == 3:
            return [archive.describe_short() for archive in self.archives.values()]

        result = []

        for archive in self.archives.values():
            if name_prefix and archive.name.startswith(name_prefix):
                result.append(archive.describe_short())
            elif source_arn and archive.source_arn == source_arn:
                result.append(archive.describe_short())
            elif state and archive.state == state:
                result.append(archive.describe_short())

        return result

    def update_archive(self, name, description, event_pattern, retention):
        archive = self.archives.get(name)

        if not archive:
            raise ResourceNotFoundException("Archive {} does not exist.".format(name))

        archive.update(description, event_pattern, retention)

        return {
            "ArchiveArn": archive.arn,
            "CreationTime": archive.creation_time,
            "State": archive.state,
        }

    def delete_archive(self, name):
        archive = self.archives.get(name)

        if not archive:
            raise ResourceNotFoundException("Archive {} does not exist.".format(name))

        archive.delete(self.region_name)

    def start_replay(
        self, name, description, source_arn, start_time, end_time, destination
    ):
        event_bus_arn = destination["Arn"]
        event_bus_arn_pattern = r"^arn:aws:events:[a-zA-Z0-9-]+:\d{12}:event-bus/"
        if not re.match(event_bus_arn_pattern, event_bus_arn):
            raise ValidationException(
                "Parameter Destination.Arn is not valid. "
                "Reason: Must contain an event bus ARN."
            )

        self._get_event_bus(event_bus_arn)

        archive_name = source_arn.split("/")[-1]
        archive = self.archives.get(archive_name)
        if not archive:
            raise ValidationException(
                "Parameter EventSourceArn is not valid. "
                "Reason: Archive {} does not exist.".format(archive_name)
            )

        if event_bus_arn != archive.source_arn:
            raise ValidationException(
                "Parameter Destination.Arn is not valid. "
                "Reason: Cross event bus replay is not permitted."
            )

        if start_time > end_time:
            raise ValidationException(
                "Parameter EventEndTime is not valid. "
                "Reason: EventStartTime must be before EventEndTime."
            )

        if name in self.replays:
            raise ResourceAlreadyExistsException(
                "Replay {} already exists.".format(name)
            )

        replay = Replay(
            self.region_name,
            name,
            description,
            source_arn,
            start_time,
            end_time,
            destination,
        )

        self.replays[name] = replay

        replay.replay_events(archive)

        return {
            "ReplayArn": replay.arn,
            "ReplayStartTime": replay.start_time,
            "State": ReplayState.STARTING.value,  # the replay will be done before returning the response
        }

    def describe_replay(self, name):
        replay = self._get_replay(name)

        return replay.describe()

    def list_replays(self, name_prefix, source_arn, state):
        if [name_prefix, source_arn, state].count(None) < 2:
            raise ValidationException(
                "At most one filter is allowed for ListReplays. "
                "Use either : State, EventSourceArn, or NamePrefix."
            )

        valid_states = sorted([item.value for item in ReplayState])
        if state and state not in valid_states:
            raise ValidationException(
                "1 validation error detected: "
                "Value '{0}' at 'state' failed to satisfy constraint: "
                "Member must satisfy enum value set: "
                "[{1}]".format(state, ", ".join(valid_states))
            )

        if [name_prefix, source_arn, state].count(None) == 3:
            return [replay.describe_short() for replay in self.replays.values()]

        result = []

        for replay in self.replays.values():
            if name_prefix and replay.name.startswith(name_prefix):
                result.append(replay.describe_short())
            elif source_arn and replay.source_arn == source_arn:
                result.append(replay.describe_short())
            elif state and replay.state == state:
                result.append(replay.describe_short())

        return result

    def cancel_replay(self, name):
        replay = self._get_replay(name)

        # replays in the state 'COMPLETED' can't be canceled,
        # but the implementation is done synchronously,
        # so they are done right after the start
        if replay.state not in [
            ReplayState.STARTING,
            ReplayState.RUNNING,
            ReplayState.COMPLETED,
        ]:
            raise IllegalStatusException(
                "Replay {} is not in a valid state for this operation.".format(name)
            )

        replay.state = ReplayState.CANCELLED

        return {"ReplayArn": replay.arn, "State": ReplayState.CANCELLING.value}

    def create_connection(self, name, description, authorization_type, auth_parameters):
        connection = Connection(
            name, self.region_name, description, authorization_type, auth_parameters
        )
        self.connections[name] = connection
        return connection

    def update_connection(self, *, name, **kwargs):
        connection = self.connections.get(name)
        if not connection:
            raise ResourceNotFoundException(
                "Connection '{}' does not exist.".format(name)
            )

        for attr, value in kwargs.items():
            if value is not None and hasattr(connection, attr):
                setattr(connection, attr, value)
        return connection.describe_short()

    def list_connections(self):
        return self.connections.values()

    def describe_connection(self, name):
        """
        Retrieves details about a connection.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeConnection.html

        Args:
            name: The name of the connection to retrieve.

        Raises:
            ResourceNotFoundException: When the connection is not present.

        Returns:
            dict
        """
        connection = self.connections.get(name)
        if not connection:
            raise ResourceNotFoundException(
                "Connection '{}' does not exist.".format(name)
            )

        return connection.describe()

    def delete_connection(self, name):
        """
        Deletes a connection.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DeleteConnection.html

        Args:
            name: The name of the connection to delete.

        Raises:
            ResourceNotFoundException: When the connection is not present.

        Returns:
            dict
        """
        connection = self.connections.pop(name, None)
        if not connection:
            raise ResourceNotFoundException(
                "Connection '{}' does not exist.".format(name)
            )

        return connection.describe_short()

    def create_api_destination(
        self,
        name,
        description,
        connection_arn,
        invocation_endpoint,
        invocation_rate_limit_per_second,
        http_method,
    ):
        """
        Creates an API destination, which is an HTTP invocation endpoint configured as a target for events.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_CreateApiDestination.html

        Returns:
            dict
        """
        destination = Destination(
            name=name,
            region_name=self.region_name,
            description=description,
            connection_arn=connection_arn,
            invocation_endpoint=invocation_endpoint,
            invocation_rate_limit_per_second=invocation_rate_limit_per_second,
            http_method=http_method,
        )

        self.destinations[name] = destination
        return destination.describe_short()

    def list_api_destinations(self):
        return self.destinations.values()

    def describe_api_destination(self, name):
        """
        Retrieves details about an API destination.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DescribeApiDestination.html
        Args:
            name: The name of the API destination to retrieve.

        Returns:
            dict
        """
        destination = self.destinations.get(name)
        if not destination:
            raise ResourceNotFoundException(
                "An api-destination '{}' does not exist.".format(name)
            )
        return destination.describe()

    def update_api_destination(self, *, name, **kwargs):
        """
        Creates an API destination, which is an HTTP invocation endpoint configured as a target for events.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_UpdateApiDestination.html

        Returns:
            dict
        """
        destination = self.destinations.get(name)
        if not destination:
            raise ResourceNotFoundException(
                "An api-destination '{}' does not exist.".format(name)
            )

        for attr, value in kwargs.items():
            if value is not None and hasattr(destination, attr):
                setattr(destination, attr, value)
        return destination.describe_short()

    def delete_api_destination(self, name):
        """
        Deletes the specified API destination.

        Docs:
            https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_DeleteApiDestination.html

        Args:
            name: The name of the destination to delete.

        Raises:
            ResourceNotFoundException: When the destination is not present.

        Returns:
            dict

        """
        destination = self.destinations.pop(name, None)
        if not destination:
            raise ResourceNotFoundException(
                "An api-destination '{}' does not exist.".format(name)
            )
        return {}


events_backends = BackendDict(EventsBackend, "events")
