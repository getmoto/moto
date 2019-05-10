from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class NotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(NotFoundException, self).__init__(
            "NotFoundException", message)


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__(
            "ValidationException", message)


class AlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(AlreadyExistsException, self).__init__(
            "AlreadyExistsException", message)


class NotAuthorizedException(JsonRESTError):
    code = 400

    def __init__(self):
        super(NotAuthorizedException, self).__init__(
            "NotAuthorizedException", None)

        self.description = '{"__type":"NotAuthorizedException"}'
