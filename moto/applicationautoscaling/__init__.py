from ..core.models import base_decorator
from .models import applicationautoscaling_backends

mock_applicationautoscaling = base_decorator(applicationautoscaling_backends)
