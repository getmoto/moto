from ..core.models import base_decorator
from .models import cognitoidentity_backends

mock_cognitoidentity = base_decorator(cognitoidentity_backends)
