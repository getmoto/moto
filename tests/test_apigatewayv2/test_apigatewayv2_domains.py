import boto3
import botocore.exceptions
import pytest

from moto import mock_aws


@mock_aws
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
        assert key in post_resp

    # check get response has all keys
    for key in expected_keys:
        assert key in get_resp

    # check that values are equal for post and get of same resource
    for key in expected_keys:
        assert post_resp.get(key) == get_resp.get(key)

    # ensure known values are set correct in post response
    assert post_resp.get("DomainName") == domain_name
    assert post_resp.get("Tags") == tags


@mock_aws
def test_create_domain_name_already_exists():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    client.create_domain_name(DomainName="exists.io")

    with pytest.raises(botocore.exceptions.ClientError) as exc:
        client.create_domain_name(DomainName="exists.io")

    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "The domain name resource already exists."


@mock_aws
def test_get_domain_names():
    client = boto3.client("apigatewayv2", region_name="us-east-1")
    dev_domain = client.create_domain_name(DomainName="dev.service.io")
    prod_domain = client.create_domain_name(DomainName="prod.service.io")

    # sanity check responses
    assert dev_domain["DomainName"] == "dev.service.io"
    assert prod_domain["DomainName"] == "prod.service.io"

    # make comparable
    del dev_domain["ResponseMetadata"]
    del prod_domain["ResponseMetadata"]

    get_resp = client.get_domain_names()
    assert "Items" in get_resp
    assert dev_domain in get_resp.get("Items")
    assert prod_domain in get_resp.get("Items")


@mock_aws
def test_delete_domain_name():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    post_resp = client.create_domain_name(DomainName="dev.service.io")
    client.delete_domain_name(DomainName="dev.service.io")
    get_resp = client.get_domain_names()

    del post_resp["ResponseMetadata"]
    assert "Items" in get_resp
    assert post_resp not in get_resp.get("Items")


@mock_aws
def test_delete_domain_name_dne():
    client = boto3.client("apigatewayv2", region_name="ap-southeast-1")
    with pytest.raises(botocore.exceptions.ClientError) as exc:
        client.delete_domain_name(DomainName="dne.io")

    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "The domain name resource specified in the request was not found."
    )
