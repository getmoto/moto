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


class ResourceNotFoundException(ManagedBlockchainClientError):
    def __init__(self, pretty_called_method, operation_error):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "An error occurred (BadRequestException) when calling the {0} operation: {1}".format(
                pretty_called_method, operation_error
            ),
        )
