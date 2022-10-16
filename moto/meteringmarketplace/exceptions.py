from moto.core.exceptions import JsonRESTError


class DisabledApiException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="DisabledApiException", message=message)


class InternalServiceErrorException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="InternalServiceErrorException", message=message)


class InvalidCustomerIdentifierException(JsonRESTError):
    def __init__(self, message):
        super().__init__(
            error_type="InvalidCustomerIdentifierException", message=message
        )


class InvalidProductCodeException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="InvalidProductCodeException", message=message)


class InvalidUsageDimensionException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="InvalidUsageDimensionException", message=message)


class ThrottlingException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="ThrottlingException", message=message)


class TimestampOutOfBoundsException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="TimestampOutOfBoundsException", message=message)
