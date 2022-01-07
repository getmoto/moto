from moto.core.exceptions import JsonRESTError


class AWSValidationException(JsonRESTError):
    def __init__(self, message, **kwargs):
        super().__init__("ValidationException", message, **kwargs)
