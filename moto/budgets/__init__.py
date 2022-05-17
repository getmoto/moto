from .models import budgets_backend
from ..core.models import base_decorator

budgets_backends = {"global": budgets_backend}
mock_budgets = base_decorator(budgets_backends)
