from .models import DEFAULT_ACCOUNT_ID  # noqa
from .base_backend import BaseBackend, BackendDict  # noqa
from .common_models import BaseModel  # noqa
from .common_models import CloudFormationModel, CloudWatchMetricProvider  # noqa
from .models import patch_client, patch_resource  # noqa
from .responses import ActionAuthenticatorMixin

set_initial_no_auth_action_count = (
    ActionAuthenticatorMixin.set_initial_no_auth_action_count
)
