from __future__ import unicode_literals

from .models import BaseModel, BaseBackend, moto_api_backend, set_initial_no_auth_action_count  # flake8: noqa

moto_api_backends = {"global": moto_api_backend}
set_initial_no_auth_action_count = set_initial_no_auth_action_count
