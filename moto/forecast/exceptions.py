from moto.core.exceptions import ServiceException


class ForecastException(ServiceException):
    pass


class InvalidInputException(ForecastException):
    code = "InvalidInputException"


class ResourceAlreadyExistsException(ForecastException):
    code = "ResourceAlreadyExistsException"


class ResourceNotFoundException(ForecastException):
    code = "ResourceNotFoundException"


class ResourceInUseException(ForecastException):
    code = "ResourceInUseException"


class LimitExceededException(ForecastException):
    code = "LimitExceededException"


class ValidationException(ForecastException):
    code = "ValidationException"
