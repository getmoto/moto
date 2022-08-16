"""Handles incoming personalize requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import personalize_backends


class PersonalizeResponse(BaseResponse):
    """Handler for Personalize requests and responses."""

    def __init__(self):
        super().__init__(service_name="personalize")

    @property
    def personalize_backend(self):
        """Return backend instance specific for this region."""
        return personalize_backends[self.current_account][self.region]

    # add methods from here

    def create_schema(self):
        params = json.loads(self.body)
        name = params.get("name")
        schema = params.get("schema")
        domain = params.get("domain")
        schema_arn = self.personalize_backend.create_schema(
            name=name,
            schema=schema,
            domain=domain,
        )
        return json.dumps(dict(schemaArn=schema_arn))

    def delete_schema(self):
        params = json.loads(self.body)
        schema_arn = params.get("schemaArn")
        self.personalize_backend.delete_schema(schema_arn=schema_arn)
        return "{}"

    def describe_schema(self):
        params = json.loads(self.body)
        schema_arn = params.get("schemaArn")
        schema = self.personalize_backend.describe_schema(schema_arn=schema_arn)
        return json.dumps(dict(schema=schema.to_dict()))

    def list_schemas(self):
        schemas = self.personalize_backend.list_schemas()
        resp = {"schemas": [s.to_dict(full=False) for s in schemas]}
        return json.dumps(resp)
