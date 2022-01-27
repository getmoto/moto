import json
from werkzeug.exceptions import BadRequest
from moto.core import ACCOUNT_ID


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )


class ResourceInUseError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceInUseException"}
        )


class StreamNotFoundError(ResourceNotFoundError):
    def __init__(self, stream_name):
        super().__init__(
            "Stream {0} under account {1} not found.".format(stream_name, ACCOUNT_ID)
        )


class ShardNotFoundError(ResourceNotFoundError):
    def __init__(self, shard_id, stream):
        super().__init__(
            f"Could not find shard {shard_id} in stream {stream} under account {ACCOUNT_ID}."
        )


class ConsumerNotFound(ResourceNotFoundError):
    def __init__(self, consumer):
        super().__init__(f"Consumer {consumer}, account {ACCOUNT_ID} not found.")


class InvalidArgumentError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "InvalidArgumentException"}
        )


class InvalidRetentionPeriod(InvalidArgumentError):
    def __init__(self, hours, too_short):
        if too_short:
            msg = f"Minimum allowed retention period is 24 hours. Requested retention period ({hours} hours) is too short."
        else:
            msg = f"Maximum allowed retention period is 8760 hours. Requested retention period ({hours} hours) is too long."
        super().__init__(msg)


class InvalidDecreaseRetention(InvalidArgumentError):
    def __init__(self, name, requested, existing):
        msg = f"Requested retention period ({requested} hours) for stream {name} can not be longer than existing retention period ({existing} hours). Use IncreaseRetentionPeriod API."
        super().__init__(msg)


class InvalidIncreaseRetention(InvalidArgumentError):
    def __init__(self, name, requested, existing):
        msg = f"Requested retention period ({requested} hours) for stream {name} can not be shorter than existing retention period ({existing} hours). Use DecreaseRetentionPeriod API."
        super().__init__(msg)


class ValidationException(BadRequest):
    def __init__(self, value, position, regex_to_match):
        super().__init__()
        self.description = json.dumps(
            {
                "message": f"1 validation error detected: Value '{value}' at '{position}' failed to satisfy constraint: Member must satisfy regular expression pattern: {regex_to_match}",
                "__type": "ValidationException",
            }
        )
