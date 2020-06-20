from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class ApplicationAutoscalingClientError(RESTError):
    code = 400
