from ..core.models import base_decorator
from .models import route53_backends

mock_route53 = base_decorator(route53_backends)
