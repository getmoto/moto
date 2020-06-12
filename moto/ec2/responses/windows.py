from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class Windows(BaseResponse):
    def bundle_instance(self):
        raise NotImplementedError("Windows.bundle_instance is not yet implemented")

    def cancel_bundle_task(self):
        raise NotImplementedError("Windows.cancel_bundle_task is not yet implemented")

    def describe_bundle_tasks(self):
        raise NotImplementedError(
            "Windows.describe_bundle_tasks is not yet implemented"
        )

    def get_password_data(self):
        raise NotImplementedError("Windows.get_password_data is not yet implemented")
