from moto.core.exceptions import ServiceException


class KMSException(ServiceException):
    pass


class NotFoundException(KMSException):
    code = "NotFoundException"


class ValidationException(KMSException):
    code = "ValidationException"


class AlreadyExistsException(KMSException):
    code = "AlreadyExistsException"


class InvalidAliasNameException(KMSException):
    code = "InvalidAliasNameException"
    message = "The specified alias name is not valid."


class AccessDeniedException(KMSException):
    code = "AccessDeniedException"


class InvalidCiphertextException(KMSException):
    code = "InvalidCiphertextException"
    message = ""


class InvalidKeyUsageException(KMSException):
    code = "InvalidKeyUsageException"
    message = ""


class KMSInvalidMacException(KMSException):
    code = "KMSInvalidMacException"
    message = ""


class DisabledException(KMSException):
    code = "DisabledException"

    def __init__(self, key_arn: str):
        super().__init__(f"{key_arn} is disabled.")
