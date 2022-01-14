from moto.core.exceptions import RESTError


class SNSNotFoundError(RESTError):
    code = 404

    def __init__(self, message, **kwargs):
        super().__init__("NotFound", message, **kwargs)


class TopicNotFound(SNSNotFoundError):
    def __init__(self):
        super().__init__(message="Topic does not exist")


class ResourceNotFoundError(RESTError):
    code = 404

    def __init__(self):
        super().__init__("ResourceNotFound", "Resource does not exist")


class DuplicateSnsEndpointError(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("DuplicateEndpoint", message)


class SnsEndpointDisabled(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("EndpointDisabled", message)


class SNSInvalidParameter(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameter", message)


class InvalidParameterValue(RESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidParameterValue", message)


class TagLimitExceededError(RESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "TagLimitExceeded",
            "Could not complete request: tag quota of per resource exceeded",
        )


class InternalError(RESTError):
    code = 500

    def __init__(self, message):
        super().__init__("InternalFailure", message)


class TooManyEntriesInBatchRequest(RESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "TooManyEntriesInBatchRequest",
            "The batch request contains more entries than permissible.",
        )


class BatchEntryIdsNotDistinct(RESTError):
    code = 400

    def __init__(self):
        super().__init__(
            "BatchEntryIdsNotDistinct",
            "Two or more batch entries in the request have the same Id.",
        )
