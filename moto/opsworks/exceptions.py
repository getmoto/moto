from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class ResourceNotFoundException(BadRequest):

    def __init__(self, message):
        super(ResourceNotFoundException, self).__init__()
        self.description = json.dumps({
            "message": message,
            '__type': 'ResourceNotFoundException',
        })


class ValidationException(BadRequest):

    def __init__(self, message):
        super(ValidationException, self).__init__()
        self.description = json.dumps({
            "message": message,
            '__type': 'ResourceNotFoundException',
        })
