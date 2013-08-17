from moto.core import BaseBackend


class FakeAlarm(object):
    def __init__(self, name, comparison_operator):
        self.name = name
        self.comparison_operator = comparison_operator


class CloudWatchBackend(BaseBackend):

    def __init__(self):
        self.alarms = {}

    def put_metric_alarm(self, name, comparison_operator):
        alarm = FakeAlarm(name, comparison_operator)
        self.alarms[name] = alarm
        return alarm

    def get_all_alarms(self):
        return self.alarms.values()

cloudwatch_backend = CloudWatchBackend()
