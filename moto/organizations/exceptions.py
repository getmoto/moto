from moto.core.exceptions import JsonRESTError


class AccountAlreadyRegisteredException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AccountAlreadyRegisteredException, self).__init__(
            "AccountAlreadyRegisteredException",
            "The provided account is already a delegated administrator for your organization.",
        )


class AccountNotRegisteredException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AccountNotRegisteredException, self).__init__(
            "AccountNotRegisteredException",
            "The provided account is not a registered delegated administrator for your organization.",
        )


class AccountNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AccountNotFoundException, self).__init__(
            "AccountNotFoundException", "You specified an account that doesn't exist."
        )


class AWSOrganizationsNotInUseException(JsonRESTError):
    code = 400

    def __init__(self):
        super(AWSOrganizationsNotInUseException, self).__init__(
            "AWSOrganizationsNotInUseException",
            "Your account is not a member of an organization.",
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


class PolicyTypeAlreadyEnabledException(JsonRESTError):
    code = 400

    def __init__(self):
        super(PolicyTypeAlreadyEnabledException, self).__init__(
            "PolicyTypeAlreadyEnabledException",
            "The specified policy type is already enabled.",
        )


class PolicyTypeNotEnabledException(JsonRESTError):
    code = 400

    def __init__(self):
        super(PolicyTypeNotEnabledException, self).__init__(
            "PolicyTypeNotEnabledException",
            "This operation can be performed only for enabled policy types.",
        )


class RootNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(RootNotFoundException, self).__init__(
            "RootNotFoundException", "You specified a root that doesn't exist."
        )


class TargetNotFoundException(JsonRESTError):
    code = 400

    def __init__(self):
        super(TargetNotFoundException, self).__init__(
            "TargetNotFoundException", "You specified a target that doesn't exist."
        )
