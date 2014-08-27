from .models import ec2_backends, ec2_backend
from ..core.models import MockAWS

def mock_ec2(func=None):
    if func:
        return MockAWS(ec2_backends)(func)
    else:
        return MockAWS(ec2_backends)
