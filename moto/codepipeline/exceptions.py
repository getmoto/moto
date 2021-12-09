from moto.core.exceptions import JsonRESTError


class InvalidStructureException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidStructureException", message)


class PipelineNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("PipelineNotFoundException", message)


class ResourceNotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("ResourceNotFoundException", message)


class InvalidTagsException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("InvalidTagsException", message)


class TooManyTagsException(JsonRESTError):
    code = 400

    def __init__(self, arn):
        super().__init__(
            "TooManyTagsException", "Tag limit exceeded for resource [{}].".format(arn)
        )
