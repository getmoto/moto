from moto.core.exceptions import RESTError


class AutoscalingClientError(RESTError):
    code = 400


class ResourceContentionError(RESTError):
    code = 500

    def __init__(self):
        super().__init__(
            "ResourceContentionError",
            "You already have a pending update to an Auto Scaling resource (for example, a group, instance, or load balancer).",
        )


class InvalidInstanceError(AutoscalingClientError):
    def __init__(self, instance_id):
        super().__init__(
            "ValidationError", "Instance [{0}] is invalid.".format(instance_id)
        )


class ValidationError(AutoscalingClientError):
    def __init__(self, message):
        super().__init__("ValidationError", message)
