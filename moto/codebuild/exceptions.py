"""Exceptions raised by the codebuild service."""

from moto.core.exceptions import ServiceException


class CodeBuildException(ServiceException):
    pass


class InvalidInputException(CodeBuildException):
    code = "InvalidInputException"


class ResourceNotFoundException(CodeBuildException):
    code = "ResourceNotFoundException"


class ResourceAlreadyExistsException(CodeBuildException):
    code = "ResourceAlreadyExistsException"
