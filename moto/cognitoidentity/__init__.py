from .models import cognitoidentity_backends
from ..core.models import base_decorator, deprecated_base_decorator

mock_cognitoidentity = base_decorator(cognitoidentity_backends)
mock_cognitoidentity_deprecated = deprecated_base_decorator(cognitoidentity_backends)
