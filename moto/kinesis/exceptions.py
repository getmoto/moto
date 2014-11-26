from __future__ import unicode_literals

import json
from werkzeug.exceptions import BadRequest


class ResourceNotFoundError(BadRequest):
    def __init__(self, message):
        super(ResourceNotFoundError, self).__init__()
        self.description = json.dumps({
            "message": message,
            '__type': 'ResourceNotFoundException',
        })


class StreamNotFoundError(ResourceNotFoundError):
    def __init__(self, stream_name):
        super(StreamNotFoundError, self).__init__(
            'Stream {} under account 123456789012 not found.'.format(stream_name))
