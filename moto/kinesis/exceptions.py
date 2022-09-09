import json
from werkzeug.exceptions import BadRequest


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
    def __init__(self, stream_name, account_id):
        super().__init__(f"Stream {stream_name} under account {account_id} not found.")


class StreamCannotBeUpdatedError(BadRequest):
    def __init__(self, stream_name, account_id):
        super().__init__()
        message = f"Request is invalid. Stream {stream_name} under account {account_id} is in On-Demand mode."
        self.description = json.dumps(
            {"message": message, "__type": "ValidationException"}
        )


class ShardNotFoundError(ResourceNotFoundError):
    def __init__(self, shard_id, stream, account_id):
        super().__init__(
            f"Could not find shard {shard_id} in stream {stream} under account {account_id}."
        )


class ConsumerNotFound(ResourceNotFoundError):
    def __init__(self, consumer, account_id):
        super().__init__(f"Consumer {consumer}, account {account_id} not found.")


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


class RecordSizeExceedsLimit(BadRequest):
    def __init__(self, position):
        super().__init__()
        self.description = json.dumps(
            {
                "message": f"1 validation error detected: Value at 'records.{position}.member.data' failed to satisfy constraint: Member must have length less than or equal to 1048576",
                "__type": "ValidationException",
            }
        )


class TotalRecordsSizeExceedsLimit(BadRequest):
    def __init__(self):
        super().__init__()
        self.description = json.dumps(
            {
                "message": "Records size exceeds 5 MB limit",
                "__type": "InvalidArgumentException",
            }
        )


class TooManyRecords(BadRequest):
    def __init__(self):
        super().__init__()
        self.description = json.dumps(
            {
                "message": "1 validation error detected: Value at 'records' failed to satisfy constraint: Member must have length less than or equal to 500",
                "__type": "ValidationException",
            }
        )
