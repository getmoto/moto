from moto.core.exceptions import RESTError


class SNSException(RESTError):
    def __init__(self, *args, **kwargs):
        kwargs["template"] = "wrapped_single_error"
        super().__init__(*args, **kwargs)


class SNSNotFoundError(SNSException):
    code = 404

    def __init__(self, message, **kwargs):
        super().__init__("NotFound", message, **kwargs)


class TopicNotFound(SNSNotFoundError):
    def __init__(self):
        super().__init__(message="Topic does not exist")


class ResourceNotFoundError(SNSException):
    code = 404

    def __init__(self):
        super().__init__("ResourceNotFound", "Resource does not exist")


class DuplicateSnsEndpointError(SNSException):
    code = 400

    def __init__(self, message):
        super().__init__("DuplicateEndpoint", message)


class SnsEndpointDisabled(SNSException):
    code = 400

    def __init__(self, message):
        super().__init__("EndpointDisabled", message)


class SNSInvalidParameter(SNSException):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameter", message)


class InvalidParameterValue(SNSException):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameterValue", message)


class TagLimitExceededError(SNSException):
    code = 400

    def __init__(self):
        super().__init__(
            "TagLimitExceeded",
            "Could not complete request: tag quota of per resource exceeded",
        )


class InternalError(SNSException):
    code = 500

    def __init__(self, message):
        super().__init__("InternalFailure", message)


class TooManyEntriesInBatchRequest(SNSException):
    code = 400

    def __init__(self):
        super().__init__(
            "TooManyEntriesInBatchRequest",
            "The batch request contains more entries than permissible.",
        )


class BatchEntryIdsNotDistinct(SNSException):
    code = 400

    def __init__(self):
        super().__init__(
            "BatchEntryIdsNotDistinct",
            "Two or more batch entries in the request have the same Id.",
        )
