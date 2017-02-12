from __future__ import unicode_literals
from .models import lambda_backends
from ..core.models import MockAWS, base_decorator


lambda_backend = lambda_backends['us-east-1']
mock_lambda = base_decorator(lambda_backends)
