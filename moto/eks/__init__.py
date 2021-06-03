from __future__ import unicode_literals

from ..core.models import base_decorator
from .models import eks_backends

REGION = "us-east-1"
eks_backend = eks_backends[REGION]
mock_eks = base_decorator(eks_backends)
