from ..core.models import base_decorator
from .models import s3_backends

mock_s3 = base_decorator(s3_backends)
