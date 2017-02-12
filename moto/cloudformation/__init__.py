from __future__ import unicode_literals
from .models import cloudformation_backends
from ..core.models import MockAWS, base_decorator

cloudformation_backend = cloudformation_backends['us-east-1']
mock_cloudformation = base_decorator(cloudformation_backends)
