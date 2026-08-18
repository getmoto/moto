from moto.core.exceptions import JsonRESTError


class PaymentCryptographyError(JsonRESTError):
    code = 400

    def __init__(self, error_type: str, message: str):
        super().__init__(error_type, message)


class ConflictException(PaymentCryptographyError):
    code = 409

    def __init__(self, message: str):
        super().__init__("ConflictException", message)


class ResourceNotFoundException(PaymentCryptographyError):
    code = 404

    def __init__(self, message: str):
        super().__init__("ResourceNotFoundException", message)


class ValidationException(PaymentCryptographyError):
    def __init__(self, message: str):
        super().__init__("ValidationException", message)
