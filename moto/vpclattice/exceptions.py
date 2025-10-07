"""Exceptions raised by the vpclattice service."""

from moto.core.exceptions import JsonRESTError

 
class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message: str):
        super().__init__("ValidationException", message)


class ThrottlingException(JsonRESTError):
    code = 400

    def __init__(self, message: str):
        super().__init__("ThrottlingException", message)


class ConflictException(JsonRESTError):
    code = 400

    def __init__(self, message: str):
        super().__init__("ConflictException", message)


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message: str):
        super().__init__("ResourceNotFoundException", message)


class AccessDeniedException(JsonRESTError):
    code = 403

    def __init__(self, message: str):
        super().__init__("AccessDeniedException", message)


class ServiceQuotaExceededException(JsonRESTError):
    code = 400

    def __init__(self, message: str):
        super().__init__("ServiceQuotaExceededException", message)
