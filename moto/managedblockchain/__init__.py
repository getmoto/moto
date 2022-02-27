from .models import managedblockchain_backends
from ..core.models import base_decorator

managedblockchain_backend = managedblockchain_backends["us-east-1"]
mock_managedblockchain = base_decorator(managedblockchain_backends)
