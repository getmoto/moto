"""Exceptions raised by the codedeploy service."""

from moto.core.exceptions import ServiceException


class CodeDeployException(ServiceException):
    pass


class ApplicationDoesNotExistException(CodeDeployException):
    code = "ApplicationDoesNotExistException"


class DeploymentDoesNotExistException(CodeDeployException):
    code = "DeploymentDoesNotExistException"


class ApplicationAlreadyExistsException(CodeDeployException):
    code = "ApplicationAlreadyExistsException"


class ApplicationNameRequiredException(CodeDeployException):
    code = "ApplicationNameRequiredException"


class DeploymentGroupAlreadyExistsException(CodeDeployException):
    code = "DeploymentGroupAlreadyExistsException"


class DeploymentGroupNameRequiredException(CodeDeployException):
    code = "DeploymentGroupNameRequiredException"


class DeploymentGroupDoesNotExistException(CodeDeployException):
    code = "DeploymentGroupDoesNotExistException"


class InvalidTimeRangeException(CodeDeployException):
    code = "InvalidTimeRangeException"
