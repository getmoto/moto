from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class MessageNotInflight(Exception):
    description = "The message referred to is not in flight."
    status_code = 400


class ReceiptHandleIsInvalid(Exception):
    description = "The receipt handle provided is not valid."
    status_code = 400


class MessageAttributesInvalid(Exception):
    status_code = 400

    def __init__(self, description):
        self.description = description


class QueueDoesNotExist(Exception):
    status_code = 404
    description = "The specified queue does not exist for this wsdl version."


class QueueAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(QueueAlreadyExists, self).__init__(
            "QueueAlreadyExists", message)
