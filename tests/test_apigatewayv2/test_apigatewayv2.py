"""Unit tests for apigatewayv2-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_apigatewayv2

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_apigatewayv2
def test_create_api_with_unknown_protocol_type():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.create_api(Name="test-api", ProtocolType="?")
    err = exc.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.equal(
        "Invalid protocol specified. Must be one of [HTTP, WEBSOCKET]"
    )


@mock_apigatewayv2
def test_create_api_minimal():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(Name="test-api", ProtocolType="HTTP")

    resp.should.have.key("ApiId")
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals(
        "$request.header.x-api-key"
    )
    resp.should.have.key("CreatedDate")
    resp.should.have.key("DisableExecuteApiEndpoint").equals(False)
    resp.should.have.key("Name").equals("test-api")
    resp.should.have.key("ProtocolType").equals("HTTP")
    resp.should.have.key("RouteSelectionExpression").equals(
        "$request.method $request.path"
    )


@mock_apigatewayv2
def test_create_api():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    resp = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )

    resp.should.have.key("ApiId")
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals("s3l3ction")
    resp.should.have.key("CreatedDate")
    resp.should.have.key("CorsConfiguration").equals(
        {
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        }
    )
    resp.should.have.key("Description").equals("my first api")
    resp.should.have.key("DisableExecuteApiEndpoint").equals(True)
    resp.should.have.key("DisableSchemaValidation").equals(True)
    resp.should.have.key("Name").equals("test-api")
    resp.should.have.key("ProtocolType").equals("HTTP")
    resp.should.have.key("RouteSelectionExpression").equals("route_s3l3ction")
    resp.should.have.key("Version").equals("1.0")


@mock_apigatewayv2
def test_delete_api():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="t", ProtocolType="HTTP")["ApiId"]

    client.delete_api(ApiId=api_id)

    with pytest.raises(ClientError) as exc:
        client.get_api(ApiId=api_id)
    exc.value.response["Error"]["Code"].should.equal("NotFoundException")


@mock_apigatewayv2
def test_delete_cors_configuration():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    client.delete_cors_configuration(ApiId=api_id)

    resp = client.get_api(ApiId=api_id)

    resp.shouldnt.have.key("CorsConfiguration")
    resp.should.have.key("Description").equals("my first api")
    resp.should.have.key("Name").equals("test-api")


@mock_apigatewayv2
def test_get_api_unknown():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.get_api(ApiId="unknown")

    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal("Invalid API identifier specified unknown")


@mock_apigatewayv2
def test_get_api():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    api_id = client.create_api(Name="test-get-api", ProtocolType="WEBSOCKET")["ApiId"]

    resp = client.get_api(ApiId=api_id)

    resp.should.have.key("ApiId").equals(api_id)
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.ap-southeast-1.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals(
        "$request.header.x-api-key"
    )
    resp.should.have.key("CreatedDate")
    resp.should.have.key("DisableExecuteApiEndpoint").equals(False)
    resp.should.have.key("Name").equals("test-get-api")
    resp.should.have.key("ProtocolType").equals("WEBSOCKET")
    resp.should.have.key("RouteSelectionExpression").equals(
        "$request.method $request.path"
    )


@mock_apigatewayv2
def test_get_apis():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    client.get_apis().should.have.key("Items").length_of(0)

    api_id_1 = client.create_api(Name="api1", ProtocolType="HTTP")["ApiId"]
    api_id_2 = client.create_api(Name="api2", ProtocolType="WEBSOCKET")["ApiId"]
    client.get_apis().should.have.key("Items").length_of(2)

    api_ids = [i["ApiId"] for i in client.get_apis()["Items"]]
    api_ids.should.contain(api_id_1)
    api_ids.should.contain(api_id_2)


@mock_apigatewayv2
def test_update_api_minimal():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    resp = client.update_api(
        ApiId=api_id,
        CorsConfiguration={
            "AllowCredentials": False,
            "AllowHeaders": ["x-header2"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header2"],
            "MaxAge": 2,
        },
    )

    resp.should.have.key("ApiId")
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals("s3l3ction")
    resp.should.have.key("CreatedDate")
    resp.should.have.key("CorsConfiguration").equals(
        {
            "AllowCredentials": False,
            "AllowHeaders": ["x-header2"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header2"],
            "MaxAge": 2,
        }
    )
    resp.should.have.key("Description").equals("my first api")
    resp.should.have.key("DisableExecuteApiEndpoint").equals(True)
    resp.should.have.key("DisableSchemaValidation").equals(True)
    resp.should.have.key("Name").equals("test-api")
    resp.should.have.key("ProtocolType").equals("HTTP")
    resp.should.have.key("RouteSelectionExpression").equals("route_s3l3ction")
    resp.should.have.key("Version").equals("1.0")


@mock_apigatewayv2
def test_update_api_empty_fields():
    client = boto3.client("apigatewayv2", region_name="eu-west-1")
    api_id = client.create_api(
        ApiKeySelectionExpression="s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["x-header1"],
            "AllowMethods": ["GET", "PUT"],
            "AllowOrigins": ["google.com"],
            "ExposeHeaders": ["x-header1"],
            "MaxAge": 2,
        },
        Description="my first api",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="test-api",
        ProtocolType="HTTP",
        RouteSelectionExpression="route_s3l3ction",
        Version="1.0",
    )["ApiId"]

    resp = client.update_api(ApiId=api_id, Description="", Name="updated", Version="")

    resp.should.have.key("ApiId")
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.eu-west-1.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals("s3l3ction")
    resp.should.have.key("Description").equals("")
    resp.should.have.key("DisableExecuteApiEndpoint").equals(True)
    resp.should.have.key("DisableSchemaValidation").equals(True)
    resp.should.have.key("Name").equals("updated")
    resp.should.have.key("ProtocolType").equals("HTTP")
    resp.should.have.key("RouteSelectionExpression").equals("route_s3l3ction")
    resp.should.have.key("Version").equals("")


@mock_apigatewayv2
def test_update_api():
    client = boto3.client("apigatewayv2", region_name="us-east-2")
    api_id = client.create_api(Name="test-api", ProtocolType="HTTP")["ApiId"]

    resp = client.update_api(
        ApiId=api_id,
        ApiKeySelectionExpression="api_key_s3l3ction",
        CorsConfiguration={
            "AllowCredentials": True,
            "AllowHeaders": ["X-Amz-Target"],
            "AllowMethods": ["GET"],
        },
        CredentialsArn="credentials:arn",
        Description="updated API",
        DisableSchemaValidation=True,
        DisableExecuteApiEndpoint=True,
        Name="new name",
        RouteKey="route key",
        RouteSelectionExpression="route_s3l3ction",
        Target="updated target",
        Version="1.1",
    )

    resp.should.have.key("ApiId")
    resp.should.have.key("ApiEndpoint").equals(
        f"https://{resp['ApiId']}.execute-api.us-east-2.amazonaws.com"
    )
    resp.should.have.key("ApiKeySelectionExpression").equals("api_key_s3l3ction")
    resp.should.have.key("CorsConfiguration").equals(
        {
            "AllowCredentials": True,
            "AllowHeaders": ["X-Amz-Target"],
            "AllowMethods": ["GET"],
        }
    )
    resp.should.have.key("CreatedDate")
    resp.should.have.key("Description").equals("updated API")
    resp.should.have.key("DisableSchemaValidation").equals(True)
    resp.should.have.key("DisableExecuteApiEndpoint").equals(True)
    resp.should.have.key("Name").equals("new name")
    resp.should.have.key("ProtocolType").equals("HTTP")
    resp.should.have.key("RouteSelectionExpression").equals("route_s3l3ction")
    resp.should.have.key("Version").equals("1.1")


@mock_apigatewayv2
def test_create_domain_name():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    domain_name = "dev"
    tags = {"tag": "it"}
    expected_keys = [
        "DomainName",
        "ApiMappingSelectionExpression",
        "DomainNameConfigurations",
        "MutualTlsAuthentication",
        "Tags",
    ]

    post_resp = client.create_domain_name(DomainName=domain_name, Tags=tags)
    get_resp = client.get_domain_name(DomainName=domain_name)

    # check post response has all keys
    for key in expected_keys:
        post_resp.should.have.key(key)

    # check get response has all keys
    for key in expected_keys:
        get_resp.should.have.key(key)

    # check that values are equal for post and get of same resource
    for key in expected_keys:
        post_resp.get(key).should.equal(get_resp.get(key))

    # ensure known values are set correct in post response
    post_resp.get("DomainName").should.equal(domain_name)
    post_resp.get("Tags").should.equal(tags)


@mock_apigatewayv2
def test_get_domain_names():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    dev_domain = client.create_domain_name(DomainName="dev.service.io")
    prod_domain = client.create_domain_name(DomainName="prod.service.io")

    # sanity check responses
    dev_domain.should.have.key("DomainName").equals("dev.service.io")
    prod_domain.should.have.key("DomainName").equals("prod.service.io")

    # make comparable
    del dev_domain["ResponseMetadata"]
    del prod_domain["ResponseMetadata"]

    get_resp = client.get_domain_names()
    get_resp.should.have.key("Items")
    get_resp.get("Items").should.contain(dev_domain)
    get_resp.get("Items").should.contain(prod_domain)


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
