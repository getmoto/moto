from moto.core.exceptions import RESTError


class InvalidFormat(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__(__class__.__name__, message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__(__class__.__name__, message)


class ResourceNotFound(RESTError):
    code = 404

    def __init__(self):
        super().__init__(__class__.__name__, "Unknown")


class ResourceNotFoundException(RESTError):
    code = 404

    def __init__(self):
        super().__init__(__class__.__name__, "Unknown")


class ValidationError(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__(__class__.__name__, message)
