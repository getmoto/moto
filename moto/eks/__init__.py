from __future__ import unicode_literals
from .models import eks_backends
from ..core.models import base_decorator

eks_backend = eks_backends['us-east-1']
mock_eks = base_decorator(eks_backends)
