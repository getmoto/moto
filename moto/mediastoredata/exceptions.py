from moto.core.exceptions import JsonRESTError


class MediaStoreDataClientError(JsonRESTError):
    code = 400


# AWS service exceptions are caught with the underlying botocore exception, ClientError
class ClientError(MediaStoreDataClientError):
    def __init__(self, error, message):
        super().__init__(error, message)
