"""Exceptions raised by the datasync service."""

from moto.core.exceptions import ServiceException


class DataSyncClientError(ServiceException):
    pass


class InvalidRequestException(DataSyncClientError):
    code = "InvalidRequestException"
    message = "The request is not valid."
