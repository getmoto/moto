from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self):
        super().__init__("ResourceNotFoundException", "Query does not exist.")


class ValidationException(JsonRESTError):
    def __init__(self, message):
        super().__init__("ValidationException", message)
