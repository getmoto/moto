from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import cloudwatch_backend


class CloudWatchResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def put_metric_alarm(self):
        name = self._get_param('AlarmName')
        comparison_operator = self._get_param('ComparisonOperator')
        alarm = cloudwatch_backend.put_metric_alarm(name, comparison_operator)
        template = Template(PUT_METRIC_ALARM_TEMPLATE)
        return template.render(alarm=alarm)

    def describe_alarms(self):
        alarms = cloudwatch_backend.get_all_alarms()
        template = Template(DESCRIBE_ALARMS_TEMPLATE)
        return template.render(alarms=alarms)


PUT_METRIC_ALARM_TEMPLATE = """<PutMetricAlarmResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</PutMetricAlarmResponse>"""

DESCRIBE_ALARMS_TEMPLATE = """<DescribeAlarmsResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
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
</DescribeAlarmsResponse>"""