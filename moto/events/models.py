import copy
import os
import re
import json
import sys
import warnings
from collections import namedtuple
from datetime import datetime
from enum import Enum, unique

from boto3 import Session

from moto.core.exceptions import JsonRESTError
from moto.core import ACCOUNT_ID, BaseBackend, CloudFormationModel, BaseModel
from moto.core.utils import unix_time, iso_8601_datetime_without_milliseconds
from moto.events.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidEventPatternException,
    IllegalStatusException,
)
from moto.utilities.tagging_service import TaggingService

from uuid import uuid4


class Rule(CloudFormationModel):
    Arn = namedtuple("Arn", ["service", "resource_type", "resource_id"])

    def __init__(self, name, region_name, **kwargs):
        self.name = name
        self.region_name = region_name
        self.event_pattern = kwargs.get("EventPattern")
        self.schedule_exp = kwargs.get("ScheduleExpression")
        self.state = kwargs.get("State") or "ENABLED"
        self.description = kwargs.get("Description")
        self.role_arn = kwargs.get("RoleArn")
        self.managed_by = kwargs.get("ManagedBy")  # can only be set by AWS services
        self.event_bus_name = kwargs.get("EventBusName")
        self.created_by = ACCOUNT_ID
        self.targets = []

    @property
    def arn(self):
        event_bus_name = (
            ""
            if self.event_bus_name == "default"
            else "{}/".format(self.event_bus_name)
        )

        return "arn:aws:events:{region}:{account_id}:rule/{event_bus_name}{name}".format(
            region=self.region_name,
            account_id=ACCOUNT_ID,
            event_bus_name=event_bus_name,
            name=self.name,
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

    def _does_event_match_pattern(self, event, pattern):
        if not pattern:
            return True
        event_pattern_pairs = [(event.get(k), v) for k, v in pattern.items()]
        for event_item, pattern_item in event_pattern_pairs:
            if not self._does_event_item_match_pattern_item(event_item, pattern_item):
                return False
        return True

    def _does_event_item_match_pattern_item(self, event_item, pattern_item):
        #  Only supports "key: [value]" filters currently
        if not event_item:
            return False
        if isinstance(pattern_item, list):
            return event_item in pattern_item
        if isinstance(pattern_item, dict):
            return self._does_event_match_pattern(event_item, pattern_item)

    def send_to_targets(self, event_bus_name, event):
        event_bus_name = event_bus_name.split("/")[-1]
        if event_bus_name != self.event_bus_name:
            return

        if not self._validate_event(event):
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

    def _validate_event(self, event):
        for field, pattern in json.loads(self.event_pattern).items():
            if not isinstance(pattern, list):
                # to keep it simple at the beginning only pattern with 1 level of depth are validated
                continue

            if isinstance(pattern[0], dict):
                if "exists" in pattern[0]:
                    if pattern[0]["exists"] and field not in event:
                        return False
                    elif not pattern[0]["exists"] and field in event:
                        return False
            elif event.get(field) not in pattern:
                return False

        return True

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
                "timestamp": unix_time(datetime.utcnow()),
                "message": json.dumps(event_copy),
            }
        ]

        logs_backends[self.region_name].create_log_stream(name, log_stream_name)
        logs_backends[self.region_name].put_log_events(
            name, log_stream_name, log_events, None
        )

    def _send_to_events_archive(self, resource_id, event):
        archive_name, archive_uuid = resource_id.split(":")
        archive = events_backends[self.region_name].archives.get(archive_name)
        pattern = archive.event_pattern
        if archive.uuid == archive_uuid:
            event = json.loads(json.dumps(event))
            pattern = json.loads(pattern) if pattern else None
            if self._does_event_match_pattern(event, pattern):
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
                    "To let EventBridge send messages to your SQS FIFO queue, you must enable content-based deduplication."
                )
                return

        sqs_backends[self.region_name].send_message(
            queue_name=resource_id,
            message_body=json.dumps(event_copy),
            group_id=group_id,
        )

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
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        properties.setdefault("EventBusName", "default")

        event_backend = events_backends[region_name]
        event_name = resource_name
        return event_backend.put_rule(name=event_name, **properties)

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
        event_name = resource_name
        event_backend.delete_rule(name=event_name)


class EventBus(CloudFormationModel):
    def __init__(self, region_name, name):
        self.region = region_name
        self.name = name

        self._permissions = {}

    @property
    def arn(self):
        return "arn:aws:events:{region}:{account_id}:event-bus/{name}".format(
            region=self.region, account_id=ACCOUNT_ID, name=self.name
        )

    @property
    def policy(self):
        if not len(self._permissions):
            return None

        policy = {"Version": "2012-10-17", "Statement": []}

        for sid, permission in self._permissions.items():
            policy["Statement"].append(
                {
                    "Sid": sid,
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::{}:root".format(permission["Principal"])
                    },
                    "Action": permission["Action"],
                    "Resource": self.arn,
                }
            )

        return json.dumps(policy)

    def delete(self, region_name):
        event_backend = events_backends[region_name]
        event_backend.delete_event_bus(name=self.name)

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
        cls, resource_name, cloudformation_json, region_name
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
        self.event_pattern = event_pattern
        self.retention = retention if retention else 0

        self.creation_time = unix_time(datetime.utcnow())
        self.state = "ENABLED"
        self.uuid = str(uuid4())

        self.events = []
        self.event_bus_name = source_arn.split("/")[-1]

    @property
    def arn(self):
        return "arn:aws:events:{region}:{account_id}:archive/{name}".format(
            region=self.region, account_id=ACCOUNT_ID, name=self.name
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
            "EventPattern": self.event_pattern,
        }
        result.update(self.describe_short())

        return result

    def update(self, description, event_pattern, retention):
        if description:
            self.description = description
        if event_pattern:
            self.event_pattern = event_pattern
        if retention:
            self.retention = retention

    def delete(self, region_name):
        event_backend = events_backends[region_name]
        event_backend.archives.pop(self.name)

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
        cls, resource_name, cloudformation_json, region_name
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

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        event_backend = events_backends[region_name]
        event_backend.delete_archive(resource_name)


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
            region=self.region, account_id=ACCOUNT_ID, name=self.name
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


class EventsBackend(BaseBackend):
    ACCOUNT_ID = re.compile(r"^(\d{1,12}|\*)$")
    STATEMENT_ID = re.compile(r"^[a-zA-Z0-9-_]{1,64}$")

    def __init__(self, region_name):
        self.rules = {}
        # This array tracks the order in which the rules have been added, since
        # 2.6 doesn't have OrderedDicts.
        self.rules_order = []
        self.next_tokens = {}
        self.region_name = region_name
        self.event_buses = {}
        self.event_sources = {}
        self.archives = {}
        self.replays = {}
        self.tagger = TaggingService()

        self._add_default_event_bus()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def _add_default_event_bus(self):
        self.event_buses["default"] = EventBus(self.region_name, "default")

    def _get_rule_by_index(self, i):
        return self.rules.get(self.rules_order[i])

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

    def delete_rule(self, name):
        self.rules_order.pop(self.rules_order.index(name))
        arn = self.rules.get(name).arn
        if self.tagger.has_tags(arn):
            self.tagger.delete_all_tags_for_resource(arn)
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
            len(self.rules), next_token, limit
        )

        for i in range(start_index, end_index):
            rule = self._get_rule_by_index(i)
            for target in rule.targets:
                if target["Arn"] == target_arn:
                    matching_rules.append(rule.name)

        return_obj["RuleNames"] = matching_rules
        if new_next_token is not None:
            return_obj["NextToken"] = new_next_token

        return return_obj

    def list_rules(self, prefix=None, next_token=None, limit=None):
        match_string = ".*"
        if prefix is not None:
            match_string = "^" + prefix + match_string

        match_regex = re.compile(match_string)

        matching_rules = []
        return_obj = {}

        start_index, end_index, new_next_token = self._process_token_and_limits(
            len(self.rules), next_token, limit
        )

        for i in range(start_index, end_index):
            rule = self._get_rule_by_index(i)
            if match_regex.match(rule.name):
                matching_rules.append(rule)

        return_obj["Rules"] = matching_rules
        if new_next_token is not None:
            return_obj["NextToken"] = new_next_token

        return return_obj

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

    def update_rule(self, rule, **kwargs):
        rule.event_pattern = kwargs.get("EventPattern") or rule.event_pattern
        rule.schedule_exp = kwargs.get("ScheduleExpression") or rule.schedule_exp
        rule.state = kwargs.get("State") or rule.state
        rule.description = kwargs.get("Description") or rule.description
        rule.role_arn = kwargs.get("RoleArn") or rule.role_arn
        rule.event_bus_name = kwargs.get("EventBusName") or rule.event_bus_name

    def put_rule(self, name, **kwargs):
        if kwargs.get("ScheduleExpression") and kwargs.get("EventBusName") != "default":
            raise ValidationException(
                "ScheduleExpression is supported only on the default event bus."
            )

        if name in self.rules:
            self.update_rule(self.rules[name], **kwargs)
            new_rule = self.rules[name]
        else:
            new_rule = Rule(name, self.region_name, **kwargs)
            self.rules[new_rule.name] = new_rule
            self.rules_order.append(new_rule.name)
        return new_rule

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
                            "account": ACCOUNT_ID,
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

    def put_permission(self, event_bus_name, action, principal, statement_id):
        if not event_bus_name:
            event_bus_name = "default"

        event_bus = self.describe_event_bus(event_bus_name)

        if action is None or action != "events:PutEvents":
            raise JsonRESTError(
                "ValidationException",
                "Provided value in parameter 'action' is not supported.",
            )

        if principal is None or self.ACCOUNT_ID.match(principal) is None:
            raise JsonRESTError(
                "InvalidParameterValue", r"Principal must match ^(\d{1,12}|\*)$"
            )

        if statement_id is None or self.STATEMENT_ID.match(statement_id) is None:
            raise JsonRESTError(
                "InvalidParameterValue", r"StatementId must match ^[a-zA-Z0-9-_]{1,64}$"
            )

        event_bus._permissions[statement_id] = {
            "Action": action,
            "Principal": principal,
        }

    def remove_permission(self, event_bus_name, statement_id):
        if not event_bus_name:
            event_bus_name = "default"

        event_bus = self.describe_event_bus(event_bus_name)

        if not len(event_bus._permissions):
            raise JsonRESTError(
                "ResourceNotFoundException", "EventBus does not have a policy."
            )

        if not event_bus._permissions.pop(statement_id, None):
            raise JsonRESTError(
                "ResourceNotFoundException",
                "Statement with the provided id does not exist.",
            )

    def describe_event_bus(self, name):
        if not name:
            name = "default"

        event_bus = self._get_event_bus(name)

        return event_bus

    def create_event_bus(self, name, event_source_name=None):
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

        self.event_buses[name] = EventBus(self.region_name, name)

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
        self.event_buses.pop(name, None)

    def list_tags_for_resource(self, arn):
        name = arn.split("/")[-1]
        if name in self.rules:
            return self.tagger.list_tags_for_resource(self.rules[name].arn)
        raise ResourceNotFoundException(
            "Rule {0} does not exist on EventBus default.".format(name)
        )

    def tag_resource(self, arn, tags):
        name = arn.split("/")[-1]
        if name in self.rules:
            self.tagger.tag_resource(self.rules[name].arn, tags)
            return {}
        raise ResourceNotFoundException(
            "Rule {0} does not exist on EventBus default.".format(name)
        )

    def untag_resource(self, arn, tag_names):
        name = arn.split("/")[-1]
        if name in self.rules:
            self.tagger.untag_resource_using_names(self.rules[name].arn, tag_names)
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

        if event_pattern:
            self._validate_event_pattern(event_pattern)

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

        rule = self.put_rule(
            "Events-Archive-{}".format(name),
            **{
                "EventPattern": json.dumps(rule_event_pattern),
                "EventBusName": event_bus.name,
                "ManagedBy": "prod.vhs.events.aws.internal",
            }
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

    def _validate_event_pattern(self, pattern):
        try:
            json_pattern = json.loads(pattern)
        except ValueError:  # json.JSONDecodeError exists since Python 3.5
            raise InvalidEventPatternException

        if not self._is_event_value_an_array(json_pattern):
            raise InvalidEventPatternException

    def _is_event_value_an_array(self, pattern):
        # the values of a key in the event pattern have to be either a dict or an array
        for value in pattern.values():
            if isinstance(value, dict):
                if not self._is_event_value_an_array(value):
                    return False
            elif not isinstance(value, list):
                return False

        return True

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

        if event_pattern:
            self._validate_event_pattern(event_pattern)

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


events_backends = {}
for region in Session().get_available_regions("events"):
    events_backends[region] = EventsBackend(region)
for region in Session().get_available_regions("events", partition_name="aws-us-gov"):
    events_backends[region] = EventsBackend(region)
for region in Session().get_available_regions("events", partition_name="aws-cn"):
    events_backends[region] = EventsBackend(region)
