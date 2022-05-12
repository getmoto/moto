import json

from werkzeug.exceptions import BadRequest


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super().__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )


class InvalidNameException(BadRequest):

    message = "1 validation error detected: Value '{}' at 'identityPoolName' failed to satisfy constraint: Member must satisfy regular expression pattern: [\\w\\s+=,.@-]+"

    def __init__(self, name):
        super().__init__()
        self.description = json.dumps(
            {
                "message": InvalidNameException.message.format(name),
                "__type": "ValidationException",
            }
        )
