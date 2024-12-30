"""S3TablesBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class S3TablesBackend(BaseBackend):
    """Implementation of S3Tables APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def create_table_bucket(self, name):
        raise Exception("wow")
        # implement here
        return arn
    

s3tables_backends = BackendDict(S3TablesBackend, "s3tables")
