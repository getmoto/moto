import json
from werkzeug.exceptions import BadRequest
from moto.core import ACCOUNT_ID


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super(ResourceNotFoundError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )


class ResourceInUseError(BadRequest):
    def __init__(self, message):
        super(ResourceInUseError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceInUseException"}
        )


class StreamNotFoundError(ResourceNotFoundError):
    def __init__(self, stream_name):
        super(StreamNotFoundError, self).__init__(
            "Stream {0} under account {1} not found.".format(stream_name, ACCOUNT_ID)
        )


class ShardNotFoundError(ResourceNotFoundError):
    def __init__(self, shard_id, stream):
        super(ShardNotFoundError, self).__init__(
            f"Could not find shard {shard_id} in stream {stream} under account {ACCOUNT_ID}."
        )


class InvalidArgumentError(BadRequest):
    def __init__(self, message):
        super(InvalidArgumentError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidArgumentException"}
        )


class ValidationException(BadRequest):
    def __init__(self, value, position, regex_to_match):
        super(ValidationException, self).__init__()
        self.description = json.dumps(
            {
                "message": f"1 validation error detected: Value '{value}' at '{position}' failed to satisfy constraint: Member must satisfy regular expression pattern: {regex_to_match}",
                "__type": "ValidationException",
            }
        )
