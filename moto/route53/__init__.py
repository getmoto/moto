from __future__ import unicode_literals
from .models import route53_backend
mock_route53 = route53_backend.decorator
mock_route53_deprecated = route53_backend.deprecated_decorator
