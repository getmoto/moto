from __future__ import unicode_literals
from moto.core.exceptions import RESTError


class GlueClientError(RESTError):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('template', 'single_error')
        super(GlueClientError, self).__init__(*args, **kwargs)
