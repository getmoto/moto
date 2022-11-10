"""PersonalizeBackend class with methods for supported APIs."""

from .exceptions import ResourceNotFoundException
from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time


class Schema(BaseModel):
    def __init__(self, account_id, region, name, schema, domain):
        self.name = name
        self.schema = schema
        self.domain = domain
        self.arn = f"arn:aws:personalize:{region}:{account_id}:schema/{name}"
        self.created = unix_time()

    def to_dict(self, full=True):
        d = {
            "name": self.name,
            "schemaArn": self.arn,
            "domain": self.domain,
            "creationDateTime": self.created,
            "lastUpdatedDateTime": self.created,
        }
        if full:
            d["schema"] = self.schema
        return d


class PersonalizeBackend(BaseBackend):
    """Implementation of Personalize APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.schemas: [str, Schema] = dict()

    def create_schema(self, name, schema, domain):
        schema = Schema(
            region=self.region_name,
            account_id=self.account_id,
            name=name,
            schema=schema,
            domain=domain,
        )
        self.schemas[schema.arn] = schema
        return schema.arn

    def delete_schema(self, schema_arn):
        if schema_arn not in self.schemas:
            raise ResourceNotFoundException(schema_arn)
        self.schemas.pop(schema_arn, None)

    def describe_schema(self, schema_arn):
        if schema_arn not in self.schemas:
            raise ResourceNotFoundException(schema_arn)
        return self.schemas[schema_arn]

    def list_schemas(self) -> [Schema]:
        """
        Pagination is not yet implemented
        """
        return self.schemas.values()


personalize_backends = BackendDict(PersonalizeBackend, "personalize")
