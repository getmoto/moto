import json
from moto.core.responses import BaseResponse
from .models import cloudwatch_backends


class CloudWatchResponse(BaseResponse):

    @property
    def cloudwatch_backend(self):
        return cloudwatch_backends[self.region]

    def _error(self, code, message, status=400):
        template = self.response_template(ERROR_RESPONSE_TEMPLATE)
        return template.render(code=code, message=message), dict(status=status)

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

    def delete_alarms(self):
        alarm_names = self._get_multi_param('AlarmNames.member')
        self.cloudwatch_backend.delete_alarms(alarm_names)
        template = self.response_template(DELETE_METRIC_ALARMS_TEMPLATE)
        return template.render()

    def put_metric_data(self):
        namespace = self._get_param('Namespace')
        metric_data = []
        metric_index = 1
        while True:
            try:
                metric_name = self.querystring[
                    'MetricData.member.{0}.MetricName'.format(metric_index)][0]
            except KeyError:
                break
            value = self.querystring.get(
                'MetricData.member.{0}.Value'.format(metric_index), [None])[0]
            dimensions = []
            dimension_index = 1
            while True:
                try:
                    dimension_name = self.querystring[
                        'MetricData.member.{0}.Dimensions.member.{1}.Name'.format(metric_index, dimension_index)][0]
                except KeyError:
                    break
                dimension_value = self.querystring[
                    'MetricData.member.{0}.Dimensions.member.{1}.Value'.format(metric_index, dimension_index)][0]
                dimensions.append(
                    {'name': dimension_name, 'value': dimension_value})
                dimension_index += 1
            metric_data.append([metric_name, value, dimensions])
            metric_index += 1
        self.cloudwatch_backend.put_metric_data(namespace, metric_data)
        template = self.response_template(PUT_METRIC_DATA_TEMPLATE)
        return template.render()

    def list_metrics(self):
        metrics = self.cloudwatch_backend.get_all_metrics()
        template = self.response_template(LIST_METRICS_TEMPLATE)
        return template.render(metrics=metrics)

    def delete_dashboards(self):
        dashboards = self._get_multi_param('DashboardNames.member')
        if dashboards is None:
            return self._error('InvalidParameterValue', 'Need at least 1 dashboard')

        status, error = self.cloudwatch_backend.delete_dashboards(dashboards)
        if not status:
            return self._error('ResourceNotFound', error)

        template = self.response_template(DELETE_DASHBOARD_TEMPLATE)
        return template.render()

    def describe_alarm_history(self):
        raise NotImplementedError()

    def describe_alarms_for_metric(self):
        raise NotImplementedError()

    def disable_alarm_actions(self):
        raise NotImplementedError()

    def enable_alarm_actions(self):
        raise NotImplementedError()

    def get_dashboard(self):
        dashboard_name = self._get_param('DashboardName')

        dashboard = self.cloudwatch_backend.get_dashboard(dashboard_name)
        if dashboard is None:
            return self._error('ResourceNotFound', 'Dashboard does not exist')

        template = self.response_template(GET_DASHBOARD_TEMPLATE)
        return template.render(dashboard=dashboard)

    def get_metric_statistics(self):
        raise NotImplementedError()

    def list_dashboards(self):
        prefix = self._get_param('DashboardNamePrefix', '')

        dashboards = self.cloudwatch_backend.list_dashboards(prefix)

        template = self.response_template(LIST_DASHBOARD_RESPONSE)
        return template.render(dashboards=dashboards)

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

    def set_alarm_state(self):
        raise NotImplementedError()


PUT_METRIC_ALARM_TEMPLATE = """<PutMetricAlarmResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
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
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</DeleteMetricAlarmResponse>"""

PUT_METRIC_DATA_TEMPLATE = """<PutMetricDataResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</PutMetricDataResponse>"""

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
    <RequestId>44b1d4d8-9fa3-11e7-8ad3-41b86ac5e49e</RequestId>
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
    <RequestId>c3773873-9fa5-11e7-b315-31fcc9275d62</RequestId>
  </ResponseMetadata>
</ListDashboardsResponse>"""

DELETE_DASHBOARD_TEMPLATE = """<DeleteDashboardsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <DeleteDashboardsResult/>
  <ResponseMetadata>
    <RequestId>68d1dc8c-9faa-11e7-a694-df2715690df2</RequestId>
  </ResponseMetadata>
</DeleteDashboardsResponse>"""

GET_DASHBOARD_TEMPLATE = """<GetDashboardResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <GetDashboardResult>
    <DashboardArn>{{ dashboard.arn }}</DashboardArn>
    <DashboardBody>{{ dashboard.body }}</DashboardBody>
    <DashboardName>{{ dashboard.name }}</DashboardName>
  </GetDashboardResult>
  <ResponseMetadata>
    <RequestId>e3c16bb0-9faa-11e7-b315-31fcc9275d62</RequestId>
  </ResponseMetadata>
</GetDashboardResponse>
"""

ERROR_RESPONSE_TEMPLATE = """<ErrorResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
  <Error>
    <Type>Sender</Type>
    <Code>{{ code }}</Code>
    <Message>{{ message }}</Message>
  </Error>
  <RequestId>5e45fd1e-9fa3-11e7-b720-89e8821d38c4</RequestId>
</ErrorResponse>"""
