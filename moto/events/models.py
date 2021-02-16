import copy
import os
import re
import json
import sys
from datetime import datetime

from boto3 import Session

from moto.core.exceptions import JsonRESTError
from moto.core import ACCOUNT_ID, BaseBackend, CloudFormationModel
from moto.core.utils import unix_time
from moto.events.exceptions import (
    ValidationException,
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidEventPatternException,
)
from moto.utilities.tagging_service import TaggingService

from uuid import uuid4


class Rule(CloudFormationModel):
    def _generate_arn(self, name):
        return "arn:aws:events:{region_name}:111111111111:rule/{name}".format(
            region_name=self.region_name, name=name
        )

    def __init__(self, name, region_name, **kwargs):
        self.name = name
        self.region_name = region_name
        self.arn = kwargs.get("Arn") or self._generate_arn(name)
        self.event_pattern = kwargs.get("EventPattern")
        self.schedule_exp = kwargs.get("ScheduleExpression")
        self.state = kwargs.get("State") or "ENABLED"
        self.description = kwargs.get("Description")
        self.role_arn = kwargs.get("RoleArn")
        self.event_bus_name = kwargs.get("EventBusName", "default")
        self.targets = []

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

    def matches_pattern(self, event):
        if not self.event_pattern:
            return True

        # only works on the first level of the event dict
        # logic for nested dicts needs to be implemented
        for pattern_key, pattern_value in json.loads(self.event_pattern).items():
            event_value = event.get(pattern_key)
            if event_value not in pattern_value:
                return False

        return True

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

    def put_rule(self, name, **kwargs):
        new_rule = Rule(name, self.region_name, **kwargs)
        self.rules[new_rule.name] = new_rule
        self.rules_order.append(new_rule.name)
        return new_rule

    def put_targets(self, name, targets):
        rule = self.rules.get(name)

        if rule:
            rule.put_targets(targets)
            return True

        return False

    def put_events(self, events):
        num_events = len(events)

        if num_events < 1:
            raise JsonRESTError("ValidationError", "Need at least 1 event")
        elif num_events > 10:
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

                entries.append({"EventId": str(uuid4())})

                # add to correct archive
                # if 'EventBusName' is not espically set, it will stored in the default
                event_bus_name = event.get("EventBusName", "default")
                archives = [
                    archive
                    for archive in self.archives.values()
                    if archive.event_bus_name == event_bus_name
                ]

                for archive in archives:
                    event_copy = copy.deepcopy(event)
                    event_copy.pop("EventBusName", None)

                    if archive.matches_pattern(event):
                        archive.events.append(event_copy)

        # We dont really need to store the events yet
        return entries

    def remove_targets(self, name, ids):
        rule = self.rules.get(name)

        if rule:
            rule.remove_targets(ids)
            return {"FailedEntries": [], "FailedEntryCount": 0}
        else:
            raise JsonRESTError(
                "ResourceNotFoundException",
                "An entity that you specified does not exist",
            )

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

        event_bus = self.event_buses.get(name)

        if not event_bus:
            raise JsonRESTError(
                "ResourceNotFoundException", "Event bus {} does not exist.".format(name)
            )

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

        event_bus_name = source_arn.split("/")[-1]
        if event_bus_name not in self.event_buses:
            raise ResourceNotFoundException(
                "Event bus {} does not exist.".format(event_bus_name)
            )

        if name in self.archives:
            raise ResourceAlreadyExistsException(
                "Archive {} already exists.".format(name)
            )

        archive = Archive(
            self.region_name, name, source_arn, description, event_pattern, retention
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
                "1 validation error detected: Value '{0}' at 'state' failed to satisfy constraint: "
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


events_backends = {}
for region in Session().get_available_regions("events"):
    events_backends[region] = EventsBackend(region)
for region in Session().get_available_regions("events", partition_name="aws-us-gov"):
    events_backends[region] = EventsBackend(region)
for region in Session().get_available_regions("events", partition_name="aws-cn"):
    events_backends[region] = EventsBackend(region)
