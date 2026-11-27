"""Exceptions raised by the route53domains service."""

from moto.core.exceptions import ServiceException


class Route53DomainsException(ServiceException):
    pass


class DomainLimitExceededException(Route53DomainsException):
    code = "DomainLimitExceeded"
    message = (
        "The number of registered domains has exceeded the allowed threshold for this account. If you want to "
        "register more domains please request a higher quota"
    )


class DuplicateRequestException(Route53DomainsException):
    code = "DuplicateRequest"
    message = "The request is already in progress for the domain."


class InvalidInputException(Route53DomainsException):
    code = "InvalidInput"

    def __init__(self, error_msgs: list[str]):
        error_msgs_str = "\n\t".join(error_msgs)
        super().__init__(f"The requested item is not acceptable.\n\t{error_msgs_str}")


class UnsupportedTLDException(Route53DomainsException):
    code = "UnsupportedTLD"

    def __init__(self, tld: str):
        super().__init__(
            f"Amazon Route53 does not support the top-level domain (TLD) `.{tld}`."
        )
