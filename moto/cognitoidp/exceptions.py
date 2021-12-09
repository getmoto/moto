import json
from werkzeug.exceptions import BadRequest
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )


class UserNotFoundError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "UserNotFoundException"}
        )


class UsernameExistsException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "UsernameExistsException"}
        )


class GroupExistsException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "GroupExistsException"}
        )


class NotAuthorizedError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "NotAuthorizedException"}
        )


class UserNotConfirmedException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "UserNotConfirmedException"}
        )


class ExpiredCodeException(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ExpiredCodeException"}
        )


class InvalidParameterException(JsonRESTError):
    def __init__(self, msg=None):
        self.code = 400
        super().__init__(
            "InvalidParameterException", msg or "A parameter is specified incorrectly."
        )
