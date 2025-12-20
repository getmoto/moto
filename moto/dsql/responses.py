"""Handles incoming dsql requests, invokes methods, returns responses."""

import json
from urllib.parse import unquote

from moto.core.responses import BaseResponse
from moto.core.utils import unix_time

from .models import AuroraDSQLBackend, dsql_backends


class AuroraDSQLResponse(BaseResponse):
    """Handler for AuroraDSQL requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="dsql")

    @property
    def dsql_backend(self) -> AuroraDSQLBackend:
        """Return backend instance specific for this region."""
        return dsql_backends[self.current_account][self.region]

    def create_cluster(self) -> str:
        params = json.loads(self.body)
        deletion_protection_enabled = params.get("deletionProtectionEnabled", True)
        tags = params.get("tags")
        client_token = params.get("clientToken")
        cluster = self.dsql_backend.create_cluster(
            deletion_protection_enabled=deletion_protection_enabled,
            tags=tags,
            client_token=client_token,
        )

        return json.dumps(dict(cluster.to_dict()))

    def delete_cluster(self) -> str:
        identifier = self.path.split("/")[-1]
        cluster = self.dsql_backend.delete_cluster(identifier=identifier)
        result = {
            "identifier": cluster.identifier,
            "arn": cluster.arn,
            "status": "DELETING",
            "creationTime": unix_time(cluster.creation_time),
        }
        return json.dumps(result)

    def get_cluster(self) -> str:
        identifier = self.path.split("/")[-1]
        cluster = self.dsql_backend.get_cluster(identifier=identifier)

        return json.dumps(dict(cluster.to_dict()))

    def get_vpc_endpoint_service_name(self) -> str:
        identifier = self.path.split("/")[-2]
        cluster = self.dsql_backend.get_cluster(identifier=identifier)
        result = {
            "serviceName": cluster.endpoint_service_name,
            "clusterVpcEndpoint": cluster.endpoint,
        }
        return json.dumps(result)

    def list_tags_for_resource(self) -> str:
        arn = unquote(self.path.split("/")[-1])
        identifier = arn.split("/")[-1]
        cluster = self.dsql_backend.get_cluster(identifier=identifier)
        return json.dumps({"tags": cluster.tags})
