from moto.core.exceptions import ServiceException


class DevOpsAgentClientError(ServiceException):
    pass


class ResourceNotFoundException(DevOpsAgentClientError):
    code = "ResourceNotFoundException"


class ConflictException(DevOpsAgentClientError):
    code = "ConflictException"


class ValidationException(DevOpsAgentClientError):
    code = "ValidationException"
