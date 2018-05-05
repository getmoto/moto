import json
from moto.core.utils import amzn_request_id
from moto.core.responses import BaseResponse
from .models import cloudwatch_backends
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
        name = self._get_param('AlarmName')
        namespace = self._get_param('Namespace')
        metric_name = self._get_param('MetricName')
        comparison_operator = self._get_param('ComparisonOperator')
        evaluation_periods = self._get_param('EvaluationPeriods')
        period = self._get_param('Period')
        threshold = self._get_param('Threshold')
        statistic = self._get_param('Statistic')
        description = self._get_param('AlarmDescription')
        dimensions = self._get_list_prefix('Dimensions.member')
        alarm_actions = self._get_multi_param('AlarmActions.member')
        ok_actions = self._get_multi_param('OKActions.member')
        insufficient_data_actions = self._get_multi_param(
            "InsufficientDataActions.member")
        unit = self._get_param('Unit')
        alarm = self.cloudwatch_backend.put_metric_alarm(name, namespace, metric_name,
                                                         comparison_operator,
                                                         evaluation_periods, period,
                                                         threshold, statistic,
                                                         description, dimensions,
                                                         alarm_actions, ok_actions,
                                                         insufficient_data_actions,
                                                         unit)
        template = self.response_template(PUT_METRIC_ALARM_TEMPLATE)
        return template.render(alarm=alarm)

    @amzn_request_id
    def describe_alarms(self):
        action_prefix = self._get_param('ActionPrefix')
        alarm_name_prefix = self._get_param('AlarmNamePrefix')
        alarm_names = self._get_multi_param('AlarmNames.member')
        state_value = self._get_param('StateValue')

        if action_prefix:
            alarms = self.cloudwatch_backend.get_alarms_by_action_prefix(
                action_prefix)
        elif alarm_name_prefix:
            alarms = self.cloudwatch_backend.get_alarms_by_alarm_name_prefix(
                alarm_name_prefix)
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
        alarm_names = self._get_multi_param('AlarmNames.member')
        self.cloudwatch_backend.delete_alarms(alarm_names)
        template = self.response_template(DELETE_METRIC_ALARMS_TEMPLATE)
        return template.render()

    @amzn_request_id
    def put_metric_data(self):
        namespace = self._get_param('Namespace')
        metric_data = self._get_multi_param('MetricData.member')

        self.cloudwatch_backend.put_metric_data(namespace, metric_data)
        template = self.response_template(PUT_METRIC_DATA_TEMPLATE)
        return template.render()

    @amzn_request_id
    def get_metric_statistics(self):
        namespace = self._get_param('Namespace')
        metric_name = self._get_param('MetricName')
        start_time = dtparse(self._get_param('StartTime'))
        end_time = dtparse(self._get_param('EndTime'))
        period = int(self._get_param('Period'))
        statistics = self._get_multi_param("Statistics.member")

        # Unsupported Parameters (To Be Implemented)
        unit = self._get_param('Unit')
        extended_statistics = self._get_param('ExtendedStatistics')
        dimensions = self._get_param('Dimensions')
        if unit or extended_statistics or dimensions:
            raise NotImplemented()

        # TODO: this should instead throw InvalidParameterCombination
        if not statistics:
            raise NotImplemented("Must specify either Statistics or ExtendedStatistics")

        datapoints = self.cloudwatch_backend.get_metric_statistics(namespace, metric_name, start_time, end_time, period, statistics)
        template = self.response_template(GET_METRIC_STATISTICS_TEMPLATE)
        return template.render(label=metric_name, datapoints=datapoints)

    @amzn_request_id
    def list_metrics(self):
        metrics = self.cloudwatch_backend.get_all_metrics()
        template = self.response_template(LIST_METRICS_TEMPLATE)
        return template.render(metrics=metrics)

    @amzn_request_id
    def delete_dashboards(self):
        dashboards = self._get_multi_param('DashboardNames.member')
        if dashboards is None:
            return self._error('InvalidParameterValue', 'Need at least 1 dashboard')

        status, error = self.cloudwatch_backend.delete_dashboards(dashboards)
        if not status:
            return self._error('ResourceNotFound', error)

        template = self.response_template(DELETE_DASHBOARD_TEMPLATE)
        return template.render()

    @amzn_request_id
    def describe_alarm_history(self):
        raise NotImplementedError()

    @amzn_request_id
    def describe_alarms_for_metric(self):
        raise NotImplementedError()

    @amzn_request_id
    def disable_alarm_actions(self):
        raise NotImplementedError()

    @amzn_request_id
    def enable_alarm_actions(self):
        raise NotImplementedError()

    @amzn_request_id
    def get_dashboard(self):
        dashboard_name = self._get_param('DashboardName')

        dashboard = self.cloudwatch_backend.get_dashboard(dashboard_name)
        if dashboard is None:
            return self._error('ResourceNotFound', 'Dashboard does not exist')

        template = self.response_template(GET_DASHBOARD_TEMPLATE)
        return template.render(dashboard=dashboard)

    @amzn_request_id
    def list_dashboards(self):
        prefix = self._get_param('DashboardNamePrefix', '')

        dashboards = self.cloudwatch_backend.list_dashboards(prefix)

        template = self.response_template(LIST_DASHBOARD_RESPONSE)
        return template.render(dashboards=dashboards)

    @amzn_request_id
    def put_dashboard(self):
        name = self._get_param('DashboardName')
        body = self._get_param('DashboardBody')

        try:
            json.loads(body)
        except ValueError:
            return self._error('InvalidParameterInput', 'Body is invalid JSON')

        self.cloudwatch_backend.put_dashboard(name, body)

        template = self.response_template(PUT_DASHBOARD_RESPONSE)
        return template.render()

    @amzn_request_id
    def set_alarm_state(self):
        alarm_name = self._get_param('AlarmName')
        reason = self._get_param('StateReason')
        reason_data = self._get_param('StateReasonData')
        state_value = self._get_param('StateValue')

        self.cloudwatch_backend.set_alarm_state(alarm_name, reason, reason_data, state_value)

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
                <AlarmArn>{{ alarm.arn }}</AlarmArn>
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
    </DescribeAlarmsResult>
</DescribeAlarmsResponse>"""

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

GET_METRIC_STATISTICS_TEMPLATE = """<GetMetricStatisticsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         {{ request_id }}
      </RequestId>
   </ResponseMetadata>

  <GetMetricStatisticsResult>
      <Label>{{ label }}</Label>
      <Datapoints>
        {% for datapoint in datapoints %}
            <Datapoint>
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
              <Unit>{{ datapoint.unit }}</Unit>
            </Datapoint>
        {% endfor %}
      </Datapoints>
    </GetMetricStatisticsResult>
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
        <NextToken>
            96e88479-4662-450b-8a13-239ded6ce9fe
        </NextToken>
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
