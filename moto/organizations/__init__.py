from .models import organizations_backend
from ..core.models import base_decorator

organizations_backends = {"global": organizations_backend}
mock_organizations = base_decorator(organizations_backends)
