from moto.core.exceptions import JsonRESTError


class ConflictException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(ConflictException, self).__init__("ConflictException", message, **kwargs)


class BadRequestException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super(BadRequestException, self).__init__(
            "BadRequestException", message, **kwargs
        )
