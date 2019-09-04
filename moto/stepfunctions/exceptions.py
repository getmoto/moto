from __future__ import unicode_literals
import json


class AWSError(Exception):
    CODE = None
    STATUS = 400

    def __init__(self, message, code=None, status=None):
        self.message = message
        self.code = code if code is not None else self.CODE
        self.status = status if status is not None else self.STATUS

    def response(self):
        return json.dumps({'__type': self.code, 'message': self.message}), dict(status=self.status)


class AccessDeniedException(AWSError):
    CODE = 'AccessDeniedException'
    STATUS = 400


class ExecutionDoesNotExist(AWSError):
    CODE = 'ExecutionDoesNotExist'
    STATUS = 400


class InvalidArn(AWSError):
    CODE = 'InvalidArn'
    STATUS = 400


class InvalidName(AWSError):
    CODE = 'InvalidName'
    STATUS = 400


class StateMachineDoesNotExist(AWSError):
    CODE = 'StateMachineDoesNotExist'
    STATUS = 400
