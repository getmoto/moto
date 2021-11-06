from moto.core.responses import BaseResponse


class Monitoring(BaseResponse):
    def monitor_instances(self):
        if self.is_not_dryrun("MonitorInstances"):
            raise NotImplementedError(
                "Monitoring.monitor_instances is not yet implemented"
            )

    def unmonitor_instances(self):
        if self.is_not_dryrun("UnMonitorInstances"):
            raise NotImplementedError(
                "Monitoring.unmonitor_instances is not yet implemented"
            )
