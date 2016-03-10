from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class MessageRejectedError(RESTError):
    code = 400

    def __init__(self, message):
        super(MessageRejectedError, self).__init__(
            "MessageRejected", message)
