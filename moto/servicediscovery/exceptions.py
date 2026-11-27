"""Exceptions raised by the servicediscovery service."""

from moto.core.exceptions import ServiceException


class ServiceDiscoveryException(ServiceException):
    pass


class OperationNotFound(ServiceDiscoveryException):
    code = "OperationNotFound"


class NamespaceNotFound(ServiceDiscoveryException):
    code = "NamespaceNotFound"


class ServiceNotFound(ServiceDiscoveryException):
    code = "ServiceNotFound"


class InstanceNotFound(ServiceDiscoveryException):
    code = "InstanceNotFound"


class ConflictingDomainExists(ServiceDiscoveryException):
    code = "ConflictingDomainExists"


class CustomHealthNotFound(ServiceDiscoveryException):
    code = "CustomHealthNotFound"


class InvalidInput(ServiceDiscoveryException):
    code = "InvalidInput"


class ServiceAttributesLimitExceededException(ServiceDiscoveryException):
    code = "ServiceAttributesLimitExceededException"
