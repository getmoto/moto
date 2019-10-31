from __future__ import unicode_literals
from moto.core.exceptions import RESTError, JsonRESTError


class ServiceNotFoundException(RESTError):
    code = 400

    def __init__(self, service_name):
        super(ServiceNotFoundException, self).__init__(
            error_type="ServiceNotFoundException",
            message="The service {0} does not exist".format(service_name),
            template="error_json",
        )


class TaskDefinitionNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(TaskDefinitionNotFoundException, self).__init__(
            error_type="ClientException",
            message="The specified task definition does not exist.",
        )
