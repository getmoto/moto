from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class AutoscalingClientError(RESTError):
    code = 400


class ResourceContentionError(RESTError):
    code = 500

    def __init__(self):
        super(ResourceContentionError, self).__init__(
            "ResourceContentionError",
            "You already have a pending update to an Auto Scaling resource (for example, a group, instance, or load balancer).")
