from ..core.models import base_decorator
from .models import redshift_backends

mock_redshift = base_decorator(redshift_backends)
