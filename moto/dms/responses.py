from __future__ import unicode_literals
# import json
# import re
# from datetime import datetime
# from functools import wraps

# import pytz

# from six.moves.urllib.parse import urlparse
from moto.core.responses import BaseResponse
# from .exceptions import DMSError
from .models import dms_backends


class DMSServiceResponse(BaseResponse):

    @property
    def backend(self):
        return dms_backends[self.region]
