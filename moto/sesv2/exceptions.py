from moto.core.exceptions import RESTError


class NotFoundException(RESTError):
    code = 404

    def __init__(self, message: str):
        super().__init__("NotFoundException", message)
