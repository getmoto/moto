from moto.core.exceptions import JsonRESTError


class NotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(NotFoundException, self).__init__("NotFoundException", message)


class ValidationException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)


class AlreadyExistsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(AlreadyExistsException, self).__init__("AlreadyExistsException", message)


class NotAuthorizedException(JsonRESTError):
    code = 400

    def __init__(self):
        super(NotAuthorizedException, self).__init__("NotAuthorizedException", None)

        self.description = '{"__type":"NotAuthorizedException"}'


class AccessDeniedException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(AccessDeniedException, self).__init__("AccessDeniedException", message)

        self.description = '{"__type":"AccessDeniedException"}'


class InvalidCiphertextException(JsonRESTError):
    code = 400

    def __init__(self):
        super(InvalidCiphertextException, self).__init__(
            "InvalidCiphertextException", None
        )

        self.description = '{"__type":"InvalidCiphertextException"}'
