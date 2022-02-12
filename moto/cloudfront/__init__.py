from .models import cloudfront_backend
from ..core.models import base_decorator

cloudfront_backends = {"global": cloudfront_backend}
mock_cloudfront = base_decorator(cloudfront_backends)
