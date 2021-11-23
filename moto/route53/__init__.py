from .models import route53_backend

route53_backends = {"global": route53_backend}
mock_route53 = route53_backend.decorator
mock_route53_deprecated = route53_backend.deprecated_decorator
