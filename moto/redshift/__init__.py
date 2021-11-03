from .models import redshift_backends
from ..core.models import base_decorator, deprecated_base_decorator

redshift_backend = redshift_backends["us-east-1"]
mock_redshift = base_decorator(redshift_backends)
mock_redshift_deprecated = deprecated_base_decorator(redshift_backends)
