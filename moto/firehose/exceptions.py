"""Exceptions raised by the Firehose service."""
from moto.core.exceptions import JsonRESTError


class InvalidArgumentException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidArgumentException", message)


class LimitExceededException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("LimitExceededException", message)


class ResourceInUseException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ResourceInUseException", message)


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidKMSResourceException", message)


class InvalidKMSResourceException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidKMSResourceException", message)
