from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class ManagedBlockchainClientError(RESTError):
    code = 400


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
