import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_apigatewayv2


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
