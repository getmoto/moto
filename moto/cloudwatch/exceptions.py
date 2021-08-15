from moto.core.exceptions import RESTError


class ResourceNotFoundException(RESTError):
    code = 404

    def __init__(self):
        super().__init__(__class__.__name__, "Unknown")
