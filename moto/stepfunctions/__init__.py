from .models import stepfunction_backends
from ..core.models import base_decorator

mock_stepfunctions = base_decorator(stepfunction_backends)
