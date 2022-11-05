from moto.core.exceptions import JsonRESTError


class NotFoundException(JsonRESTError):
    code = 400

    def __init__(self, message):
        super().__init__("NotFoundException", message)
