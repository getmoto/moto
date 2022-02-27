import json

from werkzeug.exceptions import HTTPException


class BadRequestException(HTTPException):
    code = 400

    def __init__(self, message, **kwargs):
        super().__init__(
            description=json.dumps({"Message": message, "Code": "BadRequestException"}),
            **kwargs
        )
