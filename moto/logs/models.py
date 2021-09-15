import uuid

from boto3 import Session

from moto import core as moto_core
from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time_millis
from moto.logs.metric_filters import MetricFilters
from moto.logs.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidParameterException,
    LimitExceededException,
)

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

    def __init__(self, region, log_group, name):
        self.region = region
        self.arn = "arn:aws:logs:{region}:{id}:log-group:{log_group}:log-stream:{log_stream}".format(
            region=region,
            id=moto_core.ACCOUNT_ID,
            log_group=log_group,
            log_stream=name,
        )
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

    def put_log_events(
        self, log_group_name, log_stream_name, log_events, sequence_token
    ):
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

            lambda_backends[self.region].send_log_event(
                self.destination_arn,
                self.filter_name,
                log_group_name,
                log_stream_name,
                formatted_log_events,
            )
        elif service == "firehose":
            from moto.firehose import (  # pylint: disable=import-outside-toplevel
                firehose_backends,
            )

            firehose_backends[self.region].send_log_event(
                self.destination_arn,
                self.filter_name,
                log_group_name,
                log_stream_name,
                formatted_log_events,
            )

        return "{:056d}".format(self.upload_sequence_token)

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
        if filter_pattern:
            raise NotImplementedError("filter_pattern is not yet implemented")

        def filter_func(event):
            if start_time and event.timestamp < start_time:
                return False

            if end_time and event.timestamp > end_time:
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


class LogGroup(BaseModel):
    def __init__(self, region, name, tags, **kwargs):
        self.name = name
        self.region = region
        self.arn = f"arn:aws:logs:{region}:{moto_core.ACCOUNT_ID}:log-group:{name}"
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

    def create_log_stream(self, log_stream_name):
        if log_stream_name in self.streams:
            raise ResourceAlreadyExistsException()
        self.streams[log_stream_name] = LogStream(
            self.region, self.name, log_stream_name
        )

    def delete_log_stream(self, log_stream_name):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        del self.streams[log_stream_name]

    def describe_log_streams(
        self,
        descending,
        limit,
        log_group_name,
        log_stream_name_prefix,
        next_token,
        order_by,
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
                if order_by == "logStreamName"
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

    def put_log_events(
        self, log_group_name, log_stream_name, log_events, sequence_token
    ):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException("The specified log stream does not exist.")
        stream = self.streams[log_stream_name]
        return stream.put_log_events(
            log_group_name, log_stream_name, log_events, sequence_token
        )

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
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        stream = self.streams[log_stream_name]
        return stream.get_log_events(
            log_group_name,
            log_stream_name,
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
            events += stream.filter_log_events(
                log_group_name,
                log_stream_names,
                start_time,
                end_time,
                limit,
                next_token,
                filter_pattern,
                interleaved,
            )

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


class LogsBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.groups = dict()  # { logGroupName: LogGroup}
        self.filters = MetricFilters()
        self.queries = dict()
        self.resource_policies = dict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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
            self.region_name, log_group_name, tags, **kwargs
        )
        return self.groups[log_group_name]

    def ensure_log_group(self, log_group_name, tags):
        if log_group_name in self.groups:
            return
        self.groups[log_group_name] = LogGroup(self.region_name, log_group_name, tags)

    def delete_log_group(self, log_group_name):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        del self.groups[log_group_name]

    def describe_log_groups(self, limit, log_group_name_prefix, next_token):
        if limit > 50:
            raise InvalidParameterException(
                constraint="Member must have value less than or equal to 50",
                parameter="limit",
                value=limit,
            )
        if log_group_name_prefix is None:
            log_group_name_prefix = ""

        groups = [
            group.to_describe_dict()
            for name, group in self.groups.items()
            if name.startswith(log_group_name_prefix)
        ]
        groups = sorted(groups, key=lambda x: x["logGroupName"])

        index_start = 0
        if next_token:
            try:
                index_start = (
                    next(
                        index
                        for (index, d) in enumerate(groups)
                        if d["logGroupName"] == next_token
                    )
                    + 1
                )
            except StopIteration:
                index_start = 0
                # AWS returns an empty list if it receives an invalid token.
                groups = []

        index_end = index_start + limit
        if index_end > len(groups):
            index_end = len(groups)

        groups_page = groups[index_start:index_end]

        next_token = None
        if groups_page and index_end < len(groups):
            next_token = groups_page[-1]["logGroupName"]

        return groups_page, next_token

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
            descending,
            limit,
            log_group_name,
            log_stream_name_prefix,
            next_token,
            order_by,
        )

    def put_log_events(
        self, log_group_name, log_stream_name, log_events, sequence_token
    ):
        # TODO: add support for sequence_tokens
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.put_log_events(
            log_group_name, log_stream_name, log_events, sequence_token
        )

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
            log_group_name,
            log_stream_name,
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

        policies = []
        for policy_name, policy_info in self.resource_policies.items():
            policies.append(
                {
                    "policyName": policy_name,
                    "policyDocument": policy_info["policyDocument"],
                    "lastUpdatedTime": policy_info["lastUpdatedTime"],
                }
            )
        return policies

    def put_resource_policy(self, policy_name, policy_doc):
        """Create resource policy and return dict of policy name and doc."""
        if len(self.resource_policies) == MAX_RESOURCE_POLICIES_PER_REGION:
            raise LimitExceededException()

        policy = {
            "policyName": policy_name,
            "policyDocument": policy_doc,
            "lastUpdatedTime": int(unix_time_millis()),
        }
        self.resource_policies[policy_name] = policy
        return {"resourcePolicy": policy}

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
            from moto.awslambda import (  # pylint: disable=import-outside-toplevel
                lambda_backends,
            )

            lambda_func = lambda_backends[self.region_name].get_function(
                destination_arn
            )
            # no specific permission check implemented
            if not lambda_func:
                raise InvalidParameterException(
                    "Could not execute the lambda function. Make sure you "
                    "have given CloudWatch Logs permission to execute your "
                    "function."
                )
        elif service == "firehose":
            from moto.firehose import (  # pylint: disable=import-outside-toplevel
                firehose_backends,
            )

            firehose = firehose_backends[self.region_name].lookup_name_from_arn(
                destination_arn
            )
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


logs_backends = {}
for available_region in Session().get_available_regions("logs"):
    logs_backends[available_region] = LogsBackend(available_region)
for available_region in Session().get_available_regions(
    "logs", partition_name="aws-us-gov"
):
    logs_backends[available_region] = LogsBackend(available_region)
for available_region in Session().get_available_regions(
    "logs", partition_name="aws-cn"
):
    logs_backends[available_region] = LogsBackend(available_region)
