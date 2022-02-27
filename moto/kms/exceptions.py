from moto.core.exceptions import JsonRESTError


class NotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("NotFoundException", message)


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ValidationException", message)


class AlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("AlreadyExistsException", message)


class NotAuthorizedException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__("NotAuthorizedException", None)

        self.description = '{"__type":"NotAuthorizedException"}'


class AccessDeniedException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("AccessDeniedException", message)

        self.description = '{"__type":"AccessDeniedException"}'


class InvalidCiphertextException(JsonRESTError):
    code = 400

    def __init__(self):
        super().__init__("InvalidCiphertextException", None)

        self.description = '{"__type":"InvalidCiphertextException"}'
