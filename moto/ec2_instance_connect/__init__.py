from ..core.models import base_decorator
from .models import ec2_instance_connect_backends

mock_ec2_instance_connect = base_decorator(ec2_instance_connect_backends)
