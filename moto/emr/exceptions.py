from moto.core.exceptions import JsonRESTError


class InvalidRequestException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException", message, **kwargs
        )


class ValidationException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(ValidationException, self).__init__(
            "ValidationException", message, **kwargs
        )


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", message, **kwargs
        )
