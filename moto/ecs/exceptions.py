from __future__ import unicode_literals
from moto.core.exceptions import RESTError, JsonRESTError


class ServiceNotFoundException(RESTError):
    code = 400

    def __init__(self):
        super(ServiceNotFoundException, self).__init__(
            error_type="ServiceNotFoundException", message="Service not found."
        )


class TaskDefinitionNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(TaskDefinitionNotFoundException, self).__init__(
            error_type="ClientException",
            message="The specified task definition does not exist.",
        )


class RevisionNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(RevisionNotFoundException, self).__init__(
            error_type="ClientException", message="Revision is missing.",
        )


class TaskSetNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(TaskSetNotFoundException, self).__init__(
            error_type="ClientException",
            message="The specified task set does not exist.",
        )


class ClusterNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(ClusterNotFoundException, self).__init__(
            error_type="ClientException", message="Cluster not found",
        )


class InvalidParameterException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterException, self).__init__(
            error_type="ClientException", message=message,
        )
