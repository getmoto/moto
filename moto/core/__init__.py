from __future__ import unicode_literals

from .models import BaseModel, BaseBackend, moto_api_backend  # flake8: noqa
from .responses import ActionAuthenticatorMixin

moto_api_backends = {"global": moto_api_backend}
set_initial_no_auth_action_count = ActionAuthenticatorMixin.set_initial_no_auth_action_count
