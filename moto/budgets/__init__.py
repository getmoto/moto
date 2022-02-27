from .models import budgets_backend

budgets_backends = {"global": budgets_backend}
mock_budgets = budgets_backend.decorator
