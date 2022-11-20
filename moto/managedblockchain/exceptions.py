import json
from moto.core.exceptions import JsonRESTError
from functools import wraps


def exception_handler(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ManagedBlockchainClientError as err:
            return err.code, err.get_headers(), err.description

    return _wrapper


class ManagedBlockchainClientError(JsonRESTError):
    def __init__(self, error_type, message):
        super().__init__(error_type=error_type, message=message)
        self.error_type = error_type
        self.message = message
        self.description = json.dumps({"message": self.message})

    def get_headers(self, *args, **kwargs):  # pylint: disable=unused-argument
        return [
            ("Content-Type", "application/json"),
            ("x-amzn-ErrorType", self.error_type),
        ]

    def get_body(self, *args, **kwargs):  # pylint: disable=unused-argument
        return self.description


class BadRequestException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        super().__init__(
            "BadRequestException",
            f"An error occurred (BadRequestException) when calling the {pretty_called_method} operation: {operation_error}",
        )


class InvalidRequestException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        super().__init__(
            "InvalidRequestException",
            f"An error occurred (InvalidRequestException) when calling the {pretty_called_method} operation: {operation_error}",
        )


class ResourceNotFoundException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 404
        super().__init__(
            "ResourceNotFoundException",
            f"An error occurred (ResourceNotFoundException) when calling the {pretty_called_method} operation: {operation_error}",
        )


class ResourceAlreadyExistsException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 409
        super().__init__(
            "ResourceAlreadyExistsException",
            f"An error occurred (ResourceAlreadyExistsException) when calling the {pretty_called_method} operation: {operation_error}",
        )


class ResourceLimitExceededException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 429
        super().__init__(
            "ResourceLimitExceededException",
            f"An error occurred (ResourceLimitExceededException) when calling the {pretty_called_method} operation: {operation_error}",
        )
