from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class AccountAlreadyRegisteredException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AccountAlreadyRegisteredException, self).__init__(
            "AccountAlreadyRegisteredException",
            "The provided account is already a delegated administrator for your organization.",
        )


class AccountNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AccountNotFoundException, self).__init__(
            "AccountNotFoundException", "You specified an account that doesn't exist."
        )


class ConstraintViolationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ConstraintViolationException, self).__init__(
            "ConstraintViolationException", message
        )


class InvalidInputException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidInputException, self).__init__("InvalidInputException", message)


class DuplicateOrganizationalUnitException(JsonRESTError):
    code = 400

    def __init__(self):
        super(DuplicateOrganizationalUnitException, self).__init__(
            "DuplicateOrganizationalUnitException",
            "An OU with the same name already exists.",
        )


class DuplicatePolicyException(JsonRESTError):
    code = 400

    def __init__(self):
        super(DuplicatePolicyException, self).__init__(
            "DuplicatePolicyException", "A policy with the same name already exists."
        )
