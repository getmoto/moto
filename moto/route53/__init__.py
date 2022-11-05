from .models import route53_backends
from ..core.models import base_decorator

mock_route53 = base_decorator(route53_backends)
