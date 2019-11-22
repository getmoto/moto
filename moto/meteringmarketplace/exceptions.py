from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class DisabledApiException(BadRequest):
    def __init__(self, message):
        super(DisabledApiException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "DisabledApiException"}
        )


class InternalServiceErrorException(BadRequest):
    def __init__(self, message):
        super(InternalServiceErrorException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InternalServiceErrorException"}
        )


class InvalidCustomerIdentifierException(BadRequest):
    def __init__(self, message):
        super(InvalidCustomerIdentifierException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidCustomerIdentifierException"}
        )


class InvalidProductCodeException(BadRequest):
    def __init__(self, message):
        super(InvalidProductCodeException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidProductCodeException"}
        )


class InvalidUsageDimensionException(BadRequest):
    def __init__(self, message):
        super(InvalidUsageDimensionException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidUsageDimensionException"}
        )


class ThrottlingException(BadRequest):
    def __init__(self, message):
        super(ThrottlingException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ThrottlingException"}
        )


class TimestampOutOfBoundsException(BadRequest):
    def __init__(self, message):
        super(TimestampOutOfBoundsException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "TimestampOutOfBoundsException"}
        )
