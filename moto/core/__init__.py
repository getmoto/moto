from .base_backend import SERVICE_BACKEND, BackendDict, BaseBackend
from .common_models import BaseModel, CloudFormationModel, CloudWatchMetricProvider
from .models import DEFAULT_ACCOUNT_ID, patch_client, patch_resource
from .responses import ActionAuthenticatorMixin

set_initial_no_auth_action_count = (
    ActionAuthenticatorMixin.set_initial_no_auth_action_count
)

__all__ = [
    "DEFAULT_ACCOUNT_ID",
    "SERVICE_BACKEND",
    "BackendDict",
    "BaseBackend",
    "BaseModel",
    "CloudFormationModel",
    "CloudWatchMetricProvider",
    "patch_client",
    "patch_resource",
]
