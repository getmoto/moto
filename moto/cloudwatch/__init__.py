from .models import cloudwatch_backends
from ..core.models import MockAWS


cloudwatch_backend = cloudwatch_backends['us-east-1']

def mock_cloudwatch(func=None):
    if func:
        return MockAWS(cloudwatch_backends)(func)
    else:
        return MockAWS(cloudwatch_backends)
