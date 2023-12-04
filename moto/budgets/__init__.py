from ..core.models import base_decorator
from .models import budgets_backends

mock_budgets = base_decorator(budgets_backends)
