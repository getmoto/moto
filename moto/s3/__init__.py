from .models import s3_backends
from ..core.models import base_decorator

mock_s3 = base_decorator(s3_backends)
