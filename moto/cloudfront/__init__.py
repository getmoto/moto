from .models import cloudfront_backends
from ..core.models import base_decorator

mock_cloudfront = base_decorator(cloudfront_backends)
