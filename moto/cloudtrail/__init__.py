"""cloudtrail module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import cloudtrail_backends

mock_cloudtrail = base_decorator(cloudtrail_backends)
