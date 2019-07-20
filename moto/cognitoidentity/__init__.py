from __future__ import unicode_literals
from .models import cognitoidentity_backends
from ..core.models import base_decorator, deprecated_base_decorator

cognitoidentity_backend = cognitoidentity_backends['us-east-1']
mock_cognitoidentity = base_decorator(cognitoidentity_backends)
mock_cognitoidentity_deprecated = deprecated_base_decorator(cognitoidentity_backends)
