from .generic_type import GenericType


class ActivityType(GenericType):

    @property
    def _configuration_keys(self):
        return [
            "defaultTaskHeartbeatTimeout",
            "defaultTaskScheduleToCloseTimeout",
            "defaultTaskScheduleToStartTimeout",
            "defaultTaskStartToCloseTimeout",
        ]

    @property
    def kind(self):
        return "activity"
