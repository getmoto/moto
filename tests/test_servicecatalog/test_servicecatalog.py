"""Unit tests for servicecatalog-supported APIs."""
import pytest
import boto3
import uuid

from moto import mock_servicecatalog, mock_s3
from botocore.exceptions import ClientError, ParamValidationError
from .setupdata import (
    _create_product_with_portfolio,
    _create_cf_template_in_s3,
    _create_portfolio,
    _create_product,
    _create_portfolio_with_provisioned_product,
    _create_provisioned_product,
    _create_product_with_constraint,
)


@mock_servicecatalog
class TestPortfolio:
    def test_create_portfolio(self):
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

    def test_create_portfolio_missing_required(self):
        client = boto3.client("servicecatalog", region_name="ap-southeast-1")
        with pytest.raises(ParamValidationError) as exc:
            client.create_portfolio()

        assert "DisplayName" in exc.value.args[0]

    def test_create_portfolio_duplicate(self):
        client = boto3.client("servicecatalog", region_name="ap-southeast-1")
        client.create_portfolio(
            DisplayName="Test Portfolio", ProviderName="Test Provider"
        )

        with pytest.raises(ClientError) as exc:
            client.create_portfolio(
                DisplayName="Test Portfolio", ProviderName="Test Provider"
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParametersException"
        assert err["Message"] == "Portfolio with this name already exists"

    def test_list_portfolios(self):
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

    def test_describe_portfolio(self):
        client = boto3.client("servicecatalog", region_name="ap-southeast-1")
        assert len(client.list_portfolios()["PortfolioDetails"]) == 0

        portfolio_id = client.create_portfolio(
            DisplayName="test-1", ProviderName="prov-1"
        )["PortfolioDetail"]["Id"]

        portfolio_response = client.describe_portfolio(Id=portfolio_id)
        assert portfolio_id == portfolio_response["PortfolioDetail"]["Id"]

    def test_describe_portfolio_not_existing(self):
        client = boto3.client("servicecatalog", region_name="ap-southeast-1")
        assert len(client.list_portfolios()["PortfolioDetails"]) == 0

        with pytest.raises(ClientError) as exc:
            client.describe_portfolio(Id="not-found")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Portfolio not found"


@mock_servicecatalog
@mock_s3
class TestProduct:
    def setup_method(self, method):
        self.region_name = "us-east-2"
        self.cloud_url = _create_cf_template_in_s3(region_name=self.region_name)

    def test_create_product(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.create_product(
            Name="test product",
            Owner="owner arn",
            Description="description",
            SupportEmail="test@example.com",
            ProductType="CLOUD_FORMATION_TEMPLATE",
            ProvisioningArtifactParameters={
                "Name": "InitialCreation",
                "Description": "InitialCreation",
                "Info": {"LoadTemplateFromURL": self.cloud_url},
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

    def test_create_product_missing_required(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        with pytest.raises(ParamValidationError) as exc:
            client.create_product()

        assert "Name" in exc.value.args[0]

    def test_create_product_duplicate(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        client.create_product(
            Name="test product",
            Owner="owner arn",
            ProductType="CLOUD_FORMATION_TEMPLATE",
            ProvisioningArtifactParameters={
                "Name": "InitialCreation",
                "Info": {"LoadTemplateFromURL": self.cloud_url},
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
                    "Info": {"LoadTemplateFromURL": self.cloud_url},
                },
                IdempotencyToken=str(uuid.uuid4()),
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParametersException"
        assert err["Message"] == "Product with this name already exists"


@mock_servicecatalog
@mock_s3
class TestConstraint:
    def setup_method(self, method):
        self.region_name = "us-east-2"
        self.portfolio, self.product = _create_product_with_portfolio(
            region_name=self.region_name,
            portfolio_name="My Portfolio",
            product_name="test product",
        )

    def test_create_constraint(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.create_constraint(
            PortfolioId=self.portfolio["PortfolioDetail"]["Id"],
            ProductId=self.product["ProductViewDetail"]["ProductViewSummary"][
                "ProductId"
            ],
            Parameters="""{"RoleArn": "arn:aws:iam::123456789012:role/LaunchRole"}""",
            Type="LAUNCH",
        )

        assert "ConstraintDetail" in resp
        assert "ConstraintParameters" in resp
        assert resp["Status"] == "AVAILABLE"

    def test_create_constraint_duplicate(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        client.create_constraint(
            PortfolioId=self.portfolio["PortfolioDetail"]["Id"],
            ProductId=self.product["ProductViewDetail"]["ProductViewSummary"][
                "ProductId"
            ],
            Parameters="""{"RoleArn": "arn:aws:iam::123456789012:role/LaunchRole"}""",
            Type="LAUNCH",
        )
        with pytest.raises(ClientError) as exc:
            client.create_constraint(
                PortfolioId=self.portfolio["PortfolioDetail"]["Id"],
                ProductId=self.product["ProductViewDetail"]["ProductViewSummary"][
                    "ProductId"
                ],
                Parameters="""{"RoleArn": "arn:aws:iam::123456789012:role/LaunchRole"}""",
                Type="LAUNCH",
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "DuplicateResourceException"
        assert err["Message"] == "Constraint with these links already exists"

    def test_create_constraint_missing_required(self):
        client = boto3.client("servicecatalog", region_name="ap-southeast-1")
        with pytest.raises(ParamValidationError) as exc:
            client.create_constraint()

        assert "PortfolioId" in exc.value.args[0]


@mock_servicecatalog
@mock_s3
class TestAssociateProduct:
    def setup_method(self, method):
        self.region_name = "ap-northeast-1"
        self.portfolio = _create_portfolio(
            region_name=self.region_name, portfolio_name="The Portfolio"
        )
        self.product = _create_product(
            region_name=self.region_name, product_name="My Product"
        )
        self.product_id = self.product["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ]

    def test_associate_product_with_portfolio(self):
        # Verify product is not linked to portfolio
        client = boto3.client("servicecatalog", region_name=self.region_name)
        linked = client.list_portfolios_for_product(ProductId=self.product_id)
        assert len(linked["PortfolioDetails"]) == 0

        # Link product to portfolio
        resp = client.associate_product_with_portfolio(
            PortfolioId=self.portfolio["PortfolioDetail"]["Id"],
            ProductId=self.product["ProductViewDetail"]["ProductViewSummary"][
                "ProductId"
            ],
        )
        assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

        # Verify product is now linked to portfolio
        linked = client.list_portfolios_for_product(ProductId=self.product_id)
        assert len(linked["PortfolioDetails"]) == 1
        assert (
            linked["PortfolioDetails"][0]["Id"]
            == self.portfolio["PortfolioDetail"]["Id"]
        )

    def test_associate_product_with_portfolio_invalid_ids(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)

        # Link product to portfolio
        with pytest.raises(ClientError) as exc:
            client.associate_product_with_portfolio(
                PortfolioId="invalid_portfolio",
                ProductId=self.product["ProductViewDetail"]["ProductViewSummary"][
                    "ProductId"
                ],
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Portfolio not found"

        with pytest.raises(ClientError) as exc:
            client.associate_product_with_portfolio(
                PortfolioId=self.portfolio["PortfolioDetail"]["Id"],
                ProductId="invalid_product",
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Product not found"


@mock_servicecatalog
@mock_s3
class TestProvisionProduct:
    def setup_method(self, method):
        self.region_name = "eu-west-1"

        self.product_name = "My Product"
        self.portfolio, self.product = _create_product_with_portfolio(
            region_name=self.region_name,
            product_name=self.product_name,
            portfolio_name="The Portfolio",
        )

        self.provisioning_artifact_id = self.product["ProvisioningArtifactDetail"]["Id"]

    def test_provision_product_by_product_name_and_artifact_id(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)

        # TODO: Paths
        provisioned_product_response = client.provision_product(
            ProvisionedProductName="Provisioned Product Name",
            ProvisioningArtifactId=self.provisioning_artifact_id,
            PathId="TODO",
            ProductName=self.product_name,
            Tags=[
                {"Key": "MyCustomTag", "Value": "A Value"},
                {"Key": "MyOtherTag", "Value": "Another Value"},
            ],
        )
        provisioned_product_id = provisioned_product_response["RecordDetail"][
            "ProvisionedProductId"
        ]
        product_id = self.product["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ]

        # Verify record details
        rec = provisioned_product_response["RecordDetail"]
        assert rec["ProvisionedProductName"] == "Provisioned Product Name"
        assert rec["Status"] == "CREATED"
        assert rec["ProductId"] == product_id
        assert rec["ProvisionedProductId"] == provisioned_product_id
        assert rec["ProvisionedProductType"] == "CFN_STACK"
        assert rec["ProvisioningArtifactId"] == self.provisioning_artifact_id
        assert rec["PathId"] == ""
        assert rec["RecordType"] == "PROVISION_PRODUCT"
        # tags

        # Verify cloud formation stack has been created - this example creates a bucket named "cfn-quickstart-bucket"
        s3_client = boto3.client("s3", region_name=self.region_name)
        all_buckets_response = s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in all_buckets_response["Buckets"]]

        assert any(
            [name.startswith("bucket-with-semi-random-name") for name in bucket_names]
        )

    def test_provision_product_by_artifact_name_and_product_id(
        self,
    ):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        provisioning_artifact_name = self.product["ProvisioningArtifactDetail"]["Name"]
        product_id = self.product["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ]
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
        s3_client = boto3.client("s3", region_name=self.region_name)
        all_buckets_response = s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in all_buckets_response["Buckets"]]

        assert any(
            [name.startswith("bucket-with-semi-random-name") for name in bucket_names]
        )

    def test_provision_product_by_artifact_id_and_product_id_and_path_id(self):
        assert 1 == 2

    def test_provision_product_by_artifact_id_and_product_id_and_path_name(self):
        assert 1 == 2

    def test_provision_product_with_parameters(self):
        assert 1 == 2


@mock_servicecatalog
@mock_s3
class TestListAndDescribeProvisionedProduct:
    def setup_method(self, method):
        self.region_name = "eu-west-1"

        (
            self.constraint,
            self.portfolio,
            self.product,
            self.provisioned_product,
        ) = _create_portfolio_with_provisioned_product(
            region_name=self.region_name,
            product_name="test product",
            portfolio_name="Test Portfolio",
            provisioned_product_name="My Provisioned Product",
        )
        self.provisioning_artifact_id = self.product["ProvisioningArtifactDetail"]["Id"]
        self.provisioned_product_id = self.provisioned_product["RecordDetail"][
            "ProvisionedProductId"
        ]
        self.product_id = self.product["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ]

    def test_describe_provisioned_product_by_id(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)

        resp = client.describe_provisioned_product(Id=self.provisioned_product_id)

        assert resp["ProvisionedProductDetail"]["Id"] == self.provisioned_product_id
        assert resp["ProvisionedProductDetail"]["ProductId"] == self.product_id
        assert (
            resp["ProvisionedProductDetail"]["ProvisioningArtifactId"]
            == self.provisioning_artifact_id
        )

    def test_describe_provisioned_product_by_name(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.describe_provisioned_product(Name="My Provisioned Product")

        assert resp["ProvisionedProductDetail"]["Id"] == self.provisioned_product_id
        assert resp["ProvisionedProductDetail"]["ProductId"] == self.product_id
        assert (
            resp["ProvisionedProductDetail"]["ProvisioningArtifactId"]
            == self.provisioning_artifact_id
        )

    def test_describe_provisioned_product_not_found(self):
        client = boto3.client("servicecatalog", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            client.describe_provisioned_product(Name="does not exist")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Provisioned product not found"

    def test_get_provisioned_product_outputs_by_id(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.get_provisioned_product_outputs(
            ProvisionedProductId=self.provisioned_product_id
        )

        assert len(resp["Outputs"]) == 2
        assert resp["Outputs"][0]["OutputKey"] == "WebsiteURL"

    def test_get_provisioned_product_outputs_by_name(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.get_provisioned_product_outputs(
            ProvisionedProductName="My Provisioned Product"
        )

        assert len(resp["Outputs"]) == 2
        assert resp["Outputs"][0]["OutputKey"] == "WebsiteURL"

    def test_get_provisioned_product_outputs_filtered_by_output_keys(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.get_provisioned_product_outputs(
            ProvisionedProductName="My Provisioned Product", OutputKeys=["BucketArn"]
        )

        assert len(resp["Outputs"]) == 1
        assert resp["Outputs"][0]["OutputKey"] == "BucketArn"

    def test_get_provisioned_product_outputs_missing_required(self):
        client = boto3.client("servicecatalog", region_name="us-east-1")

        with pytest.raises(ClientError) as exc:
            client.get_provisioned_product_outputs()

        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == "ProvisionedProductId and ProvisionedProductName cannot both be null"
        )

    def test_get_provisioned_product_outputs_filtered_by_output_keys_invalid(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        with pytest.raises(ClientError) as exc:
            client.get_provisioned_product_outputs(
                ProvisionedProductId=self.provisioned_product_id,
                OutputKeys=["Not a key"],
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParametersException"
        assert err["Message"] == "Invalid OutputKeys: {'Not a key'}"

    def test_search_provisioned_products(self):
        provisioned_product_2 = _create_provisioned_product(
            region_name=self.region_name,
            product_name="test product",
            provisioning_artifact_id=self.provisioning_artifact_id,
            provisioned_product_name="Second Provisioned Product",
        )
        provisioned_product_id_2 = provisioned_product_2["RecordDetail"][
            "ProvisionedProductId"
        ]

        client = boto3.client("servicecatalog", region_name=self.region_name)

        resp = client.search_provisioned_products()

        pps = resp["ProvisionedProducts"]
        assert len(pps) == 2
        assert pps[0]["Id"] == self.provisioned_product_id
        assert pps[1]["Id"] == provisioned_product_id_2

    def test_search_provisioned_products_filter_by(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.search_provisioned_products(
            Filters={"SearchQuery": ["name:My Provisioned Product"]}
        )

        assert len(resp["ProvisionedProducts"]) == 1
        assert resp["ProvisionedProducts"][0]["Id"] == self.provisioned_product_id

    def test_search_provisioned_products_sort(self):
        # arn , id , name , and lastRecordId
        # sort order -ASCENDING
        # DESCENDING
        provisioned_product_2 = _create_provisioned_product(
            region_name=self.region_name,
            product_name="test product",
            provisioning_artifact_id=self.provisioning_artifact_id,
            provisioned_product_name="A - Second Provisioned Product",
        )
        provisioned_product_2["RecordDetail"]["ProvisionedProductId"]
        client = boto3.client("servicecatalog", region_name=self.region_name)

        # Ascending Search
        resp = client.search_provisioned_products(SortBy="name")

        assert len(resp["ProvisionedProducts"]) == 2
        assert (
            resp["ProvisionedProducts"][0]["Name"] == "A - Second Provisioned Product"
        )
        assert resp["ProvisionedProducts"][1]["Name"] == "My Provisioned Product"

        # Descending Search
        resp = client.search_provisioned_products(SortBy="name", SortOrder="DESCENDING")

        assert len(resp["ProvisionedProducts"]) == 2
        assert resp["ProvisionedProducts"][0]["Name"] == "My Provisioned Product"
        assert (
            resp["ProvisionedProducts"][1]["Name"] == "A - Second Provisioned Product"
        )

    def test_search_provisioned_products_sort_by_invalid_keys(self):
        client = boto3.client("servicecatalog", region_name="eu-west-1")
        with pytest.raises(ClientError) as exc:
            client.search_provisioned_products(
                Filters={"SearchQuery": ["name:My Provisioned Product"]},
                SortBy="not_a_field",
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == "not_a_field is not a supported sort field. It must be ['arn', 'id', 'name', 'lastRecordId']"
        )

    def test_search_provisioned_products_sort_order_invalid_keys(self):
        client = boto3.client("servicecatalog", region_name="eu-west-1")
        with pytest.raises(ClientError) as exc:
            client.search_provisioned_products(
                Filters={"SearchQuery": ["name:My Provisioned Product"]},
                SortOrder="not_a_value",
            )

        err = exc.value.response["Error"]
        assert err["Code"] == "ValidationException"
        assert (
            err["Message"]
            == "1 validation error detected: Value 'not_a_value' at 'sortOrder' failed to "
            "satisfy constraint: Member must satisfy enum value set: ['ASCENDING', "
            "'DESCENDING']"
        )


@mock_servicecatalog
@mock_s3
class TestTerminateProvisionedProduct:
    def test_terminate_provisioned_product(self):
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

        provisioned_product_id = provisioned_product["RecordDetail"][
            "ProvisionedProductId"
        ]
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
class TestSearchProducts:
    def setup_method(self, method):
        self.region_name = "eu-west-1"
        self.product_name = "test product"

        self.constraint, self.portfolio, self.product = _create_product_with_constraint(
            region_name=self.region_name,
            product_name=self.product_name,
            portfolio_name="Test Portfolio",
        )

    def test_search_products(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.search_products()

        products = resp["ProductViewSummaries"]

        assert len(products) == 1
        assert (
            products[0]["Id"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["Id"]
        )
        assert (
            products[0]["ProductId"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
        )

    def test_search_products_by_filter(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.search_products(Filters={"Owner": ["owner arn"]})

        products = resp["ProductViewSummaries"]

        assert len(products) == 1
        assert (
            products[0]["Id"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["Id"]
        )
        assert (
            products[0]["ProductId"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
        )

    def test_search_products_by_filter_fulltext(self):
        """
        Fulltext searches more than a single field
        """
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.search_products(Filters={"FullTextSearch": ["owner arn"]})

        products = resp["ProductViewSummaries"]

        assert len(products) == 1
        assert (
            products[0]["Id"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["Id"]
        )
        assert (
            products[0]["ProductId"]
            == self.product["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
        )

    def test_search_products_with_sort(self):
        _create_product(
            region_name=self.region_name,
            product_name="A - Another Product",
            create_bucket=False,
        )

        client = boto3.client("servicecatalog", region_name=self.region_name)

        resp = client.search_products(SortBy="Title")
        products = resp["ProductViewSummaries"]
        assert len(products) == 2
        assert products[0]["Name"] == "A - Another Product"
        assert products[1]["Name"] == "test product"

        resp = client.search_products(SortBy="Title", SortOrder="DESCENDING")
        products = resp["ProductViewSummaries"]
        assert len(products) == 2
        assert products[0]["Name"] == "test product"
        assert products[1]["Name"] == "A - Another Product"

    # aws servicecatalog search-products --sort-by asdf
    #
    # An error occurred (ValidationException) when calling the SearchProducts operation: 1 validation error detected: Value 'asdf' at 'sortBy' failed to satisfy constraint: Member must satisfy enum value set: [CreationDate, VersionCount, Title]


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
def test_list_provisioning_artifacts_product_not_found():
    client = boto3.client("servicecatalog", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.list_provisioning_artifacts(ProductId="does_not_exist")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Product not found"


@mock_servicecatalog
@mock_s3
class TestDescribeProduct:
    def setup_method(self, method):
        self.region_name = "us-east-2"
        self.product_name = "test product"

        self.constraint, self.portfolio, self.product = _create_product_with_constraint(
            region_name=self.region_name,
            product_name=self.product_name,
            portfolio_name="Test Portfolio",
        )
        self.product_id = self.product["ProductViewDetail"]["ProductViewSummary"][
            "ProductId"
        ]

    def test_describe_product_as_admin_by_id(self):

        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.describe_product_as_admin(Id=self.product_id)

        assert (
            resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
            == self.product_id
        )
        assert len(resp["ProvisioningArtifactSummaries"]) == 1

    def test_describe_product_as_admin_by_name(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.describe_product_as_admin(Name=self.product_name)

        assert (
            resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
            == self.product_id
        )
        assert len(resp["ProvisioningArtifactSummaries"]) == 1

    def test_describe_product_as_admin_with_source_portfolio_id(self):
        assert 1 == 2

    # aws servicecatalog describe-product-as-admin --id prod-4sapxevj5x334 --source-portfolio-id port-bl325ushxntd6
    # I think provisioning artifact will be unique to the portfolio

    def test_describe_product_by_id(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.describe_product_as_admin(Id=self.product_id)

        assert (
            resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
            == self.product_id
        )
        assert len(resp["ProvisioningArtifactSummaries"]) == 1

    def test_describe_product_by_name(self):
        client = boto3.client("servicecatalog", region_name=self.region_name)
        resp = client.describe_product_as_admin(Name=self.product_name)

        assert (
            resp["ProductViewDetail"]["ProductViewSummary"]["ProductId"]
            == self.product_id
        )
        assert len(resp["ProvisioningArtifactSummaries"]) == 1

    def test_describe_product_not_found(self):
        client = boto3.client("servicecatalog", region_name="us-east-1")
        with pytest.raises(ClientError) as exc:
            client.describe_product(Id="does_not_exist")

        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "Product not found"


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
def test_update_portfolio_not_found():
    client = boto3.client("servicecatalog", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.update_portfolio(Id="does_not_exist", DisplayName="new value")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Portfolio not found"


@mock_s3
def test_update_portfolio_invalid_fields():
    assert 1 == 2


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
def test_update_product_not_found():
    client = boto3.client("servicecatalog", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.update_product(Id="does_not_exist", Name="New Product Name")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Product not found"


@mock_servicecatalog
@mock_s3
def test_update_product_invalid_fields():
    assert 1 == 2


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
def test_list_portfolios_for_product_not_found():
    region_name = "us-east-2"
    _create_product_with_portfolio(
        region_name=region_name,
        portfolio_name="My Portfolio",
        product_name="test product",
    )

    client = boto3.client("servicecatalog", region_name=region_name)
    resp = client.list_portfolios_for_product(ProductId="no product")

    assert len(resp["PortfolioDetails"]) == 0


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


@mock_servicecatalog
@mock_s3
def test_describe_record_not_found():
    client = boto3.client("servicecatalog", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.describe_record(Id="does_not_exist")

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Record not found"
