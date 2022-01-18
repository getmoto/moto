import json
import xmltodict

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from moto.s3.exceptions import S3ClientError
from moto.s3.responses import S3_PUBLIC_ACCESS_BLOCK_CONFIGURATION
from .models import s3control_backend


class S3ControlResponse(BaseResponse):
    @classmethod
    def public_access_block(cls, request, full_url, headers):
        response_instance = S3ControlResponse()
        try:
            return response_instance._public_access_block(request, headers)
        except S3ClientError as err:
            return err.code, {}, err.description

    @amzn_request_id
    def _public_access_block(self, request, headers):
        if request.method == "GET":
            return self.get_public_access_block(headers)
        elif request.method == "PUT":
            return self.put_public_access_block(request, headers)
        elif request.method == "DELETE":
            return self.delete_public_access_block(headers)

    def get_public_access_block(self, headers):
        account_id = headers["x-amz-account-id"]
        public_block_config = s3control_backend.get_public_access_block(
            account_id=account_id,
        )
        template = self.response_template(S3_PUBLIC_ACCESS_BLOCK_CONFIGURATION)
        return 200, {}, template.render(public_block_config=public_block_config)

    def put_public_access_block(self, request, headers):
        account_id = headers["x-amz-account-id"]
        pab_config = self._parse_pab_config(request.body)
        s3control_backend.put_public_access_block(
            account_id, pab_config["PublicAccessBlockConfiguration"]
        )
        return 201, {}, json.dumps({})

    def delete_public_access_block(self, headers):
        account_id = headers["x-amz-account-id"]
        s3control_backend.delete_public_access_block(account_id=account_id,)
        return 204, {}, json.dumps({})

    def _parse_pab_config(self, body):
        parsed_xml = xmltodict.parse(body)
        parsed_xml["PublicAccessBlockConfiguration"].pop("@xmlns", None)

        return parsed_xml
