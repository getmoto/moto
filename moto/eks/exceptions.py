from typing import Any

from moto.core.exceptions import ServiceException


class EKSError(ServiceException):
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message)
        # Error members modeled for some exceptions, e.g. clusterName, nodegroupName
        for key, value in kwargs.items():
            setattr(self, key, value)


class ResourceInUseException(EKSError):
    code = "ResourceInUseException"


class ResourceNotFoundException(EKSError):
    code = "ResourceNotFoundException"


class InvalidParameterException(EKSError):
    code = "InvalidParameterException"


class InvalidRequestException(EKSError):
    code = "InvalidRequestException"
