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
