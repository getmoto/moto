from __future__ import unicode_literals
from .models import s3_backend

s3_backends = {"global": s3_backend}
mock_s3 = s3_backend.decorator
mock_s3_deprecated = s3_backend.deprecated_decorator
