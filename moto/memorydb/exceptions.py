"""Exceptions raised by the memorydb service."""

from moto.core.exceptions import ServiceException


class MemoryDBClientError(ServiceException):
    pass


class ClusterAlreadyExistsFault(MemoryDBClientError):
    code = "ClusterAlreadyExistsFault"


class InvalidSubnetError(MemoryDBClientError):
    code = "InvalidSubnet"

    def __init__(self, subnet_identifier: list[str]):
        super().__init__(f"Subnet {subnet_identifier} not found.")


class SubnetGroupAlreadyExistsFault(MemoryDBClientError):
    code = "SubnetGroupAlreadyExistsFault"


class ClusterNotFoundFault(MemoryDBClientError):
    code = "ClusterNotFoundFault"


class SnapshotAlreadyExistsFault(MemoryDBClientError):
    code = "SnapshotAlreadyExistsFault"


class SnapshotNotFoundFault(MemoryDBClientError):
    code = "SnapshotNotFoundFault"


class SubnetGroupNotFoundFault(MemoryDBClientError):
    code = "SubnetGroupNotFoundFault"


class TagNotFoundFault(MemoryDBClientError):
    code = "TagNotFoundFault"


class InvalidParameterValueException(MemoryDBClientError):
    code = "InvalidParameterValueException"


class SubnetGroupInUseFault(MemoryDBClientError):
    code = "SubnetGroupInUseFault"


class UserAlreadyExistsFault(MemoryDBClientError):
    code = "UserAlreadyExistsFault"


class UserNotFoundFault(MemoryDBClientError):
    code = "UserNotFoundFault"
