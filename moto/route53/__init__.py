from .models import route53_backend
from ..core.models import base_decorator

route53_backends = {"global": route53_backend}
mock_route53 = base_decorator(route53_backends)
