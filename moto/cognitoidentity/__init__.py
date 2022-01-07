from .models import cognitoidentity_backends
from ..core.models import base_decorator

mock_cognitoidentity = base_decorator(cognitoidentity_backends)
