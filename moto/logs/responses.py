import json
import re

from .exceptions import InvalidParameterException

from moto.core.responses import BaseResponse
from .models import logs_backends

# See http://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/Welcome.html


class LogsResponse(BaseResponse):
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
        kms_key_id = self._get_param("kmsKeyId")

        self.logs_backend.create_log_group(log_group_name, tags, kmsKeyId=kms_key_id)
        return ""

    def delete_log_group(self):
        log_group_name = self._get_param("logGroupName")
        self.logs_backend.delete_log_group(log_group_name)
        return ""

    def describe_log_groups(self):
        log_group_name_prefix = self._get_param("logGroupNamePrefix")
        next_token = self._get_param("nextToken")
        limit = self._get_param("limit", 50)
        groups, next_token = self.logs_backend.describe_log_groups(
            limit, log_group_name_prefix, next_token
        )
        result = {"logGroups": groups}
        if next_token:
            result["nextToken"] = next_token
        return json.dumps(result)

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
        next_token = self._get_param("nextToken")
        order_by = self._get_param("orderBy", "LogStreamName")

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
        limit = self._get_param("limit")
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
        limit = self._get_param("limit")
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

    def describe_resource_policies(self):
        next_token = self._get_param("nextToken")
        limit = self._get_param("limit")
        policies = self.logs_backend.describe_resource_policies(next_token, limit)
        return json.dumps({"resourcePolicies": policies})

    def put_resource_policy(self):
        policy_name = self._get_param("policyName")
        policy_doc = self._get_param("policyDocument")
        result = self.logs_backend.put_resource_policy(policy_name, policy_doc)
        return json.dumps(result)

    def delete_resource_policy(self):
        policy_name = self._get_param("policyName")
        self.logs_backend.delete_resource_policy(policy_name)
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

    def describe_subscription_filters(self):
        log_group_name = self._get_param("logGroupName")

        subscription_filters = self.logs_backend.describe_subscription_filters(
            log_group_name
        )

        return json.dumps({"subscriptionFilters": subscription_filters})

    def put_subscription_filter(self):
        log_group_name = self._get_param("logGroupName")
        filter_name = self._get_param("filterName")
        filter_pattern = self._get_param("filterPattern")
        destination_arn = self._get_param("destinationArn")
        role_arn = self._get_param("roleArn")

        self.logs_backend.put_subscription_filter(
            log_group_name, filter_name, filter_pattern, destination_arn, role_arn
        )

        return ""

    def delete_subscription_filter(self):
        log_group_name = self._get_param("logGroupName")
        filter_name = self._get_param("filterName")

        self.logs_backend.delete_subscription_filter(log_group_name, filter_name)

        return ""

    def start_query(self):
        log_group_name = self._get_param("logGroupName")
        log_group_names = self._get_param("logGroupNames")
        start_time = self._get_param("startTime")
        end_time = self._get_param("endTime")
        query_string = self._get_param("queryString")

        if log_group_name and log_group_names:
            raise InvalidParameterException()

        if log_group_name:
            log_group_names = [log_group_name]

        query_id = self.logs_backend.start_query(
            log_group_names, start_time, end_time, query_string
        )

        return json.dumps({"queryId": "{0}".format(query_id)})
