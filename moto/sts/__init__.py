from __future__ import unicode_literals
from .models import sts_backend

sts_backends = {"global": sts_backend}
mock_sts = sts_backend.decorator
mock_sts_deprecated = sts_backend.deprecated_decorator
