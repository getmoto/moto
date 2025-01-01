"""Handles incoming s3tables requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import s3tables_backends


class S3TablesResponse(BaseResponse):
    """Handler for S3Tables requests and responses."""

    def __init__(self):
        super().__init__(service_name="s3tables")

    @property
    def s3tables_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # s3tables_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return s3tables_backends[self.current_account][self.region]

    # add methods from here

    
    def create_table_bucket(self):
        params = self._get_params()
        name = params.get("name")
        table_bucketle_bucket = self.s3tables_backend.create_table_bucket(
            name=name,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=table_bucketle_bucket.arn))

# add templates from here
