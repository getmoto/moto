from .models import BaseModel, BaseBackend, moto_api_backend, ACCOUNT_ID  # noqa
from .models import CloudFormationModel, CloudWatchMetricProvider  # noqa
from .models import patch_client, patch_resource  # noqa
from .responses import ActionAuthenticatorMixin

moto_api_backends = {"global": moto_api_backend}
set_initial_no_auth_action_count = (
    ActionAuthenticatorMixin.set_initial_no_auth_action_count
)
