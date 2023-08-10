"""Unit tests for servicecatalog-supported APIs."""
import boto3
import uuid
from datetime import date
from moto import mock_servicecatalog, mock_s3

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

BASIC_CLOUD_STACK = """---
Resources:
  LocalBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: cfn-quickstart-bucket
Outputs:
  WebsiteURL:
    Value: !GetAtt LocalBucket.WebsiteURL
    Description: URL for website hosted on S3
"""


def _create_cf_template_in_s3(region_name: str):
    cloud_bucket = "cf-servicecatalog"
    cloud_s3_key = "sc-templates/test-product/stack.yaml"
    cloud_url = f"https://s3.amazonaws.com/{cloud_bucket}/{cloud_s3_key}"
    s3_client = boto3.client("s3", region_name=region_name)
    s3_client.create_bucket(
        Bucket=cloud_bucket,
        CreateBucketConfiguration={
            "LocationConstraint": region_name,
        },
    )
    s3_client.put_object(Body=BASIC_CLOUD_STACK, Bucket=cloud_bucket, Key=cloud_s3_key)
    return cloud_url


def _create_default_product_with_portfolio(
    region_name: str, portfolio_name: str, product_name: str
):

    cloud_url = _create_cf_template_in_s3(region_name)

    client = boto3.client("servicecatalog", region_name=region_name)

    # Create portfolio
    create_portfolio_response = client.create_portfolio(
        DisplayName=portfolio_name, ProviderName="Test Provider"
    )

    # Create Product
    create_product_response = client.create_product(
        Name=product_name,
        Owner="owner arn",
        Description="description",
        SupportEmail="test@example.com",
        ProductType="CLOUD_FORMATION_TEMPLATE",
        ProvisioningArtifactParameters={
            "Name": "InitialCreation",
            "Description": "InitialCreation",
            "Info": {"LoadTemplateFromURL": cloud_url},
            "Type": "CLOUD_FORMATION_TEMPLATE",
        },
        IdempotencyToken=str(uuid.uuid4()),
    )

    # Associate product to portfolio
    resp = client.associate_product_with_portfolio(
        PortfolioId=create_portfolio_response["PortfolioDetail"]["Id"],
        ProductId=create_product_response["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ],
    )
    return create_portfolio_response, create_product_response


def _create_default_product_with_constraint(
    region_name: str, portfolio_name: str, product_name: str
):
    portfolio, product = _create_default_product_with_portfolio(
        region_name=region_name,
        portfolio_name=portfolio_name,
        product_name=product_name,
    )
    client = boto3.client("servicecatalog", region_name=region_name)
    create_constraint_response = client.create_constraint(
        PortfolioId=portfolio["PortfolioDetail"]["Id"],
        ProductId=product["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
        Parameters="""{"RoleArn": "arn:aws:iam::123456789012:role/LaunchRole"}""",
        Type="LAUNCH",
    )
    return create_constraint_response, portfolio, product


def _create_provisioned_product(
    region_name: str,
    product_name: str,
    provisioning_artifact_id: str,
    provisioned_product_name: str,
):
    client = boto3.client("servicecatalog", region_name=region_name)

    stack_id = uuid.uuid4().hex
    today = date.today()
    today = today.strftime("%Y%m%d")
    requesting_user = "test-user"
    provisioning_product_name = requesting_user + "-" + today + "_" + stack_id

    provisioned_product_response = client.provision_product(
        ProvisionedProductName=provisioned_product_name,
        ProvisioningArtifactId=provisioning_artifact_id,
        PathId="asdf",
        ProductName=product_name,
        Tags=[
            {"Key": "MyCustomTag", "Value": "A Value"},
            {"Key": "MyOtherTag", "Value": "Another Value"},
        ],
    )
    return provisioned_product_response


@mock_servicecatalog
def test_create_portfolio():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    resp = client.create_portfolio(
        DisplayName="Test Portfolio", ProviderName="Test Provider"
    )

    assert resp is not None
    assert "PortfolioDetail" in resp


@mock_servicecatalog
@mock_s3
def test_create_product():
    region_name = "us-east-2"
    cloud_url = _create_cf_template_in_s3(region_name=region_name)

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.create_product(
        Name="test product",
        Owner="owner arn",
        Description="description",
        SupportEmail="test@example.com",
        ProductType="CLOUD_FORMATION_TEMPLATE",
        ProvisioningArtifactParameters={
            "Name": "InitialCreation",
            "Description": "InitialCreation",
            "Info": {"LoadTemplateFromURL": cloud_url},
            "Type": "CLOUD_FORMATION_TEMPLATE",
        },
        IdempotencyToken=str(uuid.uuid4()),
    )
    # TODO: Much more comprehensive
    assert "ProductViewDetail" in resp
    assert "ProvisioningArtifactDetail" in resp


@mock_servicecatalog
@mock_s3
def test_create_constraint():
    region_name = "us-east-2"
    product_name = "test product"

    portfolio, product = _create_default_product_with_portfolio(
        region_name=region_name,
        portfolio_name="My Portfolio",
        product_name=product_name,
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.create_constraint(
        PortfolioId=portfolio["PortfolioDetail"]["Id"],
        ProductId=product["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
        Parameters="""{"RoleArn": "arn:aws:iam::123456789012:role/LaunchRole"}""",
        Type="LAUNCH",
    )

    assert "ConstraintDetail" in resp
    assert "ConstraintParameters" in resp
    assert resp["Status"] == "AVAILABLE"


@mock_servicecatalog
@mock_s3
def test_associate_product_with_portfolio():
    region_name = "us-east-2"
    portfolio, product = _create_default_product_with_portfolio(
        region_name=region_name,
        product_name="My PRoduct",
        portfolio_name="The Portfolio",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.associate_product_with_portfolio(
        PortfolioId=portfolio["PortfolioDetail"]["Id"],
        ProductId=product["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_servicecatalog
@mock_s3
def test_provision_product():
    region_name = "us-east-2"
    product_name = "My PRoduct"
    portfolio, product = _create_default_product_with_portfolio(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="The Portfolio",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]

    stack_id = uuid.uuid4().hex
    today = date.today()
    today = today.strftime("%Y%m%d")
    requesting_user = "test-user"
    provisioning_product_name = requesting_user + "-" + today + "_" + stack_id

    provisioned_product_response = client.provision_product(
        ProvisionedProductName=provisioning_product_name,
        ProvisioningArtifactId=provisioning_artifact_id,
        PathId="asdf",
        ProductName=product_name,
        Tags=[
            {"Key": "MyCustomTag", "Value": "A Value"},
            {"Key": "MyOtherTag", "Value": "Another Value"},
        ],
    )
    print(provisioned_product_response)

    s3_client = boto3.client("s3", region_name=region_name)
    all_buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in all_buckets_response["Buckets"]]

    assert "cfn-quickstart-bucket" in bucket_names


@mock_servicecatalog
def test_list_portfolios():

    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    assert len(client.list_portfolios()["PortfolioDetails"]) == 0

    portfolio_id_1 = client.create_portfolio(
        DisplayName="test-1", ProviderName="prov-1"
    )["PortfolioDetail"]["Id"]
    portfolio_id_2 = client.create_portfolio(
        DisplayName="test-2", ProviderName="prov-1"
    )["PortfolioDetail"]["Id"]

    assert len(client.list_portfolios()["PortfolioDetails"]) == 2
    portfolio_ids = [i["Id"] for i in client.list_portfolios()["PortfolioDetails"]]

    assert portfolio_id_1 in portfolio_ids
    assert portfolio_id_2 in portfolio_ids


@mock_servicecatalog
@mock_s3
def test_describe_provisioned_product():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )

    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]
    provisioned_product = _create_provisioned_product(
        region_name=region_name,
        product_name=product_name,
        provisioning_artifact_id=provisioning_artifact_id,
        provisioned_product_name="My Provisioned Product",
    )
    client = boto3.client("servicecatalog", region_name=region_name)

    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
    resp = client.describe_provisioned_product(Id=provisioned_product_id)

    assert resp["ProvisionedProductDetail"]["Id"] == provisioned_product_id
    assert resp["ProvisionedProductDetail"]["ProductId"] == product_id
    assert (
        resp["ProvisionedProductDetail"]["ProvisioningArtifactId"]
        == provisioning_artifact_id
    )


@mock_servicecatalog
@mock_s3
def test_get_provisioned_product_outputs():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )

    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]
    provisioned_product = _create_provisioned_product(
        region_name=region_name,
        product_name=product_name,
        provisioning_artifact_id=provisioning_artifact_id,
        provisioned_product_name="My Provisioned Product",
    )
    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)

    resp = client.get_provisioned_product_outputs(
        ProvisionedProductId=provisioned_product_id
    )

    assert len(resp["Outputs"]) == 1
    assert resp["Outputs"][0]["OutputKey"] == "WebsiteURL"


@mock_servicecatalog
@mock_s3
def test_search_provisioned_products():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )

    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]
    provisioned_product = _create_provisioned_product(
        region_name=region_name,
        product_name=product_name,
        provisioning_artifact_id=provisioning_artifact_id,
        provisioned_product_name="My Provisioned Product",
    )
    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)

    resp = client.search_provisioned_products()

    pps = resp["ProvisionedProducts"]
    assert len(pps) == 1
    assert pps[0]["Id"] == provisioned_product_id


@mock_servicecatalog
def test_terminate_provisioned_product():
    client = boto3.client("servicecatalog", region_name="eu-west-1")
    resp = client.terminate_provisioned_product()

    raise Exception("NotYetImplemented")


@mock_servicecatalog
@mock_s3
def test_search_products():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.search_products()

    products = resp["ProductViewSummaries"]

    assert len(products) == 1
    assert products[0]["Id"] == product["ProductViewDetail"]["ProductViewSummary"]["Id"]
    assert (
        products[0]["ProductId"]
        == product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
    )


@mock_servicecatalog
@mock_s3
def test_list_launch_paths():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.list_launch_paths(ProductId=product_id)

    lps = resp["LaunchPathSummaries"]
    assert len(lps) == 1
    assert len(lps[0]["ConstraintSummaries"]) == 1
    assert lps[0]["ConstraintSummaries"][0]["Type"] == "LAUNCH"


@mock_servicecatalog
@mock_s3
def test_list_provisioning_artifacts():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_default_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)

    resp = client.list_provisioning_artifacts(ProductId=product_id)

    pad = resp["ProvisioningArtifactDetails"]
    assert len(pad) == 1
    assert pad[0]["Id"] == product["ProvisioningArtifactDetail"]["Id"]
