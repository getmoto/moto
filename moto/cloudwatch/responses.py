from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.core.utils import camelcase_to_underscores
from .models import cloudwatch_backend


class CloudWatchResponse(BaseResponse):

    def _get_param(self, param_name):
        return self.querystring.get(param_name, [None])[0]

    def _get_multi_param(self, param_prefix):
        return [value[0] for key, value in self.querystring.items() if key.startswith(param_prefix)]

    def _get_list_prefix(self, param_prefix):
        results = []
        param_index = 1
        while True:
            index_prefix = "{}.{}.".format(param_prefix, param_index)
            new_items = {
                camelcase_to_underscores(key.replace(index_prefix, "")): value[0]
                for key, value in self.querystring.items()
                if key.startswith(index_prefix)
            }
            if not new_items:
                break
            results.append(new_items)
            param_index += 1
        return results

    def put_metric_alarm(self):
        name = self._get_param('AlarmName')
        comparison_operator = self._get_param('ComparisonOperator')
        evaluation_periods = self._get_param('EvaluationPeriods')
        period = self._get_param('Period')
        threshold = self._get_param('Threshold')
        statistic = self._get_param('Statistic')
        description = self._get_param('AlarmDescription')
        dimensions = self._get_list_prefix('Dimensions.member')
        alarm_actions = self._get_multi_param('AlarmActions')
        ok_actions = self._get_multi_param('OKActions')
        insufficient_data_actions = self._get_multi_param("InsufficientDataActions")
        unit = self._get_param('Unit')
        alarm = cloudwatch_backend.put_metric_alarm(name, comparison_operator,
                                                    evaluation_periods, period,
                                                    threshold, statistic,
                                                    description, dimensions,
                                                    alarm_actions, ok_actions,
                                                    insufficient_data_actions,
                                                    unit)
        template = Template(PUT_METRIC_ALARM_TEMPLATE)
        return template.render(alarm=alarm)

    def describe_alarms(self):
        alarms = cloudwatch_backend.get_all_alarms()
        template = Template(DESCRIBE_ALARMS_TEMPLATE)
        return template.render(alarms=alarms)

    def delete_alarms(self):
        alarm_names = self._get_multi_param('AlarmNames.member')
        cloudwatch_backend.delete_alarms(alarm_names)
        template = Template(DELETE_METRIC_ALARMS_TEMPLATE)
        return template.render()

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

DELETE_METRIC_ALARMS_TEMPLATE = """<DeleteMetricAlarmResponse xmlns="http://monitoring.amazonaws.com/doc/2010-08-01/">
   <ResponseMetadata>
      <RequestId>
         2690d7eb-ed86-11dd-9877-6fad448a8419
      </RequestId>
   </ResponseMetadata>
</DeleteMetricAlarmResponse>"""
