from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super(ResourceNotFoundError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )


class UserNotFoundError(BadRequest):
    def __init__(self, message):
        super(UserNotFoundError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "UserNotFoundException"}
        )


class UsernameExistsException(BadRequest):
    def __init__(self, message):
        super(UsernameExistsException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "UsernameExistsException"}
        )


class GroupExistsException(BadRequest):
    def __init__(self, message):
        super(GroupExistsException, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "GroupExistsException"}
        )


class NotAuthorizedError(BadRequest):
    def __init__(self, message):
        super(NotAuthorizedError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "NotAuthorizedException"}
        )


class InvalidParameterException(JsonRESTError):
    def __init__(self, msg=None):
        self.code = 400
        super(InvalidParameterException, self).__init__(
            "InvalidParameterException", msg or "A parameter is specified incorrectly."
        )
