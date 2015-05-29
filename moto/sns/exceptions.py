from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class SNSNotFoundError(RESTError):
    code = 404

    def __init__(self, message):
        super(SNSNotFoundError, self).__init__(
            "NotFound", message)
