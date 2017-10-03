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


class InvalidRequestException(AWSError):
    CODE = 'InvalidRequestException'


class InvalidParameterValueException(AWSError):
    CODE = 'InvalidParameterValue'


class ValidationError(AWSError):
    CODE = 'ValidationError'


class InternalFailure(AWSError):
    CODE = 'InternalFailure'
    STATUS = 500


class ClientException(AWSError):
    CODE = 'ClientException'
    STATUS = 400
