import json

from moto.core.exceptions import AWSError


class EKSError(AWSError):
    def __init__(self, **kwargs):
        super(AWSError, self).__init__(error_type=self.TYPE, message="")
        self.description = json.dumps(kwargs)
        self.headers = {"status": self.STATUS, "x-amzn-ErrorType": self.TYPE}
        self.code = self.STATUS

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
