from moto.core.exceptions import ServiceException


class BatchException(ServiceException):
    pass


class InvalidParameterValueException(BatchException):
    code = "InvalidParameterValue"


class ValidationError(BatchException):
    code = "ValidationError"


class ClientException(BatchException):
    code = "ClientException"
