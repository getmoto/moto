import uuid

from datetime import datetime, timedelta

from moto.core import BaseBackend, BaseModel
from moto.core import CloudFormationModel
from moto.core.utils import unix_time_millis, BackendDict
from moto.utilities.paginator import paginate
from moto.logs.metric_filters import MetricFilters
from moto.logs.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidParameterException,
    LimitExceededException,
)
from moto.s3.models import s3_backends
from .utils import PAGINATION_MODEL, EventMessageFilter

MAX_RESOURCE_POLICIES_PER_REGION = 10


class LogQuery(BaseModel):
    def __init__(self, query_id, start_time, end_time, query):
        self.query_id = query_id
        self.start_time = start_time
        self.end_time = end_time
        self.query = query


class LogEvent(BaseModel):
    _event_id = 0

    def __init__(self, ingestion_time, log_event):
        self.ingestion_time = ingestion_time
        self.timestamp = log_event["timestamp"]
        self.message = log_event["message"]
        self.event_id = self.__class__._event_id
        self.__class__._event_id += 1
        ""

    def to_filter_dict(self):
        return {
            "eventId": str(self.event_id),
            "ingestionTime": self.ingestion_time,
            # "logStreamName":
            "message": self.message,
            "timestamp": self.timestamp,
        }

    def to_response_dict(self):
        return {
            "ingestionTime": self.ingestion_time,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class LogStream(BaseModel):
    _log_ids = 0

    def __init__(self, account_id, region, log_group, name):
        self.account_id = account_id
        self.region = region
        self.arn = f"arn:aws:logs:{region}:{account_id}:log-group:{log_group}:log-stream:{name}"
        self.creation_time = int(unix_time_millis())
        self.first_event_timestamp = None
        self.last_event_timestamp = None
        self.last_ingestion_time = None
        self.log_stream_name = name
        self.stored_bytes = 0
        self.upload_sequence_token = (
            0  # I'm  guessing this is token needed for sequenceToken by put_events
        )
        self.events = []
        self.destination_arn = None
        self.filter_name = None

        self.__class__._log_ids += 1

    def _update(self):
        # events can be empty when stream is described soon after creation
        self.first_event_timestamp = (
            min([x.timestamp for x in self.events]) if self.events else None
        )
        self.last_event_timestamp = (
            max([x.timestamp for x in self.events]) if self.events else None
        )

    def to_describe_dict(self):
        # Compute start and end times
        self._update()

        res = {
            "arn": self.arn,
            "creationTime": self.creation_time,
            "logStreamName": self.log_stream_name,
            "storedBytes": self.stored_bytes,
        }
        if self.events:
            rest = {
                "firstEventTimestamp": self.first_event_timestamp,
                "lastEventTimestamp": self.last_event_timestamp,
                "lastIngestionTime": self.last_ingestion_time,
                "uploadSequenceToken": str(self.upload_sequence_token),
            }
            res.update(rest)
        return res

    def put_log_events(self, log_group_name, log_stream_name, log_events):
        # TODO: ensure sequence_token
        # TODO: to be thread safe this would need a lock
        self.last_ingestion_time = int(unix_time_millis())
        # TODO: make this match AWS if possible
        self.stored_bytes += sum(
            [len(log_event["message"]) for log_event in log_events]
        )
        events = [
            LogEvent(self.last_ingestion_time, log_event) for log_event in log_events
        ]
        self.events += events
        self.upload_sequence_token += 1

        service = None
        if self.destination_arn:
            service = self.destination_arn.split(":")[2]
            formatted_log_events = [
                {
                    "id": event.event_id,
                    "timestamp": event.timestamp,
                    "message": event.message,
                }
                for event in events
            ]

        if service == "lambda":
            from moto.awslambda import lambda_backends  # due to circular dependency

            lambda_backends[self.account_id][self.region].send_log_event(
                self.destination_arn,
                self.filter_name,
                log_group_name,
                log_stream_name,
                formatted_log_events,
            )
        elif service == "firehose":
            from moto.firehose import firehose_backends

            firehose_backends[self.account_id][self.region].send_log_event(
                self.destination_arn,
                self.filter_name,
                log_group_name,
                log_stream_name,
                formatted_log_events,
            )

        return "{:056d}".format(self.upload_sequence_token)

    def get_log_events(
        self,
        start_time,
        end_time,
        limit,
        next_token,
        start_from_head,
    ):
        if limit is None:
            limit = 10000

        def filter_func(event):
            if start_time and event.timestamp < start_time:
                return False

            if end_time and event.timestamp > end_time:
                return False

            return True

        def get_index_and_direction_from_token(token):
            if token is not None:
                try:
                    return token[0], int(token[2:])
                except Exception:
                    raise InvalidParameterException(
                        "The specified nextToken is invalid."
                    )
            return None, 0

        events = sorted(
            filter(filter_func, self.events), key=lambda event: event.timestamp
        )

        direction, index = get_index_and_direction_from_token(next_token)
        limit_index = limit - 1
        final_index = len(events) - 1

        if direction is None:
            if start_from_head:
                start_index = 0
                end_index = start_index + limit_index
            else:
                end_index = final_index
                start_index = end_index - limit_index
        elif direction == "f":
            start_index = index + 1
            end_index = start_index + limit_index
        elif direction == "b":
            end_index = index - 1
            start_index = end_index - limit_index
        else:
            raise InvalidParameterException("The specified nextToken is invalid.")

        if start_index < 0:
            start_index = 0
        elif start_index > final_index:
            return (
                [],
                "b/{:056d}".format(final_index),
                "f/{:056d}".format(final_index),
            )

        if end_index > final_index:
            end_index = final_index
        elif end_index < 0:
            return ([], "b/{:056d}".format(0), "f/{:056d}".format(0))

        events_page = [
            event.to_response_dict() for event in events[start_index : end_index + 1]
        ]

        return (
            events_page,
            "b/{:056d}".format(start_index),
            "f/{:056d}".format(end_index),
        )

    def filter_log_events(self, start_time, end_time, filter_pattern):
        def filter_func(event):
            if start_time and event.timestamp < start_time:
                return False

            if end_time and event.timestamp > end_time:
                return False

            if not EventMessageFilter(filter_pattern).matches(event.message):
                return False

            return True

        events = []
        for event in sorted(
            filter(filter_func, self.events), key=lambda x: x.timestamp
        ):
            event_obj = event.to_filter_dict()
            event_obj["logStreamName"] = self.log_stream_name
            events.append(event_obj)
        return events


class LogGroup(CloudFormationModel):
    def __init__(self, account_id, region, name, tags, **kwargs):
        self.name = name
        self.account_id = account_id
        self.region = region
        self.arn = f"arn:aws:logs:{region}:{account_id}:log-group:{name}"
        self.creation_time = int(unix_time_millis())
        self.tags = tags
        self.streams = dict()  # {name: LogStream}
        self.retention_in_days = kwargs.get(
            "RetentionInDays"
        )  # AWS defaults to Never Expire for log group retention
        self.subscription_filters = []

        # The Amazon Resource Name (ARN) of the CMK to use when encrypting log data. It is optional.
        # Docs:
        # https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_CreateLogGroup.html
        self.kms_key_id = kwargs.get("kmsKeyId")

    @staticmethod
    def cloudformation_name_type():
        return "LogGroupName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-logs-loggroup.html
        return "AWS::Logs::LogGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        tags = properties.get("Tags", {})
        return logs_backends[account_id][region_name].create_log_group(
            resource_name, tags, **properties
        )

    def create_log_stream(self, log_stream_name):
        if log_stream_name in self.streams:
            raise ResourceAlreadyExistsException()
        stream = LogStream(self.account_id, self.region, self.name, log_stream_name)
        filters = self.describe_subscription_filters()

        if filters:
            stream.destination_arn = filters[0]["destinationArn"]
            stream.filter_name = filters[0]["filterName"]
        self.streams[log_stream_name] = stream

    def delete_log_stream(self, log_stream_name):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        del self.streams[log_stream_name]

    def describe_log_streams(
        self,
        descending,
        log_group_name,
        log_stream_name_prefix,
        order_by,
        next_token=None,
        limit=None,
    ):
        # responses only log_stream_name, creation_time, arn, stored_bytes when no events are stored.

        log_streams = [
            (name, stream.to_describe_dict())
            for name, stream in self.streams.items()
            if name.startswith(log_stream_name_prefix)
        ]

        def sorter(item):
            return (
                item[0]
                if order_by == "LogStreamName"
                else item[1].get("lastEventTimestamp", 0)
            )

        log_streams = sorted(log_streams, key=sorter, reverse=descending)
        first_index = 0
        if next_token:
            try:
                group, stream = next_token.split("@")
                if group != log_group_name:
                    raise ValueError()
                first_index = (
                    next(
                        index
                        for (index, e) in enumerate(log_streams)
                        if e[1]["logStreamName"] == stream
                    )
                    + 1
                )
            except (ValueError, StopIteration):
                first_index = 0
                log_streams = []

        last_index = first_index + limit
        if last_index > len(log_streams):
            last_index = len(log_streams)
        log_streams_page = [x[1] for x in log_streams[first_index:last_index]]
        new_token = None
        if log_streams_page and last_index < len(log_streams):
            new_token = "{}@{}".format(
                log_group_name, log_streams_page[-1]["logStreamName"]
            )

        return log_streams_page, new_token

    def put_log_events(self, log_group_name, log_stream_name, log_events):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException("The specified log stream does not exist.")
        stream = self.streams[log_stream_name]
        return stream.put_log_events(log_group_name, log_stream_name, log_events)

    def get_log_events(
        self,
        log_stream_name,
        start_time,
        end_time,
        limit,
        next_token,
        start_from_head,
    ):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        stream = self.streams[log_stream_name]
        return stream.get_log_events(
            start_time,
            end_time,
            limit,
            next_token,
            start_from_head,
        )

    def filter_log_events(
        self,
        log_group_name,
        log_stream_names,
        start_time,
        end_time,
        limit,
        next_token,
        filter_pattern,
        interleaved,
    ):
        if not limit:
            limit = 10000
        streams = [
            stream
            for name, stream in self.streams.items()
            if not log_stream_names or name in log_stream_names
        ]

        events = []
        for stream in streams:
            events += stream.filter_log_events(start_time, end_time, filter_pattern)

        if interleaved:
            events = sorted(events, key=lambda event: event["timestamp"])

        first_index = 0
        if next_token:
            try:
                group, stream, event_id = next_token.split("@")
                if group != log_group_name:
                    raise ValueError()
                first_index = (
                    next(
                        index
                        for (index, e) in enumerate(events)
                        if e["logStreamName"] == stream and e["eventId"] == event_id
                    )
                    + 1
                )
            except (ValueError, StopIteration):
                first_index = 0
                # AWS returns an empty list if it receives an invalid token.
                events = []

        last_index = first_index + limit
        if last_index > len(events):
            last_index = len(events)
        events_page = events[first_index:last_index]
        next_token = None
        if events_page and last_index < len(events):
            last_event = events_page[-1]
            next_token = "{}@{}@{}".format(
                log_group_name, last_event["logStreamName"], last_event["eventId"]
            )

        searched_streams = [
            {"logStreamName": stream.log_stream_name, "searchedCompletely": True}
            for stream in streams
        ]
        return events_page, next_token, searched_streams

    def to_describe_dict(self):
        log_group = {
            "arn": self.arn,
            "creationTime": self.creation_time,
            "logGroupName": self.name,
            "metricFilterCount": 0,
            "storedBytes": sum(s.stored_bytes for s in self.streams.values()),
        }
        # AWS only returns retentionInDays if a value is set for the log group (ie. not Never Expire)
        if self.retention_in_days:
            log_group["retentionInDays"] = self.retention_in_days
        if self.kms_key_id:
            log_group["kmsKeyId"] = self.kms_key_id
        return log_group

    def set_retention_policy(self, retention_in_days):
        self.retention_in_days = retention_in_days

    def list_tags(self):
        return self.tags if self.tags else {}

    def tag(self, tags):
        if self.tags:
            self.tags.update(tags)
        else:
            self.tags = tags

    def untag(self, tags_to_remove):
        if self.tags:
            self.tags = {
                k: v for (k, v) in self.tags.items() if k not in tags_to_remove
            }

    def describe_subscription_filters(self):
        return self.subscription_filters

    def put_subscription_filter(
        self, filter_name, filter_pattern, destination_arn, role_arn
    ):
        creation_time = int(unix_time_millis())

        # only one subscription filter can be associated with a log group
        if self.subscription_filters:
            if self.subscription_filters[0]["filterName"] == filter_name:
                creation_time = self.subscription_filters[0]["creationTime"]
            else:
                raise LimitExceededException()

        for stream in self.streams.values():
            stream.destination_arn = destination_arn
            stream.filter_name = filter_name

        self.subscription_filters = [
            {
                "filterName": filter_name,
                "logGroupName": self.name,
                "filterPattern": filter_pattern,
                "destinationArn": destination_arn,
                "roleArn": role_arn,
                "distribution": "ByLogStream",
                "creationTime": creation_time,
            }
        ]

    def delete_subscription_filter(self, filter_name):
        if (
            not self.subscription_filters
            or self.subscription_filters[0]["filterName"] != filter_name
        ):
            raise ResourceNotFoundException(
                "The specified subscription filter does not exist."
            )

        self.subscription_filters = []


class LogResourcePolicy(CloudFormationModel):
    def __init__(self, policy_name, policy_document):
        self.policy_name = policy_name
        self.policy_document = policy_document
        self.last_updated_time = int(unix_time_millis())

    def update(self, policy_document):
        self.policy_document = policy_document
        self.last_updated_time = int(unix_time_millis())

    def describe(self):
        return {
            "policyName": self.policy_name,
            "policyDocument": self.policy_document,
            "lastUpdatedTime": self.last_updated_time,
        }

    @property
    def physical_resource_id(self):
        return self.policy_name

    @staticmethod
    def cloudformation_name_type():
        return "PolicyName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-logs-resourcepolicy.html
        return "AWS::Logs::ResourcePolicy"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        policy_name = properties["PolicyName"]
        policy_document = properties["PolicyDocument"]
        return logs_backends[account_id][region_name].put_resource_policy(
            policy_name, policy_document
        )

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        properties = cloudformation_json["Properties"]
        policy_name = properties["PolicyName"]
        policy_document = properties["PolicyDocument"]

        backend = logs_backends[account_id][region_name]
        updated = backend.put_resource_policy(policy_name, policy_document)
        # TODO: move `update by replacement logic` to cloudformation. this is required for implementing rollbacks
        if original_resource.policy_name != policy_name:
            backend.delete_resource_policy(original_resource.policy_name)
        return updated

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name
    ):
        return logs_backends[account_id][region_name].delete_resource_policy(
            resource_name
        )


class LogsBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.groups = dict()  # { logGroupName: LogGroup}
        self.filters = MetricFilters()
        self.queries = dict()
        self.resource_policies = dict()

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "logs"
        )

    def create_log_group(self, log_group_name, tags, **kwargs):
        if log_group_name in self.groups:
            raise ResourceAlreadyExistsException()
        if len(log_group_name) > 512:
            raise InvalidParameterException(
                constraint="Member must have length less than or equal to 512",
                parameter="logGroupName",
                value=log_group_name,
            )
        self.groups[log_group_name] = LogGroup(
            self.account_id, self.region_name, log_group_name, tags, **kwargs
        )
        return self.groups[log_group_name]

    def ensure_log_group(self, log_group_name, tags):
        if log_group_name in self.groups:
            return
        self.groups[log_group_name] = LogGroup(
            self.account_id, self.region_name, log_group_name, tags
        )

    def delete_log_group(self, log_group_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        del self.groups[log_group_name]

    @paginate(pagination_model=PAGINATION_MODEL)
    def describe_log_groups(self, log_group_name_prefix=None):
        if log_group_name_prefix is None:
            log_group_name_prefix = ""

        groups = [
            group.to_describe_dict()
            for name, group in self.groups.items()
            if name.startswith(log_group_name_prefix)
        ]
        groups = sorted(groups, key=lambda x: x["logGroupName"])

        return groups

    def create_log_stream(self, log_group_name, log_stream_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.create_log_stream(log_stream_name)

    def delete_log_stream(self, log_group_name, log_stream_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.delete_log_stream(log_stream_name)

    def describe_log_streams(
        self,
        descending,
        limit,
        log_group_name,
        log_stream_name_prefix,
        next_token,
        order_by,
    ):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        if limit > 50:
            raise InvalidParameterException(
                constraint="Member must have value less than or equal to 50",
                parameter="limit",
                value=limit,
            )
        if order_by not in ["LogStreamName", "LastEventTime"]:
            raise InvalidParameterException(
                constraint="Member must satisfy enum value set: [LogStreamName, LastEventTime]",
                parameter="orderBy",
                value=order_by,
            )
        if order_by == "LastEventTime" and log_stream_name_prefix:
            raise InvalidParameterException(
                msg="Cannot order by LastEventTime with a logStreamNamePrefix."
            )
        log_group = self.groups[log_group_name]
        return log_group.describe_log_streams(
            descending=descending,
            limit=limit,
            log_group_name=log_group_name,
            log_stream_name_prefix=log_stream_name_prefix,
            next_token=next_token,
            order_by=order_by,
        )

    def put_log_events(self, log_group_name, log_stream_name, log_events):
        """
        The SequenceToken-parameter is not yet implemented
        """
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]

        # Only events from the last 14 days or 2 hours in the future are accepted
        rejected_info = {}
        allowed_events = []
        last_timestamp = None
        oldest = int(unix_time_millis(datetime.utcnow() - timedelta(days=14)))
        newest = int(unix_time_millis(datetime.utcnow() + timedelta(hours=2)))
        for idx, event in enumerate(log_events):
            if last_timestamp and last_timestamp > event["timestamp"]:
                raise InvalidParameterException(
                    "Log events in a single PutLogEvents request must be in chronological order."
                )
            if event["timestamp"] < oldest:
                rejected_info["tooOldLogEventEndIndex"] = idx
            elif event["timestamp"] > newest:
                rejected_info["tooNewLogEventStartIndex"] = idx
            else:
                allowed_events.append(event)
            last_timestamp = event["timestamp"]

        token = log_group.put_log_events(
            log_group_name, log_stream_name, allowed_events
        )
        return token, rejected_info

    def get_log_events(
        self,
        log_group_name,
        log_stream_name,
        start_time,
        end_time,
        limit,
        next_token,
        start_from_head,
    ):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        if limit and limit > 1000:
            raise InvalidParameterException(
                constraint="Member must have value less than or equal to 10000",
                parameter="limit",
                value=limit,
            )
        log_group = self.groups[log_group_name]
        return log_group.get_log_events(
            log_stream_name, start_time, end_time, limit, next_token, start_from_head
        )

    def filter_log_events(
        self,
        log_group_name,
        log_stream_names,
        start_time,
        end_time,
        limit,
        next_token,
        filter_pattern,
        interleaved,
    ):
        """
        The following filter patterns are currently supported: Single Terms, Multiple Terms, Exact Phrases.
        If the pattern is not supported, all events are returned.
        """
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        if limit and limit > 1000:
            raise InvalidParameterException(
                constraint="Member must have value less than or equal to 10000",
                parameter="limit",
                value=limit,
            )
        log_group = self.groups[log_group_name]
        return log_group.filter_log_events(
            log_group_name,
            log_stream_names,
            start_time,
            end_time,
            limit,
            next_token,
            filter_pattern,
            interleaved,
        )

    def put_retention_policy(self, log_group_name, retention_in_days):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.set_retention_policy(retention_in_days)

    def delete_retention_policy(self, log_group_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.set_retention_policy(None)

    def describe_resource_policies(
        self, next_token, limit
    ):  # pylint: disable=unused-argument
        """Return list of resource policies.

        The next_token and limit arguments are ignored.  The maximum
        number of resource policies per region is a small number (less
        than 50), so pagination isn't needed.
        """
        limit = limit or MAX_RESOURCE_POLICIES_PER_REGION

        return list(self.resource_policies.values())

    def put_resource_policy(self, policy_name, policy_doc):
        """Creates/updates resource policy and return policy object"""
        if policy_name in self.resource_policies:
            policy = self.resource_policies[policy_name]
            policy.update(policy_doc)
            return policy
        if len(self.resource_policies) == MAX_RESOURCE_POLICIES_PER_REGION:
            raise LimitExceededException()
        policy = LogResourcePolicy(policy_name, policy_doc)
        self.resource_policies[policy_name] = policy
        return policy

    def delete_resource_policy(self, policy_name):
        """Remove resource policy with a policy name matching given name."""
        if policy_name not in self.resource_policies:
            raise ResourceNotFoundException(
                msg=f"Policy with name [{policy_name}] does not exist"
            )
        del self.resource_policies[policy_name]
        return ""

    def list_tags_log_group(self, log_group_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.list_tags()

    def tag_log_group(self, log_group_name, tags):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        log_group.tag(tags)

    def untag_log_group(self, log_group_name, tags):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        log_group.untag(tags)

    def put_metric_filter(
        self, filter_name, filter_pattern, log_group_name, metric_transformations
    ):
        self.filters.add_filter(
            filter_name, filter_pattern, log_group_name, metric_transformations
        )

    def describe_metric_filters(
        self, prefix=None, log_group_name=None, metric_name=None, metric_namespace=None
    ):
        filters = self.filters.get_matching_filters(
            prefix, log_group_name, metric_name, metric_namespace
        )
        return filters

    def delete_metric_filter(self, filter_name=None, log_group_name=None):
        self.filters.delete_filter(filter_name, log_group_name)

    def describe_subscription_filters(self, log_group_name):
        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        return log_group.describe_subscription_filters()

    def put_subscription_filter(
        self, log_group_name, filter_name, filter_pattern, destination_arn, role_arn
    ):
        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        service = destination_arn.split(":")[2]
        if service == "lambda":
            from moto.awslambda import lambda_backends

            try:
                lambda_backends[self.account_id][self.region_name].get_function(
                    destination_arn
                )
            # no specific permission check implemented
            except Exception:
                raise InvalidParameterException(
                    "Could not execute the lambda function. Make sure you "
                    "have given CloudWatch Logs permission to execute your "
                    "function."
                )
        elif service == "firehose":
            from moto.firehose import firehose_backends

            firehose = firehose_backends[self.account_id][
                self.region_name
            ].lookup_name_from_arn(destination_arn)
            if not firehose:
                raise InvalidParameterException(
                    "Could not deliver test message to specified Firehose "
                    "stream. Check if the given Firehose stream is in ACTIVE "
                    "state."
                )
        else:
            # TODO: support Kinesis stream destinations
            raise InvalidParameterException(
                f"Service '{service}' has not implemented for "
                f"put_subscription_filter()"
            )

        log_group.put_subscription_filter(
            filter_name, filter_pattern, destination_arn, role_arn
        )

    def delete_subscription_filter(self, log_group_name, filter_name):
        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        log_group.delete_subscription_filter(filter_name)

    def start_query(self, log_group_names, start_time, end_time, query_string):

        for log_group_name in log_group_names:
            if log_group_name not in self.groups:
                raise ResourceNotFoundException()

        query_id = uuid.uuid1()
        self.queries[query_id] = LogQuery(query_id, start_time, end_time, query_string)
        return query_id

    def create_export_task(self, log_group_name, destination):
        s3_backends[self.account_id]["global"].get_bucket(destination)
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        task_id = uuid.uuid4()
        return task_id


logs_backends = BackendDict(LogsBackend, "logs")
