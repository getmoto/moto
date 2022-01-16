"""route53resolver module initialization; sets value for base decorator."""
from .models import route53resolver_backends
from ..core.models import base_decorator

mock_route53resolver = base_decorator(route53resolver_backends)
