"""s3control module initialization; sets value for base decorator."""
from .models import s3control_backends
from ..core.models import base_decorator

mock_s3control = base_decorator(s3control_backends)
