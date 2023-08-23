import boto3
import uuid


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
  BucketArn:
    Value: !GetAtt BucketWithSemiRandomName.Arn
    Description: ARN for bucket
"""


def _create_cf_template_in_s3(region_name: str, create_bucket: bool = True):
    """
    Creates a bucket and uploads a cloudformation template to be used in product provisioning
    """
    cloud_bucket = "cf-servicecatalog"
    cloud_s3_key = "sc-templates/test-product/stack.yaml"
    cloud_url = f"https://s3.amazonaws.com/{cloud_bucket}/{cloud_s3_key}"
    s3_client = boto3.client("s3", region_name=region_name)
    if create_bucket:
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


def _create_product(region_name: str, product_name: str, create_bucket=True):
    cloud_url = _create_cf_template_in_s3(region_name, create_bucket)
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
