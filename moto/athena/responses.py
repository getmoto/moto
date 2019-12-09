import json

from moto.core.responses import BaseResponse
from .models import athena_backends


class AthenaResponse(BaseResponse):
    @property
    def athena_backend(self):
        return athena_backends[self.region]

    def create_work_group(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        configuration = self._get_param("Configuration")
        tags = self._get_param("Tags")
        work_group = self.athena_backend.create_work_group(
            name, configuration, description, tags
        )
        if not work_group:
            return (
                json.dumps(
                    {
                        "__type": "InvalidRequestException",
                        "Message": "WorkGroup already exists",
                    }
                ),
                dict(status=400),
            )
        return json.dumps(
            {
                "CreateWorkGroupResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384ac68d-3775-11df-8963-01868b7c937a"
                    }
                }
            }
        )

    def list_work_groups(self):
        return json.dumps({"WorkGroups": self.athena_backend.list_work_groups()})
