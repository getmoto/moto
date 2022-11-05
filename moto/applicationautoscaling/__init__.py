from .models import applicationautoscaling_backends
from ..core.models import base_decorator

mock_applicationautoscaling = base_decorator(applicationautoscaling_backends)
