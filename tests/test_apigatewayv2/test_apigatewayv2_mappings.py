import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_apigatewayv2


@mock_apigatewayv2
def test_create_api_mapping():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    api = client.create_api(Name="test-api", ProtocolType="HTTP")
    dev_domain = client.create_domain_name(DomainName="dev.service.io")
    expected_keys = ["ApiId", "ApiMappingId", "ApiMappingKey", "Stage"]

    post_resp = client.create_api_mapping(
        DomainName=dev_domain["DomainName"],
        ApiMappingKey="v1/api",
        Stage="$default",
        ApiId=api["ApiId"],
    )

    get_resp = client.get_api_mapping(
        DomainName="dev.service.io", ApiMappingId=post_resp["ApiMappingId"]
    )

    # check post response has all expected keys
    for key in expected_keys:
        post_resp.should.have.key(key)

    # check get response has all expected keys
    for key in expected_keys:
        get_resp.should.have.key(key)

    # check that values are equal for post and get of same resource
    for key in expected_keys:
        post_resp.get(key).should.equal(get_resp.get(key))

    # ensure known values are set correct in post response
    post_resp.get("ApiId").should_not.equal(None)
    post_resp.get("ApiMappingId").should_not.equal(None)
    post_resp.get("ApiMappingKey").should.equal("v1/api")
    post_resp.get("Stage").should.equal("$default")


@mock_apigatewayv2
def test_get_api_mappings():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api = client.create_api(Name="test-api", ProtocolType="HTTP")
    included_domain = client.create_domain_name(DomainName="dev.service.io")
    excluded_domain = client.create_domain_name(DomainName="hr.service.io")

    v1_mapping = client.create_api_mapping(
        DomainName=included_domain["DomainName"],
        ApiMappingKey="v1/api",
        Stage="$default",
        ApiId=api["ApiId"],
    )

    v2_mapping = client.create_api_mapping(
        DomainName=included_domain["DomainName"],
        ApiMappingKey="v2/api",
        Stage="$default",
        ApiId=api["ApiId"],
    )

    hr_mapping = client.create_api_mapping(
        DomainName=excluded_domain["DomainName"],
        ApiMappingKey="hr/api",
        Stage="$default",
        ApiId=api["ApiId"],
    )

    # sanity check responses
    v1_mapping.should.have.key("ApiMappingKey").equals("v1/api")
    v2_mapping.should.have.key("ApiMappingKey").equals("v2/api")
    hr_mapping.should.have.key("ApiMappingKey").equals("hr/api")

    # make comparable
    del v1_mapping["ResponseMetadata"]
    del v2_mapping["ResponseMetadata"]
    del hr_mapping["ResponseMetadata"]

    get_resp = client.get_api_mappings(DomainName=included_domain["DomainName"])
    get_resp.should.have.key("Items")
    get_resp.get("Items").should.contain(v1_mapping)
    get_resp.get("Items").should.contain(v2_mapping)
    get_resp.get("Items").should_not.contain(hr_mapping)
