"""identitystore module initialization; sets value for base decorator."""
from ..core.models import base_decorator
from .models import identitystore_backends

mock_identitystore = base_decorator(identitystore_backends)
