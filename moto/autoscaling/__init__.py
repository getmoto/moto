from .models import autoscaling_backend, autoscaling_backends
from ..core.models import MockAWS


def mock_autoscaling(func=None):
    if func:
        return MockAWS(autoscaling_backends)(func)
    else:
        return MockAWS(autoscaling_backends)
