"""Exceptions raised by the servicecatalog service."""

from moto.core.exceptions import ServiceException


class ServiceCatalogException(ServiceException):
    pass


class ResourceNotFoundException(ServiceCatalogException):
    code = "ResourceNotFoundException"


class InvalidParametersException(ServiceCatalogException):
    code = "InvalidParametersException"
