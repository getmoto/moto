"""Unit tests for servicecatalog-supported APIs."""
import pytest
import boto3
import uuid
from datetime import date
from moto import mock_servicecatalog, mock_s3
from botocore.exceptions import ClientError, ParamValidationError

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

BASIC_CLOUD_STACK = """---
Resources:
  BucketWithSemiRandomName:
    Type: "AWS::S3::Bucket"
    Properties:
      BucketName: !Join
        - "-"
        - - "bucket-with-semi-random-name"
          - !Select
            - 0
            - !Split
              - "-"
              - !Select
                - 2
                - !Split
                  - "/"
                  - !Ref "AWS::StackId"
Outputs:
  WebsiteURL:
    Value: !GetAtt BucketWithSemiRandomName.WebsiteURL
    Description: URL for website hosted on S3
"""


def _create_cf_template_in_s3(region_name: str):
    """
    Creates a bucket and uploads a cloudformation template to be used in product provisioning
    """
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


def _create_portfolio(region_name: str, portfolio_name: str):
    client = boto3.client("servicecatalog", region_name=region_name)

    # Create portfolio
    create_portfolio_response = client.create_portfolio(
        DisplayName=portfolio_name, ProviderName="Test Provider"
    )
    return create_portfolio_response


def _create_product(region_name: str, product_name: str):
    cloud_url = _create_cf_template_in_s3(region_name)
    client = boto3.client("servicecatalog", region_name=region_name)
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
    return create_product_response


def _create_product_with_portfolio(
    region_name: str, portfolio_name: str, product_name: str
):
    """
    Create a portfolio and product with a uploaded cloud formation template
    """

    create_portfolio_response = _create_portfolio(
        region_name=region_name, portfolio_name=portfolio_name
    )
    create_product_response = _create_product(
        region_name=region_name, product_name=product_name
    )

    client = boto3.client("servicecatalog", region_name=region_name)

    # Associate product to portfolio
    client.associate_product_with_portfolio(
        PortfolioId=create_portfolio_response["PortfolioDetail"]["Id"],
        ProductId=create_product_response["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ],
    )
    return create_portfolio_response, create_product_response


def _create_product_with_constraint(
    region_name: str,
    portfolio_name: str,
    product_name: str,
    role_arn: str = "arn:aws:iam::123456789012:role/LaunchRole",
):
    """
    Create a portfolio and product with a uploaded cloud formation template including
    a launch constraint on the roleARN
    """
    portfolio, product = _create_product_with_portfolio(
        region_name=region_name,
        portfolio_name=portfolio_name,
        product_name=product_name,
    )
    client = boto3.client("servicecatalog", region_name=region_name)
    create_constraint_response = client.create_constraint(
        PortfolioId=portfolio["PortfolioDetail"]["Id"],
        ProductId=product["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
        Parameters=f"""{{"RoleArn": "{role_arn}"}}""",
        Type="LAUNCH",
    )
    return create_constraint_response, portfolio, product


def _create_provisioned_product(
    region_name: str,
    product_name: str,
    provisioning_artifact_id: str,
    provisioned_product_name: str,
):
    """
    Create a provisioned product from the specified product_name
    """
    client = boto3.client("servicecatalog", region_name=region_name)
    # TODO: Path from launch object
    provisioned_product_response = client.provision_product(
        ProvisionedProductName=provisioned_product_name,
        ProvisioningArtifactId=provisioning_artifact_id,
        PathId="TODO: Launch path",
        ProductName=product_name,
        Tags=[
            {"Key": "MyCustomTag", "Value": "A Value"},
            {"Key": "MyOtherTag", "Value": "Another Value"},
        ],
    )
    return provisioned_product_response


def _create_portfolio_with_provisioned_product(
    region_name: str,
    portfolio_name: str,
    product_name: str,
    provisioned_product_name: str,
):

    constraint, portfolio, product = _create_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name=portfolio_name,
    )

    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]
    provisioned_product = _create_provisioned_product(
        region_name=region_name,
        product_name=product_name,
        provisioning_artifact_id=provisioning_artifact_id,
        provisioned_product_name=provisioned_product_name,
    )

    return constraint, portfolio, product, provisioned_product


@mock_servicecatalog
def test_create_portfolio():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    resp = client.create_portfolio(
        DisplayName="Test Portfolio",
        ProviderName="Test Provider",
        Tags=[
            {"Key": "FirstTag", "Value": "FirstTagValue"},
            {"Key": "SecondTag", "Value": "SecondTagValue"},
        ],
    )

    assert "PortfolioDetail" in resp
    portfolio = resp["PortfolioDetail"]
    assert portfolio["DisplayName"] == "Test Portfolio"
    assert portfolio["ProviderName"] == "Test Provider"
    assert "Tags" in resp
    assert len(resp["Tags"]) == 2
    assert resp["Tags"][0]["Key"] == "FirstTag"
    assert resp["Tags"][0]["Value"] == "FirstTagValue"


@mock_servicecatalog
def test_create_portfolio_duplicate():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    client.create_portfolio(DisplayName="Test Portfolio", ProviderName="Test Provider")

    with pytest.raises(ClientError) as exc:
        client.create_portfolio(
            DisplayName="Test Portfolio", ProviderName="Test Provider"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParametersException"
    assert err["Message"] == "Portfolio with this name already exists"


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
        Tags=[
            {"Key": "FirstTag", "Value": "FirstTagValue"},
            {"Key": "SecondTag", "Value": "SecondTagValue"},
        ],
    )

    assert "ProductViewDetail" in resp
    assert resp["ProductViewDetail"]["Status"] == "AVAILABLE"
    product = resp["ProductViewDetail"]["ProductViewSummary"]
    assert product["Name"] == "test product"
    assert product["Owner"] == "owner arn"
    assert product["ShortDescription"] == "description"
    assert product["SupportEmail"] == "test@example.com"

    assert "ProvisioningArtifactDetail" in resp
    artifact = resp["ProvisioningArtifactDetail"]
    assert artifact["Name"] == "InitialCreation"
    assert artifact["Type"] == "CLOUD_FORMATION_TEMPLATE"

    assert "Tags" in resp
    assert len(resp["Tags"]) == 2
    assert resp["Tags"][0]["Key"] == "FirstTag"
    assert resp["Tags"][0]["Value"] == "FirstTagValue"


@mock_servicecatalog
@mock_s3
def test_create_product_duplicate():
    region_name = "us-east-2"
    cloud_url = _create_cf_template_in_s3(region_name=region_name)

    client = boto3.client("servicecatalog", region_name=region_name)
    client.create_product(
        Name="test product",
        Owner="owner arn",
        ProductType="CLOUD_FORMATION_TEMPLATE",
        ProvisioningArtifactParameters={
            "Name": "InitialCreation",
            "Info": {"LoadTemplateFromURL": cloud_url},
        },
        IdempotencyToken=str(uuid.uuid4()),
    )

    with pytest.raises(ClientError) as exc:
        client.create_product(
            Name="test product",
            Owner="owner arn",
            ProductType="CLOUD_FORMATION_TEMPLATE",
            ProvisioningArtifactParameters={
                "Name": "InitialCreation",
                "Info": {"LoadTemplateFromURL": cloud_url},
            },
            IdempotencyToken=str(uuid.uuid4()),
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParametersException"
    assert err["Message"] == "Product with this name already exists"


@mock_servicecatalog
@mock_s3
def test_create_constraint():
    region_name = "us-east-2"
    portfolio, product = _create_product_with_portfolio(
        region_name=region_name,
        portfolio_name="My Portfolio",
        product_name="test product",
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

    portfolio = _create_portfolio(
        region_name=region_name, portfolio_name="The Portfolio"
    )
    product = _create_product(region_name=region_name, product_name="My Product")
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    # Verify product is not linked to portfolio
    client = boto3.client("servicecatalog", region_name=region_name)
    linked = client.list_portfolios_for_product(ProductId=product_id)
    assert len(linked["PortfolioDetails"]) == 0

    # Link product to portfolio
    resp = client.associate_product_with_portfolio(
        PortfolioId=portfolio["PortfolioDetail"]["Id"],
        ProductId=product["ProductViewDetail"]["ProductViewSummary"]["ProductId"],
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Verify product is now linked to portfolio
    linked = client.list_portfolios_for_product(ProductId=product_id)
    assert len(linked["PortfolioDetails"]) == 1
    assert linked["PortfolioDetails"][0]["Id"] == portfolio["PortfolioDetail"]["Id"]


@mock_servicecatalog
@mock_s3
def test_provision_product_by_product_name_and_artifact_id():
    region_name = "us-east-2"
    product_name = "My Product"
    portfolio, product = _create_product_with_portfolio(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="The Portfolio",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]

    # TODO: Paths
    provisioned_product_response = client.provision_product(
        ProvisionedProductName="Provisioned Product Name",
        ProvisioningArtifactId=provisioning_artifact_id,
        PathId="TODO",
        ProductName=product_name,
        Tags=[
            {"Key": "MyCustomTag", "Value": "A Value"},
            {"Key": "MyOtherTag", "Value": "Another Value"},
        ],
    )
    provisioned_product_id = provisioned_product_response["RecordDetail"][
        "ProvisionedProductId"
    ]
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    # Verify record details
    rec = provisioned_product_response["RecordDetail"]
    assert rec["ProvisionedProductName"] == "Provisioned Product Name"
    assert rec["Status"] == "CREATED"
    assert rec["ProductId"] == product_id
    assert rec["ProvisionedProductId"] == provisioned_product_id
    assert rec["ProvisionedProductType"] == "CFN_STACK"
    assert rec["ProvisioningArtifactId"] == provisioning_artifact_id
    assert rec["PathId"] == ""
    assert rec["RecordType"] == "PROVISION_PRODUCT"
    # tags

    # Verify cloud formation stack has been created - this example creates a bucket named "cfn-quickstart-bucket"
    s3_client = boto3.client("s3", region_name=region_name)
    all_buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in all_buckets_response["Buckets"]]

    assert any(
        [name.startswith("bucket-with-semi-random-name") for name in bucket_names]
    )


@mock_servicecatalog
@mock_s3
def test_provision_product_by_artifact_name_and_product_id():
    region_name = "us-east-2"

    portfolio, product = _create_product_with_portfolio(
        region_name=region_name,
        product_name="My Product",
        portfolio_name="The Portfolio",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    provisioning_artifact_name = product["ProvisioningArtifactDetail"]["Name"]
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    # TODO: Paths
    provisioned_product_response = client.provision_product(
        ProvisionedProductName="Provisioned Product Name",
        ProvisioningArtifactName=provisioning_artifact_name,
        PathId="TODO",
        ProductId=product_id,
        Tags=[
            {"Key": "MyCustomTag", "Value": "A Value"},
            {"Key": "MyOtherTag", "Value": "Another Value"},
        ],
    )

    # Verify record details
    rec = provisioned_product_response["RecordDetail"]
    assert rec["ProvisionedProductName"] == "Provisioned Product Name"

    # Verify cloud formation stack has been created - this example creates a bucket named "cfn-quickstart-bucket"
    s3_client = boto3.client("s3", region_name=region_name)
    all_buckets_response = s3_client.list_buckets()
    bucket_names = [bucket["Name"] for bucket in all_buckets_response["Buckets"]]

    assert any(
        [name.startswith("bucket-with-semi-random-name") for name in bucket_names]
    )


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
def test_describe_portfolio():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    assert len(client.list_portfolios()["PortfolioDetails"]) == 0

    portfolio_id = client.create_portfolio(DisplayName="test-1", ProviderName="prov-1")[
        "PortfolioDetail"
    ]["Id"]

    portfolio_response = client.describe_portfolio(Id=portfolio_id)
    assert portfolio_id == portfolio_response["PortfolioDetail"]["Id"]


@mock_servicecatalog
def test_describe_portfolio_not_existing():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    assert len(client.list_portfolios()["PortfolioDetails"]) == 0

    with pytest.raises(ClientError) as exc:
        client.describe_portfolio(Id="not-found")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Portfolio not found"


@mock_servicecatalog
@mock_s3
def test_describe_provisioned_product():
    region_name = "us-east-2"
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
        provisioned_product_name="My Provisioned Product",
    )
    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]

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

    resp = client.search_provisioned_products(Filters={"SearchQuery": []})


@mock_servicecatalog
@mock_s3
def test_get_provisioned_product_outputs():
    region_name = "us-east-2"
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
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
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
        provisioned_product_name="My Provisioned Product",
    )
    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]
    provisioning_artifact_id = product["ProvisioningArtifactDetail"]["Id"]
    provisioned_product_2 = _create_provisioned_product(
        region_name=region_name,
        product_name="test product",
        provisioning_artifact_id=provisioning_artifact_id,
        provisioned_product_name="Second Provisioned Product",
    )
    provisioned_product_id_2 = provisioned_product_2["RecordDetail"][
        "ProvisionedProductId"
    ]

    client = boto3.client("servicecatalog", region_name=region_name)

    resp = client.search_provisioned_products()

    pps = resp["ProvisionedProducts"]
    assert len(pps) == 2
    assert pps[0]["Id"] == provisioned_product_id
    assert pps[1]["Id"] == provisioned_product_id_2


@mock_servicecatalog
@mock_s3
def test_search_provisioned_products_filter_by():
    region_name = "us-east-2"
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
        provisioned_product_name="My Provisioned Product",
    )
    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)

    resp = client.search_provisioned_products(
        Filters={"SearchQuery": ["name:My Provisioned Product"]}
    )

    assert len(resp["ProvisionedProducts"]) == 1
    assert resp["ProvisionedProducts"][0]["Id"] == provisioned_product_id


@mock_servicecatalog
@mock_s3
def test_terminate_provisioned_product():
    region_name = "us-east-2"
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
        provisioned_product_name="My Provisioned Product",
    )

    provisioned_product_id = provisioned_product["RecordDetail"]["ProvisionedProductId"]
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.terminate_provisioned_product(
        ProvisionedProductId=provisioned_product_id
    )

    rec = resp["RecordDetail"]
    assert rec["RecordType"] == "TERMINATE_PROVISIONED_PRODUCT"
    assert rec["ProductId"] == product_id
    assert rec["ProvisionedProductId"] == provisioned_product_id


@mock_servicecatalog
@mock_s3
def test_search_products():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_product_with_constraint(
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

    constraint, portfolio, product = _create_product_with_constraint(
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
def test_list_launch_paths_no_constraints_attached():
    portfolio, product = _create_product_with_portfolio(
        region_name="us-east-2",
        product_name="test product",
        portfolio_name="Test Portfolio",
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    client = boto3.client("servicecatalog", region_name="us-east-2")
    resp = client.list_launch_paths(ProductId=product_id)

    lps = resp["LaunchPathSummaries"]
    assert len(lps) == 1
    assert len(lps[0]["ConstraintSummaries"]) == 0


@mock_servicecatalog
@mock_s3
def test_list_provisioning_artifacts():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_product_with_constraint(
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


@mock_servicecatalog
@mock_s3
def test_describe_product_as_admin():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.describe_product_as_admin(Id=product_id)

    assert resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"] == product_id
    assert len(resp["ProvisioningArtifactSummaries"]) == 1


@mock_servicecatalog
@mock_s3
def test_describe_product():
    region_name = "us-east-2"
    product_name = "test product"

    constraint, portfolio, product = _create_product_with_constraint(
        region_name=region_name,
        product_name=product_name,
        portfolio_name="Test Portfolio",
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.describe_product_as_admin(Id=product_id)

    assert resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"] == product_id
    assert len(resp["ProvisioningArtifactSummaries"]) == 1


@mock_servicecatalog
@mock_s3
def test_update_portfolio():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")

    create_portfolio_response = client.create_portfolio(
        DisplayName="Original Name", ProviderName="Test Provider"
    )

    portfolio_id = create_portfolio_response["PortfolioDetail"]["Id"]
    new_portfolio_name = "New Portfolio Name"
    resp = client.update_portfolio(
        Id=portfolio_id,
        DisplayName=new_portfolio_name,
    )

    assert resp["PortfolioDetail"]["Id"] == portfolio_id
    assert resp["PortfolioDetail"]["DisplayName"] == new_portfolio_name


@mock_servicecatalog
@mock_s3
def test_update_product():
    product = _create_product(region_name="ap-southeast-1", product_name="Test Product")
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    resp = client.update_product(Id=product_id, Name="New Product Name")
    new_product = resp["ProductViewDetail"]["ProductViewSummary"]
    assert new_product["Name"] == "New Product Name"


@mock_servicecatalog
@mock_s3
def test_list_portfolios_for_product():
    region_name = "us-east-2"
    product_name = "test product"

    portfolio, product = _create_product_with_portfolio(
        region_name=region_name,
        portfolio_name="My Portfolio",
        product_name=product_name,
    )
    product_id = product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.list_portfolios_for_product(ProductId=product_id)

    assert resp["PortfolioDetails"][0]["Id"] == portfolio["PortfolioDetail"]["Id"]


@mock_servicecatalog
@mock_s3
def test_describe_record():
    region_name = "eu-west-1"
    (
        constraint,
        portfolio,
        product,
        provisioned_product,
    ) = _create_portfolio_with_provisioned_product(
        region_name=region_name,
        product_name="test product",
        portfolio_name="Test Portfolio",
        provisioned_product_name="My Provisioned Product",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.describe_record(Id=provisioned_product["RecordDetail"]["RecordId"])

    assert (
        resp["RecordDetail"]["RecordId"]
        == provisioned_product["RecordDetail"]["RecordId"]
    )
