from ..core.models import base_decorator
from .models import cloudfront_backends

mock_cloudfront = base_decorator(cloudfront_backends)
