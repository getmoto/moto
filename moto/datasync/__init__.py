from __future__ import unicode_literals

from ..core.models import base_decorator, deprecated_base_decorator
from .models import datasync_backends

datasync_backend = datasync_backends["us-east-1"]
mock_datasync = base_decorator(datasync_backends)
mock_datasync_deprecated = deprecated_base_decorator(datasync_backends)
