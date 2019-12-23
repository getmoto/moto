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
