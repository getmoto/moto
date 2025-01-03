"""Exceptions raised by the s3tables service."""

from moto.core.exceptions import JsonRESTError


class BadRequestException(JsonRESTError):
    def __init__(self, message: str):
        super().__init__("BadRequestException", message)


class InvalidContinuationToken(BadRequestException):
    msg = "The continuation token is not valid."
    def __init__(self):
        super().__init__(self.msg)


class InvalidTableBucketName(BadRequestException):
    msg = "The specified bucket name is not valid."
    def __init__(self):
        super().__init__(self.msg)

class InvalidTableName(BadRequestException):
    template = "1 validation error detected: Value '%s' at 'name' failed to satisfy constraint: Member must satisfy regular expression pattern: [0-9a-z_]*"
    def __init__(self, name: str):
        super().__init__(self.template.format(name))

class InvalidNamespaceName(BadRequestException):
    msg = "The specified namespace name is not valid."
    def __init__(self):
        super().__init__(self.msg)
    


