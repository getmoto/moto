"""Exceptions raised by the acmpca service."""

from moto.core.exceptions import ServiceException


class ACMPCAException(ServiceException):
    pass


class ResourceNotFoundException(ACMPCAException):
    code = "ResourceNotFoundException"

    def __init__(self, arn: str):
        super().__init__(f"Resource {arn} not found")


class InvalidS3ObjectAclInCrlConfiguration(ACMPCAException):
    code = "InvalidArgsException"

    def __init__(self, value: str):
        super().__init__(
            f"Invalid value for parameter RevocationConfiguration.CrlConfiguration.S3ObjectAcl, value: {value}, valid values: ['PUBLIC_READ', 'BUCKET_OWNER_FULL_CONTROL']"
        )


class InvalidStateException(ACMPCAException):
    code = "InvalidStateException"

    def __init__(self, arn: str):
        super().__init__(
            f"The certificate authority {arn} is not in the correct state to have a certificate signing request."
        )


class MalformedCertificateAuthorityException(ACMPCAException):
    code = "MalformedCertificateException"
    message = "Malformed certificate."


class InvalidPolicyException(ACMPCAException):
    code = "InvalidPolicyException"
    message = "The resource policy is invalid or is missing a required statement."


class LockoutPreventedException(ACMPCAException):
    code = "LockoutPreventedException"
    message = "The current action was prevented because it would lock the caller out from performing subsequent actions."


class ConcurrentModificationException(ACMPCAException):
    code = "ConcurrentModificationException"
    message = "A previous update to your private CA is still ongoing."


class RequestInProgressException(ACMPCAException):
    code = "RequestInProgressException"
