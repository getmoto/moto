"""s3control module initialization; sets value for base decorator."""
from .models import s3control_backend
from ..core.models import base_decorator

s3control_backends = {"global": s3control_backend}
mock_s3control = base_decorator(s3control_backends)
