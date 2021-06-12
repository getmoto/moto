import json
from moto.core.utils import amzn_request_id
from moto.core.responses import BaseResponse
from .models import cloudwatch_backends, MetricDataQuery, MetricStat, Metric, Dimension
from dateutil.parser import parse as dtparse


class CloudWatchResponse(BaseResponse):
    @property
    def cloudwatch_backend(self):
        return cloudwatch_backends[self.region]

    def _error(self, code, message, status=400):
        template = self.response_template(ERROR_RESPONSE_TEMPLATE)
        return template.render(code=code, message=message), dict(status=status)

    @amzn_request_id
    def put_metric_alarm(self):
        name = self._get_param("AlarmName")
        namespace = self._get_param("Namespace")
        metric_name = self._get_param("MetricName")
        metrics = self._get_multi_param("Metrics.member")
        metric_data_queries = None
        if metrics:
            metric_data_queries = [
                MetricDataQuery(
                    id=metric.get("Id"),
                    label=metric.get("Label"),
                    period=metric.get("Period"),
                    return_data=metric.get("ReturnData"),
                    expression=metric.get("Expression"),
                    metric_stat=MetricStat(
                        metric=Metric(
                            metric_name=metric.get("MetricStat.Metric.MetricName"),
                            namespace=metric.get("MetricStat.Metric.Namespace"),
                            dimensions=[
                                Dimension(name=dim["Name"], value=dim["Value"])
                                for dim in metric["MetricStat.Metric.Dimensions.member"]
                            ],
                        ),
                        period=metric.get("MetricStat.Period"),
                        stat=metric.get("MetricStat.Stat"),
                        unit=metric.get("MetricStat.Unit"),
                    )
                    if "MetricStat.Metric.MetricName" in metric
                    else None,
                )
                for metric in metrics
            ]
        comparison_operator = self._get_param("ComparisonOperator")
        evaluation_periods = self._get_param("EvaluationPeriods")
        datapoints_to_alarm = self._get_param("DatapointsToAlarm")
        period = self._get_param("Period")
        threshold = self._get_param("Threshold")
        statistic = self._get_param("Statistic")
        description = self._get_param("AlarmDescription")
        dimensions = self._get_list_prefix("Dimensions.member")
        alarm_actions = self._get_multi_param("AlarmActions.member")
        ok_actions = self._get_multi_param("OKActions.member")
        actions_enabled = self._get_param("ActionsEnabled")
        insufficient_data_actions = self._get_multi_param(
            "InsufficientDataActions.member"
        )
        unit = self._get_param("Unit")
        alarm = self.cloudwatch_backend.put_metric_alarm(
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
            description,
            dimensions,
            alarm_actions,
            ok_actions,
            insufficient_data_actions,
            unit,
            actions_enabled,
            self.region,
        )
        template = self.response_template(PUT_METRIC_ALARM_TEMPLATE)
        return template.render(alarm=alarm)

    @amzn_request_id
    def describe_alarms(self):
        action_prefix = self._get_param("ActionPrefix")
        alarm_name_prefix = self._get_param("AlarmNamePrefix")
        alarm_names = self._get_multi_param("AlarmNames.member")
        state_value = self._get_param("StateValue")

        if action_prefix:
            alarms = self.cloudwatch_backend.get_alarms_by_action_prefix(action_prefix)
        elif alarm_name_prefix:
            alarms = self.cloudwatch_backend.get_alarms_by_alarm_name_prefix(
                alarm_name_prefix
            )
        elif alarm_names:
            alarms = self.cloudwatch_backend.get_alarms_by_alarm_names(alarm_names)
        elif state_value:
            alarms = self.cloudwatch_backend.get_alarms_by_state_value(state_value)
        else:
            alarms = self.cloudwatch_backend.get_all_alarms()

        template = self.response_template(DESCRIBE_ALARMS_TEMPLATE)
        return template.render(alarms=alarms)

    @amzn_request_id
    def delete_alarms(self):
        alarm_names = self._get_multi_param("AlarmNames.member")
        self.cloudwatch_backend.delete_alarms(alarm_names)
        template = self.response_template(DELETE_METRIC_ALARMS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def put_metric_data(self):
        namespace = self._get_param("Namespace")
        metric_data = self._get_multi_param("MetricData.member")
        self.cloudwatch_backend.put_metric_data(namespace, metric_data)
        template = self.response_template(PUT_METRIC_DATA_TEMPLATE)
        return template.render()

    @amzn_request_id
    def get_metric_data(self):
        start = dtparse(self._get_param("StartTime"))
        end = dtparse(self._get_param("EndTime"))
        scan_by = self._get_param("ScanBy")

        queries = self._get_list_prefix("MetricDataQueries.member")
        results = self.cloudwatch_backend.get_metric_data(
            start_time=start, end_time=end, queries=queries, scan_by=scan_by
        )

        template = self.response_template(GET_METRIC_DATA_TEMPLATE)
        return template.render(results=results)

    @amzn_request_id
    def get_metric_statistics(self):
        namespace = self._get_param("Namespace")
        metric_name = self._get_param("MetricName")
        start_time = dtparse(self._get_param("StartTime"))
        end_time = dtparse(self._get_param("EndTime"))
        period = int(self._get_param("Period"))
        statistics = self._get_multi_param("Statistics.member")

        # Unsupported Parameters (To Be Implemented)
        unit = self._get_param("Unit")
        extended_statistics = self._get_param("ExtendedStatistics")
        dimensions = self._get_param("Dimensions")
        if extended_statistics or dimensions:
            raise NotImplementedError()

        # TODO: this should instead throw InvalidParameterCombination
        if not statistics:
            raise NotImplementedError(
                "Must specify either Statistics or ExtendedStatistics"
            )

        datapoints = self.cloudwatch_backend.get_metric_statistics(
            namespace, metric_name, start_time, end_time, period, statistics, unit
        )
        template = self.response_template(GET_METRIC_STATISTICS_TEMPLATE)
        return template.render(label=metric_name, datapoints=datapoints)

    @amzn_request_id
    def list_metrics(self):
        namespace = self._get_param("Namespace")
        metric_name = self._get_param("MetricName")
        dimensions = self._get_multi_param("Dimensions.member")
        next_token = self._get_param("NextToken")
        next_token, metrics = self.cloudwatch_backend.list_metrics(
            next_token, namespace, metric_name, dimensions
        )
        template = self.response_template(LIST_METRICS_TEMPLATE)
        return template.render(metrics=metrics, next_token=next_token)

    @amzn_request_id
    def delete_dashboards(self):
        dashboards = self._get_multi_param("DashboardNames.member")
        if dashboards is None:
            return self._error("InvalidParameterValue", "Need at least 1 dashboard")

        status, error = self.cloudwatch_backend.delete_dashboards(dashboards)
        if not status:
            return self._error("ResourceNotFound", error)

        template = self.response_template(DELETE_DASHBOARD_TEMPLATE)
        return template.render()

    @amzn_request_id
    def describe_alarm_history(self):
        raise NotImplementedError()

    @staticmethod
    def filter_alarms(alarms, metric_name, namespace):
        metric_filtered_alarms = []

        for alarm in alarms:
            if alarm.metric_name == metric_name and alarm.namespace == namespace:
                metric_filtered_alarms.append(alarm)
        return metric_filtered_alarms

    @amzn_request_id
    def describe_alarms_for_metric(self):
        alarms = self.cloudwatch_backend.get_all_alarms()
        namespace = self._get_param("Namespace")
        metric_name = self._get_param("MetricName")
        filtered_alarms = self.filter_alarms(alarms, metric_name, namespace)
        template = self.response_template(DESCRIBE_METRIC_ALARMS_TEMPLATE)
        return template.render(alarms=filtered_alarms)

    @amzn_request_id
    def disable_alarm_actions(self):
        raise NotImplementedError()

    @amzn_request_id
    def enable_alarm_actions(self):
        raise NotImplementedError()

    @amzn_request_id
    def get_dashboard(self):
        dashboard_name = self._get_param("DashboardName")

        dashboard = self.cloudwatch_backend.get_dashboard(dashboard_name)
        if dashboard is None:
            return self._error("ResourceNotFound", "Dashboard does not exist")

        template = self.response_template(GET_DASHBOARD_TEMPLATE)
        return template.render(dashboard=dashboard)

    @amzn_request_id
    def list_dashboards(self):
        prefix = self._get_param("DashboardNamePrefix", "")

        dashboards = self.cloudwatch_backend.list_dashboards(prefix)

        template = self.response_template(LIST_DASHBOARD_RESPONSE)
        return template.render(dashboards=dashboards)

    @amzn_request_id
    def put_dashboard(self):
        name = self._get_param("DashboardName")
        body = self._get_param("DashboardBody")

        try:
            json.loads(body)
        except ValueError:
            return self._error("InvalidParameterInput", "Body is invalid JSON")

        self.cloudwatch_backend.put_dashboard(name, body)

        template = self.response_template(PUT_DASHBOARD_RESPONSE)
        return template.render()

    @amzn_request_id
    def set_alarm_state(self):
        alarm_name = self._get_param("AlarmName")
        reason = self._get_param("StateReason")
        reason_data = self._get_param("StateReasonData")
        state_value = self._get_param("StateValue")

        self.cloudwatch_backend.set_alarm_state(
            alarm_name, reason, reason_data, state_value
        )

        template = self.response_template(SET_ALARM_STATE_TEMPLATE)
        return template.render()


PUT_METRIC_ALARM_TEMPLATE = """<PutMetricAlarmResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         {{ request_id }}
      </RequestId>
   </ResponseMetadata>
</PutMetricAlarmResponse>"""

DESCRIBE_ALARMS_TEMPLATE = """<DescribeAlarmsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
    <DescribeAlarmsResult>
        <MetricAlarms>
            {% for alarm in alarms %}
            <member>
                <ActionsEnabled>{{ alarm.actions_enabled }}</ActionsEnabled>
                <AlarmActions>
                    {% for action in alarm.alarm_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </AlarmActions>
                <AlarmArn>{{ alarm.alarm_arn }}</AlarmArn>
                <AlarmConfigurationUpdatedTimestamp>{{ alarm.configuration_updated_timestamp }}</AlarmConfigurationUpdatedTimestamp>
                <AlarmDescription>{{ alarm.description }}</AlarmDescription>
                <AlarmName>{{ alarm.name }}</AlarmName>
                <ComparisonOperator>{{ alarm.comparison_operator }}</ComparisonOperator>
                {% if alarm.dimensions is not none %}
                    <Dimensions>
                        {% for dimension in alarm.dimensions %}
                        <member>
                            <Name>{{ dimension.name }}</Name>
                            <Value>{{ dimension.value }}</Value>
                        </member>
                        {% endfor %}
                    </Dimensions>
                {% endif %}
                <EvaluationPeriods>{{ alarm.evaluation_periods }}</EvaluationPeriods>
                {% if alarm.datapoints_to_alarm is not none %}
                <DatapointsToAlarm>{{ alarm.datapoints_to_alarm }}</DatapointsToAlarm>
                {% endif %}
                <InsufficientDataActions>
                    {% for action in alarm.insufficient_data_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </InsufficientDataActions>
                {% if alarm.metric_name is not none %}
                <MetricName>{{ alarm.metric_name }}</MetricName>
                {% endif %}
                {% if alarm.metric_data_queries is not none %}
                <Metrics>
                    {% for metric in alarm.metric_data_queries %}
                     <member>
                        <Id>{{ metric.id }}</Id>
                        {% if metric.label is not none %}
                        <Label>{{ metric.label }}</Label>
                        {% endif %}
                        {% if metric.expression is not none %}
                        <Expression>{{ metric.expression }}</Expression>
                        {% endif %}
                        {% if metric.metric_stat is not none %}
                        <MetricStat>
                            <Metric>
                                <Namespace>{{ metric.metric_stat.metric.namespace }}</Namespace>
                                <MetricName>{{ metric.metric_stat.metric.metric_name }}</MetricName>
                                <Dimensions>
                                {% for dim in metric.metric_stat.metric.dimensions %}
                                    <member>
                                        <Name>{{ dim.name }}</Name>
                                        <Value>{{ dim.value }}</Value>
                                    </member>
                                {% endfor %}
                                </Dimensions>
                            </Metric>
                            {% if metric.metric_stat.period is not none %}
                            <Period>{{ metric.metric_stat.period }}</Period>
                            {% endif %}
                            <Stat>{{ metric.metric_stat.stat }}</Stat>
                            {% if metric.metric_stat.unit is not none %}
                            <Unit>{{ metric.metric_stat.unit }}</Unit>
                            {% endif %}
                        </MetricStat>
                        {% endif %}
                        {% if metric.period is not none %}
                        <Period>{{ metric.period }}</Period>
                        {% endif %}
                        <ReturnData>{{ metric.return_data }}</ReturnData>
                    </member>
                    {% endfor %}
                </Metrics>
                {% endif %}
                {% if alarm.namespace is not none %}
                <Namespace>{{ alarm.namespace }}</Namespace>
                {% endif %}
                <OKActions>
                    {% for action in alarm.ok_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </OKActions>
                {% if alarm.period is not none %}
                <Period>{{ alarm.period }}</Period>
                {% endif %}
                <StateReason>{{ alarm.state_reason }}</StateReason>
                <StateReasonData>{{ alarm.state_reason_data }}</StateReasonData>
                <StateUpdatedTimestamp>{{ alarm.state_updated_timestamp }}</StateUpdatedTimestamp>
                <StateValue>{{ alarm.state_value }}</StateValue>
                {% if alarm.statistic is not none %}
                <Statistic>{{ alarm.statistic }}</Statistic>
                {% endif %}
                <Threshold>{{ alarm.threshold }}</Threshold>
                {% if alarm.unit is not none %}
                <Unit>{{ alarm.unit }}</Unit>
                {% endif %}
            </member>
            {% endfor %}
        </MetricAlarms>
    </DescribeAlarmsResult>
</DescribeAlarmsResponse>"""

DESCRIBE_METRIC_ALARMS_TEMPLATE = """<DescribeAlarmsForMetricResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
    <DescribeAlarmsForMetricResult>
        <MetricAlarms>
            {% for alarm in alarms %}
            <member>
                <ActionsEnabled>{{ alarm.actions_enabled }}</ActionsEnabled>
                <AlarmActions>
                    {% for action in alarm.alarm_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </AlarmActions>
                <AlarmArn>{{ alarm.alarm_arn }}</AlarmArn>
                <AlarmConfigurationUpdatedTimestamp>{{ alarm.configuration_updated_timestamp }}</AlarmConfigurationUpdatedTimestamp>
                <AlarmDescription>{{ alarm.description }}</AlarmDescription>
                <AlarmName>{{ alarm.name }}</AlarmName>
                <ComparisonOperator>{{ alarm.comparison_operator }}</ComparisonOperator>
                <Dimensions>
                    {% for dimension in alarm.dimensions %}
                    <member>
                        <Name>{{ dimension.name }}</Name>
                        <Value>{{ dimension.value }}</Value>
                    </member>
                    {% endfor %}
                </Dimensions>
                <EvaluationPeriods>{{ alarm.evaluation_periods }}</EvaluationPeriods>
                <InsufficientDataActions>
                    {% for action in alarm.insufficient_data_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </InsufficientDataActions>
                <MetricName>{{ alarm.metric_name }}</MetricName>
                <Namespace>{{ alarm.namespace }}</Namespace>
                <OKActions>
                    {% for action in alarm.ok_actions %}
                    <member>{{ action }}</member>
                    {% endfor %}
                </OKActions>
                <Period>{{ alarm.period }}</Period>
                <StateReason>{{ alarm.state_reason }}</StateReason>
                <StateReasonData>{{ alarm.state_reason_data }}</StateReasonData>
                <StateUpdatedTimestamp>{{ alarm.state_updated_timestamp }}</StateUpdatedTimestamp>
                <StateValue>{{ alarm.state_value }}</StateValue>
                <Statistic>{{ alarm.statistic }}</Statistic>
                <Threshold>{{ alarm.threshold }}</Threshold>
                <Unit>{{ alarm.unit }}</Unit>
            </member>
            {% endfor %}
        </MetricAlarms>
    </DescribeAlarmsForMetricResult>
</DescribeAlarmsForMetricResponse>"""

DELETE_METRIC_ALARMS_TEMPLATE = """<DeleteMetricAlarmResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         {{ request_id }}
      </RequestId>
   </ResponseMetadata>
</DeleteMetricAlarmResponse>"""

PUT_METRIC_DATA_TEMPLATE = """<PutMetricDataResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         {{ request_id }}
      </RequestId>
   </ResponseMetadata>
</PutMetricDataResponse>"""

GET_METRIC_DATA_TEMPLATE = """<GetMetricDataResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <GetMetricDataResult>
       <MetricDataResults>
           {% for result in results %}
            <member>
                <Id>{{ result.id }}</Id>
                <Label>{{ result.label }}</Label>
                <StatusCode>Complete</StatusCode>
                <Timestamps>
                    {% for val in result.timestamps %}
                    <member>{{ val }}</member>
                    {% endfor %}
                </Timestamps>
                <Values>
                    {% for val in result.vals %}
                    <member>{{ val }}</member>
                    {% endfor %}
                </Values>
            </member>
            {% endfor %}
       </MetricDataResults>
   </GetMetricDataResult>
   <ResponseMetadata>
       <RequestId>
            {{ request_id }}
       </RequestId>
   </ResponseMetadata>
</GetMetricDataResponse>"""

GET_METRIC_STATISTICS_TEMPLATE = """<GetMetricStatisticsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <GetMetricStatisticsResult>
      <Label>{{ label }}</Label>
      <Datapoints>
        {% for datapoint in datapoints %}
            <member>
              {% if datapoint.sum is not none %}
              <Sum>{{ datapoint.sum }}</Sum>
              {% endif %}

              {% if datapoint.average is not none %}
              <Average>{{ datapoint.average }}</Average>
              {% endif %}

              {% if datapoint.maximum is not none %}
              <Maximum>{{ datapoint.maximum }}</Maximum>
              {% endif %}

              {% if datapoint.minimum is not none %}
              <Minimum>{{ datapoint.minimum }}</Minimum>
              {% endif %}

              {% if datapoint.sample_count is not none %}
              <SampleCount>{{ datapoint.sample_count }}</SampleCount>
              {% endif %}

              {% if datapoint.extended_statistics is not none %}
              <ExtendedStatistics>{{ datapoint.extended_statistics }}</ExtendedStatistics>
              {% endif %}

              <Timestamp>{{ datapoint.timestamp }}</Timestamp>
              {% if datapoint.unit is not none %}
              <Unit>{{ datapoint.unit }}</Unit>
              {% endif %}
            </member>
        {% endfor %}
      </Datapoints>
    </GetMetricStatisticsResult>
    <ResponseMetadata>
      <RequestId>
        {{ request_id }}
      </RequestId>
    </ResponseMetadata>
</GetMetricStatisticsResponse>"""

LIST_METRICS_TEMPLATE = """<ListMetricsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
    <ListMetricsResult>
        <Metrics>
            {% for metric in metrics %}
            <member>
                <Dimensions>
                    {% for dimension in metric.dimensions %}
                    <member>
                        <Name>{{ dimension.name }}</Name>
                        <Value>{{ dimension.value }}</Value>
                    </member>
                    {% endfor %}
                </Dimensions>
                <MetricName>{{ metric.name }}</MetricName>
                <Namespace>{{ metric.namespace }}</Namespace>
            </member>
            {% endfor %}
        </Metrics>
        {% if next_token is not none %}
        <NextToken>
            {{ next_token }}
        </NextToken>
        {% endif %}
    </ListMetricsResult>
</ListMetricsResponse>"""

PUT_DASHBOARD_RESPONSE = """<PutDashboardResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <PutDashboardResult>
    <DashboardValidationMessages/>
  </PutDashboardResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</PutDashboardResponse>"""

LIST_DASHBOARD_RESPONSE = """<ListDashboardsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <ListDashboardsResult>
    <DashboardEntries>
      {% for dashboard in dashboards %}
      <member>
        <DashboardArn>{{ dashboard.arn }}</DashboardArn>
        <LastModified>{{ dashboard.last_modified_iso }}</LastModified>
        <Size>{{ dashboard.size }}</Size>
        <DashboardName>{{ dashboard.name }}</DashboardName>
      </member>
      {% endfor %}
    </DashboardEntries>
  </ListDashboardsResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ListDashboardsResponse>"""

DELETE_DASHBOARD_TEMPLATE = """<DeleteDashboardsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <DeleteDashboardsResult/>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</DeleteDashboardsResponse>"""

GET_DASHBOARD_TEMPLATE = """<GetDashboardResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <GetDashboardResult>
    <DashboardArn>{{ dashboard.arn }}</DashboardArn>
    <DashboardBody>{{ dashboard.body }}</DashboardBody>
    <DashboardName>{{ dashboard.name }}</DashboardName>
  </GetDashboardResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</GetDashboardResponse>
"""

SET_ALARM_STATE_TEMPLATE = """<SetAlarmStateResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</SetAlarmStateResponse>"""

ERROR_RESPONSE_TEMPLATE = """<ErrorResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <Error>
    <Type>Sender</Type>
    <Code>{{ code }}</Code>
    <Message>{{ message }}</Message>
  </Error>
  <RequestId>{{ request_id }}</RequestId>
</ErrorResponse>"""
