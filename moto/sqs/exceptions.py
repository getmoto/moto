from moto.core.exceptions import RESTError


class ReceiptHandleIsInvalid(RESTError):
    code = 400

    def __init__(self):
        super(ReceiptHandleIsInvalid, self).__init__(
            "ReceiptHandleIsInvalid", "The input receipt handle is invalid."
        )


class MessageAttributesInvalid(RESTError):
    code = 400

    def __init__(self, description):
        super(MessageAttributesInvalid, self).__init__(
            "MessageAttributesInvalid", description
        )


class QueueDoesNotExist(RESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "AWS.SimpleQueueService.NonExistentQueue",
            "The specified queue does not exist for this wsdl version.",
            template="wrapped_single_error",
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


class InvalidAttributeValue(RESTError):
    code = 400

    def __init__(self, attribute_name):
        super(InvalidAttributeValue, self).__init__(
            "InvalidAttributeValue",
            "Invalid value for the parameter {}.".format(attribute_name),
        )


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super(InvalidParameterValue, self).__init__("InvalidParameterValue", message)


class MissingParameter(RESTError):
    code = 400

    def __init__(self, parameter):
        super(MissingParameter, self).__init__(
            "MissingParameter",
            "The request must contain the parameter {}.".format(parameter),
        )


class OverLimit(RESTError):
    code = 403

    def __init__(self, count):
        super(OverLimit, self).__init__(
            "OverLimit", "{} Actions were found, maximum allowed is 7.".format(count)
        )


class InvalidAddress(RESTError):
    code = 400

    def __init__(self, address):
        super(InvalidAddress, self).__init__(
            "InvalidAddress",
            "The address {} is not valid for this endpoint.".format(address),
        )
