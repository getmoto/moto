from moto.core.responses import BaseResponse
from .models import cloudwatch_backends
import datetime
from moto.cloudwatch.utils import querystring_to_dict


class CloudWatchResponse(BaseResponse):

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
        cloudwatch_backend = cloudwatch_backends[self.region]
        alarm = cloudwatch_backend.put_metric_alarm(
            name,
            namespace,
            metric_name,
            comparison_operator,
            evaluation_periods,
            period,
            threshold,
            statistic,
            description,
            dimensions,
            alarm_actions,
            ok_actions,
            insufficient_data_actions,
            unit)
        template = self.response_template(PUT_METRIC_ALARM_TEMPLATE)
        return template.render(alarm=alarm)

    def describe_alarms(self):
        action_prefix = self._get_param('ActionPrefix')
        alarm_name_prefix = self._get_param('AlarmNamePrefix')
        alarm_names = self._get_multi_param('AlarmNames.member')
        state_value = self._get_param('StateValue')
        cloudwatch_backend = cloudwatch_backends[self.region]

        if action_prefix:
            alarms = cloudwatch_backend.get_alarms_by_action_prefix(
                action_prefix)
        elif alarm_name_prefix:
            alarms = cloudwatch_backend.get_alarms_by_alarm_name_prefix(
                alarm_name_prefix)
        elif alarm_names:
            alarms = cloudwatch_backend.get_alarms_by_alarm_names(alarm_names)
        elif state_value:
            alarms = cloudwatch_backend.get_alarms_by_state_value(state_value)
        else:
            alarms = cloudwatch_backend.get_all_alarms()

        template = self.response_template(DESCRIBE_ALARMS_TEMPLATE)
        return template.render(alarms=alarms)

    def delete_alarms(self):
        alarm_names = self._get_multi_param('AlarmNames.member')
        cloudwatch_backend = cloudwatch_backends[self.region]
        cloudwatch_backend.delete_alarms(alarm_names)
        template = self.response_template(DELETE_METRIC_ALARMS_TEMPLATE)
        return template.render()

    def put_metric_data(self):
        namespace = self._get_param('Namespace')
        data = querystring_to_dict(self.querystring, namespace)
        cloudwatch_backend = cloudwatch_backends[self.region]
        cloudwatch_backend.put_metric_data(namespace, data)
        template = self.response_template(PUT_METRIC_DATA_TEMPLATE)
        return template.render()

    def list_metrics(self):
        cloudwatch_backend = cloudwatch_backends[self.region]
        metrics = cloudwatch_backend.get_all_metrics()
        template = self.response_template(LIST_METRICS_TEMPLATE)
        return template.render(metrics=metrics)


def testdata_fixture():
    test_data = [
        {
            'MetricName': 'test_metric_1',
            'Dimensions': [
                {
                    'Name': 'test_dimension_1',
                    'Value': 'test_val_1'
                },
                {
                    'Name': 'test_dimension_2',
                    'Value': 'test_val_2'
                },
            ],
            'StatisticValues': {
                'SampleCount': 20,
                'Sum': 40,
                'Minimum': 60,
                'Maximum': 80
            },
            'Timestamp': datetime.datetime(2015, 1, 1),
            'Value': 20,
            'Unit': 'Seconds',
            'StorageResolution': 123,
        },
    ]
    return test_data


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
            {% for metricdatum in metric.MetricData %}
            <member>
                <Dimensions>
                    {% for dimension in metricdatum.Dimensions %}
                    <member>
                        <Name>{{ dimension.name }}</Name>dimensions
                        <Value>{{ dimension.value }}</Value>
                    </member>
                    {% endfor %}
                </Dimensions>
                <MetricName>{{ metricdatum.MetricName}}</MetricName>
                <Namespace>{{ metric.Namespace}}</Namespace>
            </member>
            {% endfor %}
            {% endfor %}
        </Metrics>
        <NextToken>
            96e88479-4662-450b-8a13-239ded6ce9fe
        </NextToken>
    </ListMetricsResult>
</ListMetricsResponse>"""
