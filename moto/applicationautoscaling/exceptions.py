from moto.core.exceptions import JsonRESTError, ServiceException


class AWSValidationException(JsonRESTError):
    def __init__(self, message: str) -> None:
        super().__init__("ValidationException", message)


class ResourceNotFoundException(ServiceException):
    code = "ResourceNotFoundException"


class TooManyTagsException(ServiceException):
    code = "TooManyTagsException"
