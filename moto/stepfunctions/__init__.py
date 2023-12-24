from ..core.models import base_decorator
from .models import stepfunction_backends

mock_stepfunctions = base_decorator(stepfunction_backends)
