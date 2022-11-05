from .models import redshift_backends
from ..core.models import base_decorator

mock_redshift = base_decorator(redshift_backends)
