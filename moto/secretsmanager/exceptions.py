from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class SecretsManagerClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(SecretsManagerClientError):
    def __init__(self):
        self.code = 404
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException",
            "Secrets Manager can't find the specified secret"
        )


class ClientError(SecretsManagerClientError):
    def __init__(self, message):
        super(ClientError, self).__init__(
            'InvalidParameterValue',
            message)


class InvalidParameterException(SecretsManagerClientError):
    def __init__(self, message):
        super(InvalidParameterException, self).__init__(
            'InvalidParameterException',
            message)


class ResourceExistsException(SecretsManagerClientError):
    def __init__(self, message):
        super(ResourceExistsException, self).__init__(
            'ResourceExistsException',
            message
        )


class InvalidRequestException(SecretsManagerClientError):
    def __init__(self, message):
        super(InvalidRequestException, self).__init__(
            'InvalidRequestException',
            message)
