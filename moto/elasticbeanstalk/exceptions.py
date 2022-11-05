from moto.core.exceptions import RESTError


class InvalidParameterValueError(RESTError):
    def __init__(self, message):
        super().__init__("InvalidParameterValue", message)


class ResourceNotFoundException(RESTError):
    def __init__(self, message):
        super().__init__("ResourceNotFoundException", message)
