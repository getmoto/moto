from moto.core.exceptions import JsonRESTError


class SecretsManagerClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(SecretsManagerClientError):
    def __init__(self, message):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", message
        )


class SecretNotFoundException(SecretsManagerClientError):
    def __init__(self):
        self.code = 404
        super(SecretNotFoundException, self).__init__(
            "ResourceNotFoundException",
            message="Secrets Manager can't find the specified secret.",
        )


class SecretHasNoValueException(SecretsManagerClientError):
    def __init__(self, version_stage):
        self.code = 404
        super(SecretHasNoValueException, self).__init__(
            "ResourceNotFoundException",
            message="Secrets Manager can't find the specified secret "
            "value for staging label: {}".format(version_stage),
        )


class ClientError(SecretsManagerClientError):
    def __init__(self, message):
        super(ClientError, self).__init__("InvalidParameterValue", message)


class InvalidParameterException(SecretsManagerClientError):
    def __init__(self, message):
        super(InvalidParameterException, self).__init__(
            "InvalidParameterException", message
        )


class ResourceExistsException(SecretsManagerClientError):
    def __init__(self, message):
        super(ResourceExistsException, self).__init__(
            "ResourceExistsException", message
        )


class InvalidRequestException(SecretsManagerClientError):
    def __init__(self, message):
        super(InvalidRequestException, self).__init__(
            "InvalidRequestException", message
        )


class ValidationException(SecretsManagerClientError):
    def __init__(self, message):
        super(ValidationException, self).__init__("ValidationException", message)
