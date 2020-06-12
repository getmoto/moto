from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class InvalidInputException(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidInputException, self).__init__(
            "InvalidInputException",
            "You provided a value that does not match the required pattern.",
        )


class DuplicateOrganizationalUnitException(JsonRESTError):
    code = 400

    def __init__(self):
        super(DuplicateOrganizationalUnitException, self).__init__(
            "DuplicateOrganizationalUnitException",
            "An OU with the same name already exists.",
        )
