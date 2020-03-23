import re

from moto.core.responses import BaseResponse
from .models import logs_backends
import json


# See http://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/Welcome.html


class LogsResponse(BaseResponse):
    def __init__(self):
        super().__init__()

    @property
    def logs_backend(self):
        return logs_backends[self.region]

    @property
    def request_params(self):
        try:
            return json.loads(self.body)
        except ValueError:
            return {}

    def _get_param(self, param, if_none=None):
        return self.request_params.get(param, if_none)

    def put_metric_filter(self):
        filter_name = self._get_param("filterName")
        filter_pattern = self._get_param("filterPattern")
        log_group_name = self._get_param("logGroupName")
        metric_transformations = self._get_param("metricTransformations")

        assert 1 <= len(filter_name) <= 512
        assert 0 <= len(filter_pattern) <= 1024
        assert 1 <= len(log_group_name) <= 512
        assert len(metric_transformations) == 1

        assert re.match("[^:*]*", filter_name)
        assert re.match("[.-_/#A-Za-z0-9]+", log_group_name)

        self.logs_backend.put_metric_filter(
            filter_name, filter_pattern, log_group_name, metric_transformations
        )

        return ""

    def describe_metric_filters(self):
        filter_name_prefix = self._get_param("filterNamePrefix", None)
        log_group_name = self._get_param("logGroupName", None)
        metric_name = self._get_param("metricName", None)
        metric_namespace = self._get_param("metricNamespace", None)
        next_token = self._get_param("nextToken", None)

        assert filter_name_prefix is None or 1 <= len(filter_name_prefix) <= 512
        assert log_group_name is None or 1 <= len(log_group_name) <= 512
        assert metric_name is None or len(metric_name) <= 255
        assert metric_namespace is None or len(metric_namespace) <= 255
        assert next_token is None or 1 <= len(next_token)

        assert filter_name_prefix is None or re.match("[^:*]*", filter_name_prefix)
        assert log_group_name is None or re.match("[.-_/#A-Za-z0-9]+", log_group_name)
        assert metric_name is None or re.match("[^:*$]*", metric_name)
        assert metric_namespace is None or re.match("[^:*$]*", metric_namespace)

        filters = self.logs_backend.describe_metric_filters(
            filter_name_prefix, log_group_name
        )
        response = '{"metricFilters":' + json.dumps(filters) + ', "nextToken":""}'
        return response

    def delete_metric_filter(self):
        filter_name = self._get_param("filterName", None)
        log_group_name = self._get_param("logGroupName", None)

        assert filter_name is None or 1 <= len(filter_name) <= 512
        assert log_group_name is None or 1 <= len(log_group_name) <= 512

        assert filter_name is None or re.match("[^:*]*", filter_name)
        assert log_group_name is None or re.match("[.-_/#A-Za-z0-9]+", log_group_name)

        self.logs_backend.delete_metric_filter(filter_name, log_group_name)
        return ""

    def create_log_group(self):
        log_group_name = self._get_param("logGroupName")
        tags = self._get_param("tags")
        assert 1 <= len(log_group_name) <= 512  # TODO: assert pattern

        self.logs_backend.create_log_group(log_group_name, tags)
        return ""

    def delete_log_group(self):
        log_group_name = self._get_param("logGroupName")
        self.logs_backend.delete_log_group(log_group_name)
        return ""

    def describe_log_groups(self):
        log_group_name_prefix = self._get_param("logGroupNamePrefix")
        next_token = self._get_param("nextToken")
        limit = self._get_param("limit", 50)
        assert limit <= 50
        groups, next_token = self.logs_backend.describe_log_groups(
            limit, log_group_name_prefix, next_token
        )
        return json.dumps({"logGroups": groups, "nextToken": next_token})

    def create_log_stream(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_name = self._get_param("logStreamName")
        self.logs_backend.create_log_stream(log_group_name, log_stream_name)
        return ""

    def delete_log_stream(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_name = self._get_param("logStreamName")
        self.logs_backend.delete_log_stream(log_group_name, log_stream_name)
        return ""

    def describe_log_streams(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_name_prefix = self._get_param("logStreamNamePrefix", "")
        descending = self._get_param("descending", False)
        limit = self._get_param("limit", 50)
        assert limit <= 50
        next_token = self._get_param("nextToken")
        order_by = self._get_param("orderBy", "LogStreamName")
        assert order_by in {"LogStreamName", "LastEventTime"}

        if order_by == "LastEventTime":
            assert not log_stream_name_prefix

        streams, next_token = self.logs_backend.describe_log_streams(
            descending,
            limit,
            log_group_name,
            log_stream_name_prefix,
            next_token,
            order_by,
        )
        return json.dumps({"logStreams": streams, "nextToken": next_token})

    def put_log_events(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_name = self._get_param("logStreamName")
        log_events = self._get_param("logEvents")
        sequence_token = self._get_param("sequenceToken")

        next_sequence_token = self.logs_backend.put_log_events(
            log_group_name, log_stream_name, log_events, sequence_token
        )
        return json.dumps({"nextSequenceToken": next_sequence_token})

    def get_log_events(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_name = self._get_param("logStreamName")
        start_time = self._get_param("startTime")
        end_time = self._get_param("endTime")
        limit = self._get_param("limit", 10000)
        assert limit <= 10000
        next_token = self._get_param("nextToken")
        start_from_head = self._get_param("startFromHead", False)

        (
            events,
            next_backward_token,
            next_forward_token,
        ) = self.logs_backend.get_log_events(
            log_group_name,
            log_stream_name,
            start_time,
            end_time,
            limit,
            next_token,
            start_from_head,
        )
        return json.dumps(
            {
                "events": events,
                "nextBackwardToken": next_backward_token,
                "nextForwardToken": next_forward_token,
            }
        )

    def filter_log_events(self):
        log_group_name = self._get_param("logGroupName")
        log_stream_names = self._get_param("logStreamNames", [])
        start_time = self._get_param("startTime")
        # impl, see: http://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
        filter_pattern = self._get_param("filterPattern")
        interleaved = self._get_param("interleaved", False)
        end_time = self._get_param("endTime")
        limit = self._get_param("limit", 10000)
        assert limit <= 10000
        next_token = self._get_param("nextToken")

        events, next_token, searched_streams = self.logs_backend.filter_log_events(
            log_group_name,
            log_stream_names,
            start_time,
            end_time,
            limit,
            next_token,
            filter_pattern,
            interleaved,
        )
        return json.dumps(
            {
                "events": events,
                "nextToken": next_token,
                "searchedLogStreams": searched_streams,
            }
        )

    def put_retention_policy(self):
        log_group_name = self._get_param("logGroupName")
        retention_in_days = self._get_param("retentionInDays")
        self.logs_backend.put_retention_policy(log_group_name, retention_in_days)
        return ""

    def delete_retention_policy(self):
        log_group_name = self._get_param("logGroupName")
        self.logs_backend.delete_retention_policy(log_group_name)
        return ""

    def list_tags_log_group(self):
        log_group_name = self._get_param("logGroupName")
        tags = self.logs_backend.list_tags_log_group(log_group_name)
        return json.dumps({"tags": tags})

    def tag_log_group(self):
        log_group_name = self._get_param("logGroupName")
        tags = self._get_param("tags")
        self.logs_backend.tag_log_group(log_group_name, tags)
        return ""

    def untag_log_group(self):
        log_group_name = self._get_param("logGroupName")
        tags = self._get_param("tags")
        self.logs_backend.untag_log_group(log_group_name, tags)
        return ""
