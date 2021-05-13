from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.core.utils import unix_time_millis
from .exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidParameterException,
    LimitExceededException,
)


class LogEvent(BaseModel):
    _event_id = 0

    def __init__(self, ingestion_time, log_event):
        self.ingestionTime = ingestion_time
        self.timestamp = log_event["timestamp"]
        self.message = log_event["message"]
        self.eventId = self.__class__._event_id
        self.__class__._event_id += 1

    def to_filter_dict(self):
        return {
            "eventId": str(self.eventId),
            "ingestionTime": self.ingestionTime,
            # "logStreamName":
            "message": self.message,
            "timestamp": self.timestamp,
        }

    def to_response_dict(self):
        return {
            "ingestionTime": self.ingestionTime,
            "message": self.message,
            "timestamp": self.timestamp,
        }


class LogStream(BaseModel):
    _log_ids = 0

    def __init__(self, region, log_group, name):
        self.region = region
        self.arn = "arn:aws:logs:{region}:{id}:log-group:{log_group}:log-stream:{log_stream}".format(
            region=region,
            id=self.__class__._log_ids,
            log_group=log_group,
            log_stream=name,
        )
        self.creationTime = int(unix_time_millis())
        self.firstEventTimestamp = None
        self.lastEventTimestamp = None
        self.lastIngestionTime = None
        self.logStreamName = name
        self.storedBytes = 0
        self.uploadSequenceToken = (
            0  # I'm  guessing this is token needed for sequenceToken by put_events
        )
        self.events = []
        self.destination_arn = None
        self.filter_name = None

        self.__class__._log_ids += 1

    def _update(self):
        # events can be empty when stream is described soon after creation
        self.firstEventTimestamp = (
            min([x.timestamp for x in self.events]) if self.events else None
        )
        self.lastEventTimestamp = (
            max([x.timestamp for x in self.events]) if self.events else None
        )

    def to_describe_dict(self):
        # Compute start and end times
        self._update()

        res = {
            "arn": self.arn,
            "creationTime": self.creationTime,
            "logStreamName": self.logStreamName,
            "storedBytes": self.storedBytes,
        }
        if self.events:
            rest = {
                "firstEventTimestamp": self.firstEventTimestamp,
                "lastEventTimestamp": self.lastEventTimestamp,
                "lastIngestionTime": self.lastIngestionTime,
                "uploadSequenceToken": str(self.uploadSequenceToken),
            }
            res.update(rest)
        return res

    def put_log_events(
        self, log_group_name, log_stream_name, log_events, sequence_token
    ):
        # TODO: ensure sequence_token
        # TODO: to be thread safe this would need a lock
        self.lastIngestionTime = int(unix_time_millis())
        # TODO: make this match AWS if possible
        self.storedBytes += sum([len(log_event["message"]) for log_event in log_events])
        events = [
            LogEvent(self.lastIngestionTime, log_event) for log_event in log_events
        ]
        self.events += events
        self.uploadSequenceToken += 1

        if self.destination_arn and self.destination_arn.split(":")[2] == "lambda":
            from moto.awslambda import lambda_backends  # due to circular dependency

            lambda_log_events = [
                {
                    "id": event.eventId,
                    "timestamp": event.timestamp,
                    "message": event.message,
                }
                for event in events
            ]

            lambda_backends[self.region].send_log_event(
                self.destination_arn,
                self.filter_name,
                log_group_name,
                log_stream_name,
                lambda_log_events,
            )

        return "{:056d}".format(self.uploadSequenceToken)

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
            event_obj["logStreamName"] = self.logStreamName
            events.append(event_obj)
        return events


class LogGroup(BaseModel):
    def __init__(self, region, name, tags, **kwargs):
        self.name = name
        self.region = region
        self.arn = "arn:aws:logs:{region}:1:log-group:{log_group}".format(
            region=region, log_group=name
        )
        self.creationTime = int(unix_time_millis())
        self.tags = tags
        self.streams = dict()  # {name: LogStream}
        self.retention_in_days = kwargs.get(
            "RetentionInDays"
        )  # AWS defaults to Never Expire for log group retention
        self.subscription_filters = []

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
        # responses only logStreamName, creationTime, arn, storedBytes when no events are stored.

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
            raise ResourceNotFoundException()
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
            {"logStreamName": stream.logStreamName, "searchedCompletely": True}
            for stream in streams
        ]
        return events_page, next_token, searched_streams

    def to_describe_dict(self):
        log_group = {
            "arn": self.arn,
            "creationTime": self.creationTime,
            "logGroupName": self.name,
            "metricFilterCount": 0,
            "storedBytes": sum(s.storedBytes for s in self.streams.values()),
        }
        # AWS only returns retentionInDays if a value is set for the log group (ie. not Never Expire)
        if self.retention_in_days:
            log_group["retentionInDays"] = self.retention_in_days
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
                raise LimitExceededException

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

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_log_group(self, log_group_name, tags, **kwargs):
        if log_group_name in self.groups:
            raise ResourceAlreadyExistsException()
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

    def describe_subscription_filters(self, log_group_name):
        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        return log_group.describe_subscription_filters()

    def put_subscription_filter(
        self, log_group_name, filter_name, filter_pattern, destination_arn, role_arn
    ):
        # TODO: support other destinations like Kinesis stream
        from moto.awslambda import lambda_backends  # due to circular dependency

        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        lambda_func = lambda_backends[self.region_name].get_function(destination_arn)

        # no specific permission check implemented
        if not lambda_func:
            raise InvalidParameterException(
                "Could not execute the lambda function. "
                "Make sure you have given CloudWatch Logs permission to execute your function."
            )

        log_group.put_subscription_filter(
            filter_name, filter_pattern, destination_arn, role_arn
        )

    def delete_subscription_filter(self, log_group_name, filter_name):
        log_group = self.groups.get(log_group_name)

        if not log_group:
            raise ResourceNotFoundException()

        log_group.delete_subscription_filter(filter_name)


logs_backends = {}
for region in Session().get_available_regions("logs"):
    logs_backends[region] = LogsBackend(region)
for region in Session().get_available_regions("logs", partition_name="aws-us-gov"):
    logs_backends[region] = LogsBackend(region)
for region in Session().get_available_regions("logs", partition_name="aws-cn"):
    logs_backends[region] = LogsBackend(region)
