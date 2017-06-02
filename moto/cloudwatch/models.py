from moto.core import BaseBackend, BaseModel
import boto.ec2.cloudwatch
import datetime


class Dimension(object):

    def __init__(self, name, value):
        self.name = name
        self.value = value


class FakeAlarm(BaseModel):

    def __init__(self, name, namespace, metric_name, comparison_operator, evaluation_periods,
                 period, threshold, statistic, description, dimensions, alarm_actions,
                 ok_actions, insufficient_data_actions, unit):
        self.name = name
        self.namespace = namespace
        self.metric_name = metric_name
        self.comparison_operator = comparison_operator
        self.evaluation_periods = evaluation_periods
        self.period = period
        self.threshold = threshold
        self.statistic = statistic
        self.description = description
        self.dimensions = [Dimension(dimension['name'], dimension[
                                     'value']) for dimension in dimensions]
        self.alarm_actions = alarm_actions
        self.ok_actions = ok_actions
        self.insufficient_data_actions = insufficient_data_actions
        self.unit = unit
        self.state_updated_timestamp = datetime.datetime.utcnow()
        self.configuration_updated_timestamp = datetime.datetime.utcnow()


class MetricDatum(BaseModel):

    def __init__(self, namespace, name, value, dimensions):
        self.namespace = namespace
        self.name = name
        self.value = value
        self.dimensions = [Dimension(dimension['name'], dimension[
                                     'value']) for dimension in dimensions]


class CloudWatchBackend(BaseBackend):

    def __init__(self):
        self.alarms = {}
        self.metric_data = []

    def put_metric_alarm(self, name, namespace, metric_name, comparison_operator, evaluation_periods,
                         period, threshold, statistic, description, dimensions,
                         alarm_actions, ok_actions, insufficient_data_actions, unit):
        alarm = FakeAlarm(name, namespace, metric_name, comparison_operator, evaluation_periods, period,
                          threshold, statistic, description, dimensions, alarm_actions,
                          ok_actions, insufficient_data_actions, unit)
        self.alarms[name] = alarm
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
        return [
            alarm
            for alarm in self.alarms.values()
            if alarm.name in alarm_names
        ]

    def get_alarms_by_state_value(self, state):
        raise NotImplementedError(
            "DescribeAlarm by state is not implemented in moto."
        )

    def delete_alarms(self, alarm_names):
        for alarm_name in alarm_names:
            self.alarms.pop(alarm_name, None)

    def put_metric_data(self, namespace, metric_data):
        for name, value, dimensions in metric_data:
            self.metric_data.append(MetricDatum(
                namespace, name, value, dimensions))

    def get_all_metrics(self):
        return self.metric_data


class LogGroup(BaseModel):

    def __init__(self, spec):
        # required
        self.name = spec['LogGroupName']
        # optional
        self.tags = spec.get('Tags', [])

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        spec = {
            'LogGroupName': properties['LogGroupName']
        }
        optional_properties = 'Tags'.split()
        for prop in optional_properties:
            if prop in properties:
                spec[prop] = properties[prop]
        return LogGroup(spec)


cloudwatch_backends = {}
for region in boto.ec2.cloudwatch.regions():
    cloudwatch_backends[region.name] = CloudWatchBackend()
