from .models import moto_api_backend
from .state_manager import StateManager  # noqa
from .recorder.models import Recorder  # noqa


moto_api_backends = {"global": moto_api_backend}
