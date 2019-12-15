from moto.core.exceptions import JsonRESTError


class InvalidStructureException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super(InvalidStructureException, self).__init__(
            "InvalidStructureException", message
        )
