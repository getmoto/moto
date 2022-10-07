from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class DisabledApiException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "DisabledApiException"}
        )


class InternalServiceErrorException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InternalServiceErrorException"}
        )


class InvalidCustomerIdentifierException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidCustomerIdentifierException"}
        )


class InvalidProductCodeException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidProductCodeException"}
        )


class InvalidUsageDimensionException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidUsageDimensionException"}
        )


class ThrottlingException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ThrottlingException"}
        )


class TimestampOutOfBoundsException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "TimestampOutOfBoundsException"}
        )
