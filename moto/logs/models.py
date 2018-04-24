from moto.core import BaseBackend
import boto.logs
from moto.core.utils import unix_time_millis
from .exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException
)


class LogEvent:
    _event_id = 0

    def __init__(self, ingestion_time, log_event):
        self.ingestionTime = ingestion_time
        self.timestamp = log_event["timestamp"]
        self.message = log_event['message']
        self.eventId = self.__class__._event_id
        self.__class__._event_id += 1

    def to_filter_dict(self):
        return {
            "eventId": self.eventId,
            "ingestionTime": self.ingestionTime,
            # "logStreamName":
            "message": self.message,
            "timestamp": self.timestamp
        }

    def to_response_dict(self):
        return {
            "ingestionTime": self.ingestionTime,
            "message": self.message,
            "timestamp": self.timestamp
        }


class LogStream:
    _log_ids = 0

    def __init__(self, region, log_group, name):
        self.region = region
        self.arn = "arn:aws:logs:{region}:{id}:log-group:{log_group}:log-stream:{log_stream}".format(
            region=region, id=self.__class__._log_ids, log_group=log_group, log_stream=name)
        self.creationTime = unix_time_millis()
        self.firstEventTimestamp = None
        self.lastEventTimestamp = None
        self.lastIngestionTime = None
        self.logStreamName = name
        self.storedBytes = 0
        self.uploadSequenceToken = 0  # I'm  guessing this is token needed for sequenceToken by put_events
        self.events = []

        self.__class__._log_ids += 1

    def _update(self):
        # events can be empty when stream is described soon after creation
        self.firstEventTimestamp = min([x.timestamp for x in self.events]) if self.events else None
        self.lastEventTimestamp = max([x.timestamp for x in self.events]) if self.events else None

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

    def put_log_events(self, log_group_name, log_stream_name, log_events, sequence_token):
        # TODO: ensure sequence_token
        # TODO: to be thread safe this would need a lock
        self.lastIngestionTime = unix_time_millis()
        # TODO: make this match AWS if possible
        self.storedBytes += sum([len(log_event["message"]) for log_event in log_events])
        self.events += [LogEvent(self.lastIngestionTime, log_event) for log_event in log_events]
        self.uploadSequenceToken += 1

        return self.uploadSequenceToken

    def get_log_events(self, log_group_name, log_stream_name, start_time, end_time, limit, next_token, start_from_head):
        def filter_func(event):
            if start_time and event.timestamp < start_time:
                return False

            if end_time and event.timestamp > end_time:
                return False

            return True

        events = sorted(filter(filter_func, self.events), key=lambda event: event.timestamp, reverse=start_from_head)
        back_token = next_token
        if next_token is None:
            next_token = 0

        events_page = [event.to_response_dict() for event in events[next_token: next_token + limit]]
        next_token += limit
        if next_token >= len(self.events):
            next_token = None

        return events_page, back_token, next_token

    def filter_log_events(self, log_group_name, log_stream_names, start_time, end_time, limit, next_token, filter_pattern, interleaved):
        def filter_func(event):
            if start_time and event.timestamp < start_time:
                return False

            if end_time and event.timestamp > end_time:
                return False

            return True

        events = []
        for event in sorted(filter(filter_func, self.events), key=lambda x: x.timestamp):
            event_obj = event.to_filter_dict()
            event_obj['logStreamName'] = self.logStreamName
            events.append(event_obj)
        return events


class LogGroup:
    def __init__(self, region, name, tags):
        self.name = name
        self.region = region
        self.arn = "arn:aws:logs:{region}:1:log-group:{log_group}".format(
            region=region, log_group=name)
        self.creationTime = unix_time_millis()
        self.tags = tags
        self.streams = dict()  # {name: LogStream}

    def create_log_stream(self, log_stream_name):
        if log_stream_name in self.streams:
            raise ResourceAlreadyExistsException()
        self.streams[log_stream_name] = LogStream(self.region, self.name, log_stream_name)

    def delete_log_stream(self, log_stream_name):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        del self.streams[log_stream_name]

    def describe_log_streams(self, descending, limit, log_group_name, log_stream_name_prefix, next_token, order_by):
        # responses only logStreamName, creationTime, arn, storedBytes when no events are stored.

        log_streams = [(name, stream.to_describe_dict()) for name, stream in self.streams.items() if name.startswith(log_stream_name_prefix)]

        def sorter(item):
            return item[0] if order_by == 'logStreamName' else item[1].get('lastEventTimestamp', 0)

        if next_token is None:
            next_token = 0

        log_streams = sorted(log_streams, key=sorter, reverse=descending)
        new_token = next_token + limit
        log_streams_page = [x[1] for x in log_streams[next_token: new_token]]
        if new_token >= len(log_streams):
            new_token = None

        return log_streams_page, new_token

    def put_log_events(self, log_group_name, log_stream_name, log_events, sequence_token):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        stream = self.streams[log_stream_name]
        return stream.put_log_events(log_group_name, log_stream_name, log_events, sequence_token)

    def get_log_events(self, log_group_name, log_stream_name, start_time, end_time, limit, next_token, start_from_head):
        if log_stream_name not in self.streams:
            raise ResourceNotFoundException()
        stream = self.streams[log_stream_name]
        return stream.get_log_events(log_group_name, log_stream_name, start_time, end_time, limit, next_token, start_from_head)

    def filter_log_events(self, log_group_name, log_stream_names, start_time, end_time, limit, next_token, filter_pattern, interleaved):
        streams = [stream for name, stream in self.streams.items() if not log_stream_names or name in log_stream_names]

        events = []
        for stream in streams:
            events += stream.filter_log_events(log_group_name, log_stream_names, start_time, end_time, limit, next_token, filter_pattern, interleaved)

        if interleaved:
            events = sorted(events, key=lambda event: event['timestamp'])

        if next_token is None:
            next_token = 0

        events_page = events[next_token: next_token + limit]
        next_token += limit
        if next_token >= len(events):
            next_token = None

        searched_streams = [{"logStreamName": stream.logStreamName, "searchedCompletely": True} for stream in streams]
        return events_page, next_token, searched_streams

    def to_describe_dict(self):
        return {
            "arn": self.arn,
            "creationTime": self.creationTime,
            "logGroupName": self.name,
            "metricFilterCount": 0,
            "retentionInDays": 30,
            "storedBytes": sum(s.storedBytes for s in self.streams.values()),
        }


class LogsBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.groups = dict()  # { logGroupName: LogGroup}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_log_group(self, log_group_name, tags):
        if log_group_name in self.groups:
            raise ResourceAlreadyExistsException()
        self.groups[log_group_name] = LogGroup(self.region_name, log_group_name, tags)

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
            log_group_name_prefix = ''
        if next_token is None:
            next_token = 0

        groups = sorted(group.to_describe_dict() for name, group in self.groups.items() if name.startswith(log_group_name_prefix))
        groups_page = groups[next_token:next_token + limit]

        next_token += limit
        if next_token >= len(groups):
            next_token = None

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

    def describe_log_streams(self, descending, limit, log_group_name, log_stream_name_prefix, next_token, order_by):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.describe_log_streams(descending, limit, log_group_name, log_stream_name_prefix, next_token, order_by)

    def put_log_events(self, log_group_name, log_stream_name, log_events, sequence_token):
        # TODO: add support for sequence_tokens
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.put_log_events(log_group_name, log_stream_name, log_events, sequence_token)

    def get_log_events(self, log_group_name, log_stream_name, start_time, end_time, limit, next_token, start_from_head):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.get_log_events(log_group_name, log_stream_name, start_time, end_time, limit, next_token, start_from_head)

    def filter_log_events(self, log_group_name, log_stream_names, start_time, end_time, limit, next_token, filter_pattern, interleaved):
        if log_group_name not in self.groups:
            raise ResourceNotFoundException()
        log_group = self.groups[log_group_name]
        return log_group.filter_log_events(log_group_name, log_stream_names, start_time, end_time, limit, next_token, filter_pattern, interleaved)


logs_backends = {region.name: LogsBackend(region.name) for region in boto.logs.regions()}
