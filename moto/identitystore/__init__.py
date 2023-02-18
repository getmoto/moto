"""identitystore module initialization; sets value for base decorator."""
from .models import identitystore_backends
from ..core.models import base_decorator

mock_identitystore = base_decorator(identitystore_backends)
