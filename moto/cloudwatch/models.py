import json

from moto.core import BaseBackend, BaseModel, CloudWatchMetricProvider
from moto.core.utils import (
    iso_8601_datetime_without_milliseconds,
    iso_8601_datetime_with_nanoseconds,
    BackendDict,
)
from datetime import datetime, timedelta
from dateutil.tz import tzutc
from uuid import uuid4

from .exceptions import (
    InvalidFormat,
    ResourceNotFound,
    ValidationError,
    InvalidParameterValue,
    ResourceNotFoundException,
)
from .utils import make_arn_for_dashboard, make_arn_for_alarm
from dateutil import parser

from moto.core import get_account_id
from ..utilities.tagging_service import TaggingService

_EMPTY_LIST = tuple()


class Dimension(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __eq__(self, item):
        if isinstance(item, Dimension):
            return self.name == item.name and (
                self.value is None or item.value is None or self.value == item.value
            )
        return False

    def __ne__(self, item):  # Only needed on Py2; Py3 defines it implicitly
        return self != item

    def __lt__(self, other):
        return self.name < other.name and self.value < other.name


class Metric(object):
    def __init__(self, metric_name, namespace, dimensions):
        self.metric_name = metric_name
        self.namespace = namespace
        self.dimensions = dimensions


class MetricStat(object):
    def __init__(self, metric, period, stat, unit):
        self.metric = metric
        self.period = period
        self.stat = stat
        self.unit = unit


class MetricDataQuery(object):
    def __init__(
        self, query_id, label, period, return_data, expression=None, metric_stat=None
    ):
        self.id = query_id
        self.label = label
        self.period = period
        self.return_data = return_data
        self.expression = expression
        self.metric_stat = metric_stat


def daterange(start, stop, step=timedelta(days=1), inclusive=False):
    """
    This method will iterate from `start` to `stop` datetimes with a timedelta step of `step`
    (supports iteration forwards or backwards in time)

    :param start: start datetime
    :param stop: end datetime
    :param step: step size as a timedelta
    :param inclusive: if True, last item returned will be as step closest to `end` (or `end` if no remainder).
    """

    # inclusive=False to behave like range by default
    total_step_secs = step.total_seconds()
    assert total_step_secs != 0

    if total_step_secs > 0:
        while start < stop:
            yield start
            start = start + step
    else:
        while stop < start:
            yield start
            start = start + step

    if inclusive and start == stop:
        yield start


class FakeAlarm(BaseModel):
    def __init__(
        self,
        region_name,
        name,
        namespace,
        metric_name,
        metric_data_queries,
        comparison_operator,
        evaluation_periods,
        datapoints_to_alarm,
        period,
        threshold,
        statistic,
        extended_statistic,
        description,
        dimensions,
        alarm_actions,
        ok_actions,
        insufficient_data_actions,
        unit,
        actions_enabled,
        treat_missing_data,
        evaluate_low_sample_count_percentile,
        threshold_metric_id,
        rule=None,
    ):
        self.region_name = region_name
        self.name = name
        self.alarm_arn = make_arn_for_alarm(region_name, get_account_id(), name)
        self.namespace = namespace
        self.metric_name = metric_name
        self.metric_data_queries = metric_data_queries
        self.comparison_operator = comparison_operator
        self.evaluation_periods = evaluation_periods
        self.datapoints_to_alarm = datapoints_to_alarm
        self.period = period
        self.threshold = threshold
        self.statistic = statistic
        self.extended_statistic = extended_statistic
        self.description = description
        self.dimensions = [
            Dimension(dimension["name"], dimension["value"]) for dimension in dimensions
        ]
        self.actions_enabled = True if actions_enabled is None else actions_enabled
        self.alarm_actions = alarm_actions
        self.ok_actions = ok_actions
        self.insufficient_data_actions = insufficient_data_actions
        self.unit = unit
        self.configuration_updated_timestamp = iso_8601_datetime_with_nanoseconds(
            datetime.now(tz=tzutc())
        )
        self.treat_missing_data = treat_missing_data
        self.evaluate_low_sample_count_percentile = evaluate_low_sample_count_percentile
        self.threshold_metric_id = threshold_metric_id

        self.history = []

        self.state_reason = "Unchecked: Initial alarm creation"
        self.state_reason_data = "{}"
        self.state_value = "OK"
        self.state_updated_timestamp = iso_8601_datetime_with_nanoseconds(
            datetime.now(tz=tzutc())
        )

        # only used for composite alarms
        self.rule = rule

    def update_state(self, reason, reason_data, state_value):
        # History type, that then decides what the rest of the items are, can be one of ConfigurationUpdate | StateUpdate | Action
        self.history.append(
            (
                "StateUpdate",
                self.state_reason,
                self.state_reason_data,
                self.state_value,
                self.state_updated_timestamp,
            )
        )

        self.state_reason = reason
        self.state_reason_data = reason_data
        self.state_value = state_value
        self.state_updated_timestamp = iso_8601_datetime_with_nanoseconds(
            datetime.now(tz=tzutc())
        )


def are_dimensions_same(metric_dimensions, dimensions):
    if len(metric_dimensions) != len(dimensions):
        return False
    for dimension in metric_dimensions:
        for new_dimension in dimensions:
            if (
                dimension.name != new_dimension.name
                or dimension.value != new_dimension.value
            ):
                return False
    return True


class MetricDatum(BaseModel):
    def __init__(self, namespace, name, value, dimensions, timestamp, unit=None):
        self.namespace = namespace
        self.name = name
        self.value = value
        self.timestamp = timestamp or datetime.utcnow().replace(tzinfo=tzutc())
        self.dimensions = [
            Dimension(dimension["Name"], dimension["Value"]) for dimension in dimensions
        ]
        self.unit = unit

    def filter(self, namespace, name, dimensions, already_present_metrics=None):
        if namespace and namespace != self.namespace:
            return False
        if name and name != self.name:
            return False

        for metric in already_present_metrics or []:
            if (
                (
                    self.dimensions
                    and are_dimensions_same(metric.dimensions, self.dimensions)
                )
                and self.name == metric.name
                and self.namespace == metric.namespace
            ):  # should be considered as already present only when name, namespace and dimensions all three are same
                return False

        if dimensions and any(
            Dimension(d["Name"], d.get("Value")) not in self.dimensions
            for d in dimensions
        ):
            return False
        return True


class Dashboard(BaseModel):
    def __init__(self, name, body):
        # Guaranteed to be unique for now as the name is also the key of a dictionary where they are stored
        self.arn = make_arn_for_dashboard(get_account_id(), name)
        self.name = name
        self.body = body
        self.last_modified = datetime.now()

    @property
    def last_modified_iso(self):
        return self.last_modified.isoformat()

    @property
    def size(self):
        return len(self)

    def __len__(self):
        return len(self.body)

    def __repr__(self):
        return "<CloudWatchDashboard {0}>".format(self.name)


class Statistics:
    def __init__(self, stats, dt):
        self.timestamp = iso_8601_datetime_without_milliseconds(dt)
        self.values = []
        self.stats = stats
        self.unit = None

    @property
    def sample_count(self):
        if "SampleCount" not in self.stats:
            return None

        return len(self.values)

    @property
    def sum(self):
        if "Sum" not in self.stats:
            return None

        return sum(self.values)

    @property
    def minimum(self):
        if "Minimum" not in self.stats:
            return None

        return min(self.values)

    @property
    def maximum(self):
        if "Maximum" not in self.stats:
            return None

        return max(self.values)

    @property
    def average(self):
        if "Average" not in self.stats:
            return None

        # when moto is 3.4+ we can switch to the statistics module
        return sum(self.values) / len(self.values)


class CloudWatchBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.alarms = {}
        self.dashboards = {}
        self.metric_data = []
        self.paged_metric_data = {}
        self.tagger = TaggingService()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "monitoring"
        )

    @property
    # Retrieve a list of all OOTB metrics that are provided by metrics providers
    # Computed on the fly
    def aws_metric_data(self):
        providers = CloudWatchMetricProvider.__subclasses__()
        md = []
        for provider in providers:
            md.extend(provider.get_cloudwatch_metrics())
        return md

    def put_metric_alarm(
        self,
        name,
        namespace,
        metric_name,
        metric_data_queries,
        comparison_operator,
        evaluation_periods,
        datapoints_to_alarm,
        period,
        threshold,
        statistic,
        extended_statistic,
        description,
        dimensions,
        alarm_actions,
        ok_actions,
        insufficient_data_actions,
        unit,
        actions_enabled,
        treat_missing_data,
        evaluate_low_sample_count_percentile,
        threshold_metric_id,
        rule=None,
        tags=None,
    ):
        if extended_statistic and not extended_statistic.startswith("p"):
            raise InvalidParameterValue(
                f"The value {extended_statistic} for parameter ExtendedStatistic is not supported."
            )
        if (
            evaluate_low_sample_count_percentile
            and evaluate_low_sample_count_percentile not in ("evaluate", "ignore")
        ):
            raise ValidationError(
                f"Option {evaluate_low_sample_count_percentile} is not supported. "
                "Supported options for parameter EvaluateLowSampleCountPercentile are evaluate and ignore."
            )

        alarm = FakeAlarm(
            region_name=self.region_name,
            name=name,
            namespace=namespace,
            metric_name=metric_name,
            metric_data_queries=metric_data_queries,
            comparison_operator=comparison_operator,
            evaluation_periods=evaluation_periods,
            datapoints_to_alarm=datapoints_to_alarm,
            period=period,
            threshold=threshold,
            statistic=statistic,
            extended_statistic=extended_statistic,
            description=description,
            dimensions=dimensions,
            alarm_actions=alarm_actions,
            ok_actions=ok_actions,
            insufficient_data_actions=insufficient_data_actions,
            unit=unit,
            actions_enabled=actions_enabled,
            treat_missing_data=treat_missing_data,
            evaluate_low_sample_count_percentile=evaluate_low_sample_count_percentile,
            threshold_metric_id=threshold_metric_id,
            rule=rule,
        )

        self.alarms[name] = alarm
        self.tagger.tag_resource(alarm.alarm_arn, tags)

        return alarm

    def get_all_alarms(self):
        return self.alarms.values()

    @staticmethod
    def _list_element_starts_with(items, needle):
        """True of any of the list elements starts with needle"""
        for item in items:
            if item.startswith(needle):
                return True
        return False

    def get_alarms_by_action_prefix(self, action_prefix):
        return [
            alarm
            for alarm in self.alarms.values()
            if CloudWatchBackend._list_element_starts_with(
                alarm.alarm_actions, action_prefix
            )
        ]

    def get_alarms_by_alarm_name_prefix(self, name_prefix):
        return [
            alarm
            for alarm in self.alarms.values()
            if alarm.name.startswith(name_prefix)
        ]

    def get_alarms_by_alarm_names(self, alarm_names):
        return [alarm for alarm in self.alarms.values() if alarm.name in alarm_names]

    def get_alarms_by_state_value(self, target_state):
        return filter(
            lambda alarm: alarm.state_value == target_state, self.alarms.values()
        )

    def delete_alarms(self, alarm_names):
        for alarm_name in alarm_names:
            self.alarms.pop(alarm_name, None)

    def put_metric_data(self, namespace, metric_data):
        for i, metric in enumerate(metric_data):
            if metric.get("Value") == "NaN":
                raise InvalidParameterValue(
                    f"The value NaN for parameter MetricData.member.{i + 1}.Value is invalid."
                )

        for metric_member in metric_data:
            # Preserve "datetime" for get_metric_statistics comparisons
            timestamp = metric_member.get("Timestamp")
            if timestamp is not None and type(timestamp) != datetime:
                timestamp = parser.parse(timestamp)
            self.metric_data.append(
                MetricDatum(
                    namespace,
                    metric_member["MetricName"],
                    float(metric_member.get("Value", 0)),
                    metric_member.get("Dimensions.member", _EMPTY_LIST),
                    timestamp,
                    metric_member.get("Unit"),
                )
            )

    def get_metric_data(
        self, queries, start_time, end_time, scan_by="TimestampAscending"
    ):

        period_data = [
            md for md in self.metric_data if start_time <= md.timestamp <= end_time
        ]

        results = []
        for query in queries:
            period_start_time = start_time
            query_ns = query["metric_stat._metric._namespace"]
            query_name = query["metric_stat._metric._metric_name"]
            delta = timedelta(seconds=int(query["metric_stat._period"]))
            dimensions = self._extract_dimensions_from_get_metric_data_query(query)
            result_vals = []
            timestamps = []
            stat = query["metric_stat._stat"]
            while period_start_time <= end_time:
                period_end_time = period_start_time + delta
                period_md = [
                    period_md
                    for period_md in period_data
                    if period_start_time <= period_md.timestamp < period_end_time
                ]

                query_period_data = [
                    md
                    for md in period_md
                    if md.namespace == query_ns and md.name == query_name
                ]
                if dimensions:
                    query_period_data = [
                        md
                        for md in period_md
                        if sorted(md.dimensions) == sorted(dimensions)
                        and md.name == query_name
                    ]

                metric_values = [m.value for m in query_period_data]

                if len(metric_values) > 0:
                    if stat == "SampleCount":
                        result_vals.append(len(metric_values))
                    elif stat == "Average":
                        result_vals.append(sum(metric_values) / len(metric_values))
                    elif stat == "Minimum":
                        result_vals.append(min(metric_values))
                    elif stat == "Maximum":
                        result_vals.append(max(metric_values))
                    elif stat == "Sum":
                        result_vals.append(sum(metric_values))
                    timestamps.append(
                        iso_8601_datetime_without_milliseconds(period_start_time)
                    )
                period_start_time += delta
            if scan_by == "TimestampDescending" and len(timestamps) > 0:
                timestamps.reverse()
                result_vals.reverse()
            label = query["metric_stat._metric._metric_name"] + " " + stat
            results.append(
                {
                    "id": query["id"],
                    "label": label,
                    "vals": result_vals,
                    "timestamps": timestamps,
                }
            )
        return results

    def get_metric_statistics(
        self,
        namespace,
        metric_name,
        start_time,
        end_time,
        period,
        stats,
        dimensions,
        unit=None,
    ):
        period_delta = timedelta(seconds=period)
        # TODO: Also filter by unit and dimensions
        filtered_data = [
            md
            for md in self.get_all_metrics()
            if md.namespace == namespace
            and md.name == metric_name
            and start_time <= md.timestamp <= end_time
        ]

        if unit:
            filtered_data = [md for md in filtered_data if md.unit == unit]
        if dimensions:
            filtered_data = [
                md for md in filtered_data if md.filter(None, None, dimensions)
            ]

        # earliest to oldest
        filtered_data = sorted(filtered_data, key=lambda x: x.timestamp)
        if not filtered_data:
            return []

        idx = 0
        data = list()
        for dt in daterange(
            filtered_data[0].timestamp,
            filtered_data[-1].timestamp + period_delta,
            period_delta,
        ):
            s = Statistics(stats, dt)
            while idx < len(filtered_data) and filtered_data[idx].timestamp < (
                dt + period_delta
            ):
                s.values.append(filtered_data[idx].value)
                s.unit = filtered_data[idx].unit
                idx += 1

            if not s.values:
                continue

            data.append(s)

        return data

    def get_all_metrics(self):
        return self.metric_data + self.aws_metric_data

    def put_dashboard(self, name, body):
        self.dashboards[name] = Dashboard(name, body)

    def list_dashboards(self, prefix=""):
        for key, value in self.dashboards.items():
            if key.startswith(prefix):
                yield value

    def delete_dashboards(self, dashboards):
        to_delete = set(dashboards)
        all_dashboards = set(self.dashboards.keys())

        left_over = to_delete - all_dashboards
        if len(left_over) > 0:
            # Some dashboards are not found
            return (
                False,
                "The specified dashboard does not exist. [{0}]".format(
                    ", ".join(left_over)
                ),
            )

        for dashboard in to_delete:
            del self.dashboards[dashboard]

        return True, None

    def get_dashboard(self, dashboard):
        return self.dashboards.get(dashboard)

    def set_alarm_state(self, alarm_name, reason, reason_data, state_value):
        try:
            if reason_data is not None:
                json.loads(reason_data)
        except ValueError:
            raise InvalidFormat("Unknown")

        if alarm_name not in self.alarms:
            raise ResourceNotFound

        if state_value not in ("OK", "ALARM", "INSUFFICIENT_DATA"):
            raise ValidationError(
                "1 validation error detected: "
                f"Value '{state_value}' at 'stateValue' failed to satisfy constraint: "
                "Member must satisfy enum value set: [INSUFFICIENT_DATA, ALARM, OK]"
            )

        self.alarms[alarm_name].update_state(reason, reason_data, state_value)

    def list_metrics(self, next_token, namespace, metric_name, dimensions):
        if next_token:
            if next_token not in self.paged_metric_data:
                raise InvalidParameterValue("Request parameter NextToken is invalid")
            else:
                metrics = self.paged_metric_data[next_token]
                del self.paged_metric_data[next_token]  # Cant reuse same token twice
                return self._get_paginated(metrics)
        else:
            metrics = self.get_filtered_metrics(metric_name, namespace, dimensions)
            return self._get_paginated(metrics)

    def get_filtered_metrics(self, metric_name, namespace, dimensions):
        metrics = self.get_all_metrics()
        new_metrics = []
        for md in metrics:
            if md.filter(
                namespace=namespace,
                name=metric_name,
                dimensions=dimensions,
                already_present_metrics=new_metrics,
            ):
                new_metrics.append(md)
        return new_metrics

    def list_tags_for_resource(self, arn):
        return self.tagger.get_tag_dict_for_resource(arn)

    def tag_resource(self, arn, tags):
        if arn not in self.tagger.tags.keys():
            raise ResourceNotFoundException

        self.tagger.tag_resource(arn, tags)

    def untag_resource(self, arn, tag_keys):
        if arn not in self.tagger.tags.keys():
            raise ResourceNotFoundException

        self.tagger.untag_resource_using_names(arn, tag_keys)

    def _get_paginated(self, metrics):
        if len(metrics) > 500:
            next_token = str(uuid4())
            self.paged_metric_data[next_token] = metrics[500:]
            return next_token, metrics[0:500]
        else:
            return None, metrics

    def _extract_dimensions_from_get_metric_data_query(self, query):
        dimensions = []
        prefix = "metric_stat._metric._dimensions.member."
        suffix_name = "._name"
        suffix_value = "._value"
        counter = 1

        while query.get(f"{prefix}{counter}{suffix_name}") and counter <= 10:
            name = query.get(f"{prefix}{counter}{suffix_name}")
            value = query.get(f"{prefix}{counter}{suffix_value}")
            dimensions.append(Dimension(name=name, value=value))
            counter = counter + 1

        return dimensions


cloudwatch_backends = BackendDict(CloudWatchBackend, "cloudwatch")
