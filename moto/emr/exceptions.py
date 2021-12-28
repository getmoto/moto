from moto.core.exceptions import JsonRESTError


class InvalidRequestException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__("InvalidRequestException", message, **kwargs)


class ValidationException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__("ValidationException", message, **kwargs)


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__("ResourceNotFoundException", message, **kwargs)
