from __future__ import unicode_literals

import json

from moto.core.exceptions import AWSError


class EKSError(AWSError):
    def __init__(self, *args, **kwargs):
        super(AWSError, self).__init__()
        self.description = json.dumps(kwargs)
        self.headers = {"status": self.STATUS, "x-amzn-ErrorType": self.TYPE}

    def response(self):
        return self.STATUS, self.headers, self.description


class ResourceInUseException(EKSError):
    TYPE = "ResourceInUseException"
    STATUS = 409


class ResourceNotFoundException(EKSError):
    TYPE = "ResourceNotFoundException"
    STATUS = 404


class InvalidParameterException(EKSError):
    TYPE = "InvalidParameterException"
    STATUS = 400


class InvalidRequestException(EKSError):
    TYPE = "InvalidRequestException"
    STATUS = 400
