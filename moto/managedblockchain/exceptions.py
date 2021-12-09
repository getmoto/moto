import json
from functools import wraps
from werkzeug.exceptions import HTTPException


def exception_handler(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ManagedBlockchainClientError as err:
            return err.code, err.get_headers(), err.description

    return _wrapper


class ManagedBlockchainClientError(HTTPException):
    code = 400

    def __init__(self, error_type, message, **kwargs):
        super(HTTPException, self).__init__()
        self.error_type = error_type
        self.message = message
        self.description = json.dumps({"message": self.message})

    def get_headers(self, *args, **kwargs):
        return [
            ("Content-Type", "application/json"),
            ("x-amzn-ErrorType", self.error_type),
        ]

    @property
    def response(self):
        return self.get_body()

    def get_body(self, *args, **kwargs):
        return self.description


class BadRequestException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        super(BadRequestException, self).__init__(
            "BadRequestException",
            "An error occurred (BadRequestException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )


class InvalidRequestException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException",
            "An error occurred (InvalidRequestException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )


class ResourceNotFoundException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "An error occurred (ResourceNotFoundException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )


class ResourceAlreadyExistsException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 409
        super(ResourceAlreadyExistsException, self).__init__(
            "ResourceAlreadyExistsException",
            "An error occurred (ResourceAlreadyExistsException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )


class ResourceLimitExceededException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 429
        super(ResourceLimitExceededException, self).__init__(
            "ResourceLimitExceededException",
            "An error occurred (ResourceLimitExceededException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )
