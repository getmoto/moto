import json
from werkzeug.exceptions import BadRequest


class AthenaClientError(BadRequest):
    def __init__(self, code, message):
        super().__init__()
        self.description = json.dumps(
            {
                "Error": {
                    "Code": code,
                    "Message": message,
                    "Type": "InvalidRequestException",
                },
                "RequestId": "6876f774-7273-11e4-85dc-39e55ca848d1",
            }
        )
