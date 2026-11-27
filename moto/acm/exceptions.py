from moto.core.exceptions import ServiceException


class ACMException(ServiceException):
    pass


class AWSValidationException(ACMException):
    code = "ValidationException"


class AWSResourceNotFoundException(ACMException):
    code = "ResourceNotFoundException"


class CertificateNotFound(AWSResourceNotFoundException):
    def __init__(self, arn: str, account_id: str):
        super().__init__(
            f"Certificate with arn {arn} not found in account {account_id}"
        )


class AWSTooManyTagsException(ACMException):
    code = "TooManyTagsException"


class InvalidDomainValidationOptionsException(ACMException):
    code = "InvalidDomainValidationOptionsException"


class LimitExceededException(ACMException):
    code = "LimitExceededException"
