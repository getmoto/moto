from __future__ import unicode_literals


class MessageNotInflight(Exception):
    description = "The message referred to is not in flight."
    status_code = 400


class ReceiptHandleIsInvalid(Exception):
    description = "The receipt handle provided is not valid."
    status_code = 400


class InvalidParameterValue(Exception):
    description = "One or more parameters are invalid. Reason: Message must be shorter than 262144 bytes."
    status_code = 400


class MessageAttributesInvalid(Exception):
    status_code = 400

    def __init__(self, description):
        self.description = description
