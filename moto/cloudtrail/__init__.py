"""cloudtrail module initialization; sets value for base decorator."""
from .models import cloudtrail_backends
from ..core.models import base_decorator

mock_cloudtrail = base_decorator(cloudtrail_backends)
