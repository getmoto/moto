from .models import organizations_backends
from ..core.models import base_decorator

mock_organizations = base_decorator(organizations_backends)
