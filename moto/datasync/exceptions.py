from moto.core.exceptions import JsonRESTError
from typing import Optional


class DataSyncClientError(JsonRESTError):
    code = 400


class InvalidRequestException(DataSyncClientError):
    def __init__(self, msg: Optional[str] = None):
        self.code = 400
        super().__init__("InvalidRequestException", msg or "The request is not valid.")
