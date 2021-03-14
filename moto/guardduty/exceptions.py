from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class GuarddutyClientError(RESTError):
    code = 400


class MissingParameterError(GuarddutyClientError):
    def __init__(self, parameter):
        super(MissingParameterError, self).__init__(
            "MissingParameter",
            "The request must contain the parameter {0}".format(parameter),
        )
