from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class STSClientError(RESTError):
    code = 400


class STSValidationError(STSClientError):
    def __init__(self, *args, **kwargs):
        super(STSValidationError, self).__init__("ValidationError", *args, **kwargs)
