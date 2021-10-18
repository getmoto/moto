from .models import cognitoidentity_backends
from ..core.models import base_decorator

cognitoidentity_backend = cognitoidentity_backends["us-east-1"]
mock_cognitoidentity = base_decorator(cognitoidentity_backends)
