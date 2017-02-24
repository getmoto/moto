from __future__ import unicode_literals

from moto.core.exceptions import RESTError


class EmrError(RESTError):
    code = 400
