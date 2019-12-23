from moto.core.exceptions import JsonRESTError


class InvalidStructureException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidStructureException, self).__init__(
            "InvalidStructureException", message
        )


class PipelineNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(PipelineNotFoundException, self).__init__(
            "PipelineNotFoundException", message
        )


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(ResourceNotFoundException, self).__init__(
            "ResourceNotFoundException", message
        )


class InvalidTagsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidTagsException, self).__init__("InvalidTagsException", message)


class TooManyTagsException(JsonRESTError):
    code = 400

    def __init__(self, arn):
        super(TooManyTagsException, self).__init__(
            "TooManyTagsException", "Tag limit exceeded for resource [{}].".format(arn)
        )
