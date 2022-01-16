"""Handles incoming s3control requests, invokes methods, returns responses."""
import json

import xmltodict

from moto.core.responses import BaseResponse
from .models import s3control_backends


class S3ControlResponse(BaseResponse):
    SERVICE_NAME = "s3control"
    """Handler for S3Control requests and responses."""

    @property
    def s3control_backend(self):
        """Return backend instance specific for this region."""
        return s3control_backends[self.region]

    # add methods from here

    def get_public_access_block(self):
        account_id = self.headers["x-amz-account-id"]
        public_access_block_configuration = self.s3control_backend.get_public_access_block(
            account_id=account_id,
        )
        template = self.response_template(GET_PUBLIC_ACCESS_BLOCK_TEMPLATE)
        return template.render(
            BlockPublicAcls=public_access_block_configuration.block_public_acls,
            IgnorePublicAcls=public_access_block_configuration.ignore_public_acls,
            BlockPublicPolicy=public_access_block_configuration.block_public_policy,
            RestrictPublicBuckets=public_access_block_configuration.restrict_public_buckets,
        )

    def put_public_access_block(self):
        account_id = self.headers["x-amz-account-id"]
        pab_config = self._parse_pab_config(self.body)
        self.s3control_backend.put_public_access_block(
            account_id, pab_config["PublicAccessBlockConfiguration"]
        )
        return json.dumps({})

    def delete_public_access_block(self):
        account_id = self.headers["x-amz-account-id"]
        self.s3control_backend.delete_public_access_block(account_id=account_id,)
        return json.dumps({})

    def _parse_pab_config(self, body):
        parsed_xml = xmltodict.parse(body)
        parsed_xml["PublicAccessBlockConfiguration"].pop("@xmlns", None)

        return parsed_xml


GET_PUBLIC_ACCESS_BLOCK_TEMPLATE = """
<PublicAccessBlockConfiguration xmlns="http://awss3control.amazonaws.com/doc/2018-08-20/">
    <BlockPublicAcls>{{ BlockPublicAcls }}</BlockPublicAcls>
    <IgnorePublicAcls>{{ IgnorePublicAcls }}</IgnorePublicAcls>
    <BlockPublicPolicy>{{ BlockPublicPolicy }}</BlockPublicPolicy>
    <RestrictPublicBuckets>{{ RestrictPublicBuckets }}</RestrictPublicBuckets>
</PublicAccessBlockConfiguration>
"""
