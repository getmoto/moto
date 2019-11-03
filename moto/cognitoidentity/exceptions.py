from __future__ import unicode_literals

import json

from werkzeug.exceptions import BadRequest


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super(ResourceNotFoundError, self).__init__()
        self.description = json.dumps(
            {"message": message, "__type": "ResourceNotFoundException"}
        )
