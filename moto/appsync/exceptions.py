import json
from moto.core.exceptions import JsonRESTError


class AppSyncExceptions(JsonRESTError):
    pass


class GraphqlAPINotFound(AppSyncExceptions):
    code = 404

    def __init__(self, api_id: str):
        super().__init__("NotFoundException", f"GraphQL API {api_id} not found.")
        self.description = json.dumps({"message": self.message})
