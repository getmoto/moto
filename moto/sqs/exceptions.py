from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class MessageNotInflight(Exception):
    description = "The message referred to is not in flight."
    status_code = 400


class ReceiptHandleIsInvalid(RESTError):
    code = 400

    def __init__(self):
        super(ReceiptHandleIsInvalid, self).__init__(
            "ReceiptHandleIsInvalid", "The input receipt handle is invalid."
        )


class MessageAttributesInvalid(Exception):
    status_code = 400

    def __init__(self, description):
        self.description = description


class QueueDoesNotExist(RESTError):
    code = 404

    def __init__(self):
        super(QueueDoesNotExist, self).__init__(
            "QueueDoesNotExist",
            "The specified queue does not exist for this wsdl version.",
        )


class QueueAlreadyExists(RESTError):
    code = 400

    def __init__(self, message):
        super(QueueAlreadyExists, self).__init__("QueueAlreadyExists", message)


class EmptyBatchRequest(RESTError):
    code = 400

    def __init__(self):
        super(EmptyBatchRequest, self).__init__(
            "EmptyBatchRequest",
            "There should be at least one SendMessageBatchRequestEntry in the request.",
        )


class InvalidBatchEntryId(RESTError):
    code = 400

    def __init__(self):
        super(InvalidBatchEntryId, self).__init__(
            "InvalidBatchEntryId",
            "A batch entry id can only contain alphanumeric characters, "
            "hyphens and underscores. It can be at most 80 letters long.",
        )


class BatchRequestTooLong(RESTError):
    code = 400

    def __init__(self, length):
        super(BatchRequestTooLong, self).__init__(
            "BatchRequestTooLong",
            "Batch requests cannot be longer than 262144 bytes. "
            "You have sent {} bytes.".format(length),
        )


class BatchEntryIdsNotDistinct(RESTError):
    code = 400

    def __init__(self, entry_id):
        super(BatchEntryIdsNotDistinct, self).__init__(
            "BatchEntryIdsNotDistinct", "Id {} repeated.".format(entry_id)
        )


class TooManyEntriesInBatchRequest(RESTError):
    code = 400

    def __init__(self, number):
        super(TooManyEntriesInBatchRequest, self).__init__(
            "TooManyEntriesInBatchRequest",
            "Maximum number of entries per request are 10. "
            "You have sent {}.".format(number),
        )


class InvalidAttributeName(RESTError):
    code = 400

    def __init__(self, attribute_name):
        super(InvalidAttributeName, self).__init__(
            "InvalidAttributeName", "Unknown Attribute {}.".format(attribute_name)
        )
