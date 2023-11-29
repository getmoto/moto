"""route53resolver module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import route53resolver_backends

mock_route53resolver = base_decorator(route53resolver_backends)
