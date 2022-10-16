from moto.core.exceptions import JsonRESTError


class ResourceNotFoundError(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="ResourceNotFoundException", message=message)


class UserNotFoundError(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="UserNotFoundException", message=message)


class UsernameExistsException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="UsernameExistsException", message=message)


class GroupExistsException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="GroupExistsException", message=message)


class NotAuthorizedError(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="NotAuthorizedException", message=message)


class UserNotConfirmedException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="UserNotConfirmedException", message=message)


class ExpiredCodeException(JsonRESTError):
    def __init__(self, message):
        super().__init__(error_type="ExpiredCodeException", message=message)


class InvalidParameterException(JsonRESTError):
    def __init__(self, msg=None):
        self.code = 400
        super().__init__(
            "InvalidParameterException", msg or "A parameter is specified incorrectly."
        )
