from __future__ import unicode_literals
from .models import elbv2_backends
from ..core.models import base_decorator

elb_backend = elbv2_backends['us-east-1']
mock_elbv2 = base_decorator(elbv2_backends)
