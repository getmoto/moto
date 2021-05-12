from __future__ import unicode_literals
from werkzeug.exceptions import HTTPException
from jinja2 import DictLoader, Environment


ERROR_JSON_RESPONSE = """{
    "message": "{{message}}"
}
"""


class ManagedBlockchainClientError(HTTPException):
    code = 400

    templates = {
        "error": ERROR_JSON_RESPONSE,
    }

    def __init__(self, error_type, message, **kwargs):
        super(HTTPException, self).__init__()
        env = Environment(loader=DictLoader(self.templates))
        self.error_type = error_type
        self.message = message
        self.description = env.get_template("error").render(
            error_type=error_type, message=message, **kwargs
        )

    def get_headers(self, *args, **kwargs):
        return [
            ("Content-Type", "application/json"),
            ("x-amzn-ErrorType", self.error_type),
        ]

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
