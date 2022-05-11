from .models import s3_backend
from ..core.models import base_decorator

s3_backends = {"global": s3_backend}
mock_s3 = base_decorator(s3_backends)
