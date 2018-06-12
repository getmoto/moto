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
