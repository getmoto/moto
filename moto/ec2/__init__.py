from __future__ import unicode_literals
from .models import ec2_backends
from ..core.models import MockAWS, base_decorator

ec2_backend = ec2_backends['us-east-1']
mock_ec2 = base_decorator(ec2_backends)
