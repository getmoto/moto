from ..core.models import base_decorator
from .models import organizations_backends

mock_organizations = base_decorator(organizations_backends)
