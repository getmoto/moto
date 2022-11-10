import json
import xmltodict

from moto.core.responses import BaseResponse
from moto.s3.exceptions import S3ClientError
from moto.s3.responses import S3_PUBLIC_ACCESS_BLOCK_CONFIGURATION
from moto.utilities.aws_headers import amzn_request_id
from .models import s3control_backends


class S3ControlResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="s3control")

    @property
    def backend(self):
        return s3control_backends[self.current_account]["global"]

    @amzn_request_id
    def public_access_block(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        try:
            if request.method == "GET":
                return self.get_public_access_block(request)
            elif request.method == "PUT":
                return self.put_public_access_block(request)
            elif request.method == "DELETE":
                return self.delete_public_access_block(request)
        except S3ClientError as err:
            return err.code, {}, err.description

    def get_public_access_block(self, request):
        account_id = request.headers.get("x-amz-account-id")
        public_block_config = self.backend.get_public_access_block(
            account_id=account_id
        )
        template = self.response_template(S3_PUBLIC_ACCESS_BLOCK_CONFIGURATION)
        return 200, {}, template.render(public_block_config=public_block_config)

    def put_public_access_block(self, request):
        account_id = request.headers.get("x-amz-account-id")
        data = request.body if hasattr(request, "body") else request.data
        pab_config = self._parse_pab_config(data)
        self.backend.put_public_access_block(
            account_id, pab_config["PublicAccessBlockConfiguration"]
        )
        return 201, {}, json.dumps({})

    def delete_public_access_block(self, request):
        account_id = request.headers.get("x-amz-account-id")
        self.backend.delete_public_access_block(account_id=account_id)
        return 204, {}, json.dumps({})

    def _parse_pab_config(self, body):
        parsed_xml = xmltodict.parse(body)
        parsed_xml["PublicAccessBlockConfiguration"].pop("@xmlns", None)

        return parsed_xml

    def access_point(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.create_access_point(full_url)
        if request.method == "GET":
            return self.get_access_point(full_url)
        if request.method == "DELETE":
            return self.delete_access_point(full_url)

    def access_point_policy(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.create_access_point_policy(full_url)
        if request.method == "GET":
            return self.get_access_point_policy(full_url)
        if request.method == "DELETE":
            return self.delete_access_point_policy(full_url)

    def access_point_policy_status(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "PUT":
            return self.create_access_point(full_url)
        if request.method == "GET":
            return self.get_access_point_policy_status(full_url)

    def create_access_point(self, full_url):
        account_id, name = self._get_accountid_and_name_from_accesspoint(full_url)
        params = xmltodict.parse(self.body)["CreateAccessPointRequest"]
        bucket = params["Bucket"]
        vpc_configuration = params.get("VpcConfiguration")
        public_access_block_configuration = params.get("PublicAccessBlockConfiguration")
        access_point = self.backend.create_access_point(
            account_id=account_id,
            name=name,
            bucket=bucket,
            vpc_configuration=vpc_configuration,
            public_access_block_configuration=public_access_block_configuration,
        )
        template = self.response_template(CREATE_ACCESS_POINT_TEMPLATE)
        return 200, {}, template.render(access_point=access_point)

    def get_access_point(self, full_url):
        account_id, name = self._get_accountid_and_name_from_accesspoint(full_url)

        access_point = self.backend.get_access_point(account_id=account_id, name=name)
        template = self.response_template(GET_ACCESS_POINT_TEMPLATE)
        return 200, {}, template.render(access_point=access_point)

    def delete_access_point(self, full_url):
        account_id, name = self._get_accountid_and_name_from_accesspoint(full_url)
        self.backend.delete_access_point(account_id=account_id, name=name)
        return 204, {}, ""

    def create_access_point_policy(self, full_url):
        account_id, name = self._get_accountid_and_name_from_policy(full_url)
        params = xmltodict.parse(self.body)
        policy = params["PutAccessPointPolicyRequest"]["Policy"]
        self.backend.create_access_point_policy(account_id, name, policy)
        return 200, {}, ""

    def get_access_point_policy(self, full_url):
        account_id, name = self._get_accountid_and_name_from_policy(full_url)
        policy = self.backend.get_access_point_policy(account_id, name)
        template = self.response_template(GET_ACCESS_POINT_POLICY_TEMPLATE)
        return 200, {}, template.render(policy=policy)

    def delete_access_point_policy(self, full_url):
        account_id, name = self._get_accountid_and_name_from_policy(full_url)
        self.backend.delete_access_point_policy(account_id=account_id, name=name)
        return 204, {}, ""

    def get_access_point_policy_status(self, full_url):
        account_id, name = self._get_accountid_and_name_from_policy(full_url)
        self.backend.get_access_point_policy_status(account_id, name)
        template = self.response_template(GET_ACCESS_POINT_POLICY_STATUS_TEMPLATE)
        return 200, {}, template.render()

    def _get_accountid_and_name_from_accesspoint(self, full_url):
        url = full_url
        if full_url.startswith("http"):
            url = full_url.split("://")[1]
        account_id = url.split(".")[0]
        name = url.split("v20180820/accesspoint/")[-1]
        return account_id, name

    def _get_accountid_and_name_from_policy(self, full_url):
        url = full_url
        if full_url.startswith("http"):
            url = full_url.split("://")[1]
        account_id = url.split(".")[0]
        name = self.path.split("/")[-2]
        return account_id, name


S3ControlResponseInstance = S3ControlResponse()


CREATE_ACCESS_POINT_TEMPLATE = """<CreateAccessPointResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <Alias>{{ access_point.name }}</Alias>
  <AccessPointArn>{{ access_point.arn }}</AccessPointArn>
</CreateAccessPointResult>
"""


GET_ACCESS_POINT_TEMPLATE = """<GetAccessPointResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <Name>{{ access_point.name }}</Name>
  <Bucket>{{ access_point.bucket }}</Bucket>
  <NetworkOrigin>{{ access_point.network_origin }}</NetworkOrigin>
  {% if access_point.vpc_id %}
  <VpcConfiguration>
      <VpcId>{{ access_point.vpc_id }}</VpcId>
  </VpcConfiguration>
  {% endif %}
  <PublicAccessBlockConfiguration>
      <BlockPublicAcls>{{ access_point.pubc["BlockPublicAcls"] }}</BlockPublicAcls>
      <IgnorePublicAcls>{{ access_point.pubc["IgnorePublicAcls"] }}</IgnorePublicAcls>
      <BlockPublicPolicy>{{ access_point.pubc["BlockPublicPolicy"] }}</BlockPublicPolicy>
      <RestrictPublicBuckets>{{ access_point.pubc["RestrictPublicBuckets"] }}</RestrictPublicBuckets>
  </PublicAccessBlockConfiguration>
  <CreationDate>{{ access_point.created }}</CreationDate>
  <Alias>{{ access_point.alias }}</Alias>
  <AccessPointArn>{{ access_point.arn }}</AccessPointArn>
  <Endpoints>
      <entry>
          <key>ipv4</key>
          <value>s3-accesspoint.us-east-1.amazonaws.com</value>
      </entry>
      <entry>
          <key>fips</key>
          <value>s3-accesspoint-fips.us-east-1.amazonaws.com</value>
      </entry>
      <entry>
          <key>fips_dualstack</key>
          <value>s3-accesspoint-fips.dualstack.us-east-1.amazonaws.com</value>
      </entry>
      <entry>
          <key>dualstack</key>
          <value>s3-accesspoint.dualstack.us-east-1.amazonaws.com</value>
      </entry>
  </Endpoints>
</GetAccessPointResult>
"""


GET_ACCESS_POINT_POLICY_TEMPLATE = """<GetAccessPointPolicyResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <Policy>{{ policy }}</Policy>
</GetAccessPointPolicyResult>
"""


GET_ACCESS_POINT_POLICY_STATUS_TEMPLATE = """<GetAccessPointPolicyResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
  <PolicyStatus>
      <IsPublic>true</IsPublic>
  </PolicyStatus>
</GetAccessPointPolicyResult>
"""
