from __future__ import unicode_literals
from moto.core.exceptions import AWSError


class ExecutionAlreadyExists(AWSError):
    TYPE = "ExecutionAlreadyExists"
    STATUS = 400


class ExecutionDoesNotExist(AWSError):
    TYPE = "ExecutionDoesNotExist"
    STATUS = 400


class InvalidArn(AWSError):
    TYPE = "InvalidArn"
    STATUS = 400


class InvalidName(AWSError):
    TYPE = "InvalidName"
    STATUS = 400


class InvalidExecutionInput(AWSError):
    TYPE = "InvalidExecutionInput"
    STATUS = 400


class StateMachineDoesNotExist(AWSError):
    TYPE = "StateMachineDoesNotExist"
    STATUS = 400


class InvalidToken(AWSError):
    TYPE = "InvalidToken"
    STATUS = 400

    def __init__(self, message="Invalid token"):
        super(InvalidToken, self).__init__("Invalid Token: {}".format(message))


class ResourceNotFound(AWSError):
    TYPE = "ResourceNotFound"
    STATUS = 400

    def __init__(self, arn):
        super(ResourceNotFound, self).__init__("Resource not found: '{}'".format(arn))
