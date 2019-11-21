from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class InvalidInputError(BadRequest):
    def __init__(self):
        super(InvalidInputError, self).__init__()
        self.description = json.dumps(
            {
                "message": "You provided a value that does not match the required pattern.",
                "__type": "InvalidInputException",
            }
        )
