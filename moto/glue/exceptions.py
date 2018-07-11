from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class GlueClientError(JsonRESTError):
    code = 400


class DatabaseAlreadyExistsException(GlueClientError):
    def __init__(self):
        self.code = 400
        super(DatabaseAlreadyExistsException, self).__init__(
            'DatabaseAlreadyExistsException',
            'Database already exists.'
        )
