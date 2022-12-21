from moto.moto_api._internal import mock_random as random

from moto.core import BaseModel


class WindowsBackend(BaseModel):
    def get_password_data(self, instance_id: str) -> str:
        return random.get_random_string(length=128)

