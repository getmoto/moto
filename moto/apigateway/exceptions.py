from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class StageNotFoundException(RESTError):
    code = 404

    def __init__(self):
        super(StageNotFoundException, self).__init__(
            "NotFoundException", "Invalid stage identifier specified")
