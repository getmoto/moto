from .models import budgets_backends
from ..core.models import base_decorator

mock_budgets = base_decorator(budgets_backends)
