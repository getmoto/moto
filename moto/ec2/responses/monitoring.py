from moto.core.responses import BaseResponse


class Monitoring(BaseResponse):
    def monitor_instances(self):
        raise NotImplementedError('Monitoring.monitor_instances is not yet implemented')

    def unmonitor_instances(self):
        raise NotImplementedError('Monitoring.unmonitor_instances is not yet implemented')
