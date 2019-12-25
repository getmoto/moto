from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidInputException(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidInputException, self).__init__(
            "InvalidInputException",
            "You provided a value that does not match the required pattern.",
        )
