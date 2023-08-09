"""ServiceCatalogBackend class with methods for supported APIs."""
import string
from typing import Any, Dict, OrderedDict, List, Optional, Union
from datetime import datetime

from moto.core import BaseBackend, BackendDict, BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random as random
from moto.utilities.tagging_service import TaggingService
from moto.cloudformation.utils import get_stack_from_s3_url

from .utils import create_cloudformation_stack_from_template


class Portfolio(BaseModel):
    def __init__(
        self,
        region: str,
        accept_language: str,
        display_name: str,
        description: str,
        provider_name: str,
        tags: Dict[str, str],
        idempotency_token: str,
        backend: "ServiceCatalogBackend",
    ):
        self.portfolio_id = "p" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.created_date: datetime = unix_time()
        self.region = region
        self.accept_language = accept_language
        self.display_name = display_name
        self.description = description
        self.provider_name = provider_name
        self.idempotency_token = idempotency_token
        self.backend = backend

        self.arn = f"arn:aws:servicecatalog:{region}::{self.portfolio_id}"
        self.tags = tags
        self.backend.tag_resource(self.arn, tags)

    def to_json(self) -> Dict[str, Any]:
        met = {
            "ARN": self.arn,
            "CreatedTime": self.created_date,
            "Description": self.description,
            "DisplayName": self.display_name,
            "Id": self.portfolio_id,
            "ProviderName": self.provider_name,
        }
        return met


class ProvisioningArtifact(BaseModel):
    def __init__(
        self,
        region: str,
        active: bool,
        name: str,
        artifact_type: str = "CLOUD_FORMATION_TEMPLATE",
        description: str = "",
        source_revision: str = "",
        guidance: str = "DEFAULT",
        template: str = "",
    ):
        self.provisioning_artifact_id = "pa-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )  # Id
        self.region: str = region  # RegionName

        self.active: bool = active  # Active
        self.created_date: datetime = unix_time()  # CreatedTime
        self.description = description  # Description - 8192
        self.guidance = guidance  # DEFAULT | DEPRECATED
        self.name = name  # 8192
        self.source_revision = source_revision  # 512
        self.artifact_type = artifact_type  # CLOUD_FORMATION_TEMPLATE | MARKETPLACE_AMI | MARKETPLACE_CAR | TERRAFORM_OPEN_SOURCE
        self.template = template

    def to_provisioning_artifact_detail_json(self) -> Dict[str, Any]:
        return {
            "CreatedTime": self.created_date,
            "Active": self.active,
            "Id": self.provisioning_artifact_id,
            "Description": self.description,
            "Name": self.name,
            "Type": self.artifact_type,
        }


class Product(BaseModel):
    def __init__(
        self,
        region: str,
        accept_language: str,
        name: str,
        description: str,
        owner: str,
        product_type: str,
        tags: Dict[str, str],
        backend: "ServiceCatalogBackend",
    ):
        self.product_view_summary_id = "prodview" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.product_id = "prod" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.created_time: datetime = unix_time()
        self.region = region
        self.accept_language = accept_language
        self.name = name
        self.description = description
        self.owner = owner
        self.product_type = product_type

        self.provisioning_artifacts: OrderedDict[str, "ProvisioningArtifact"] = dict()

        self.backend = backend
        self.arn = f"arn:aws:servicecatalog:{region}::product/{self.product_id}"
        self.tags = tags
        self.backend.tag_resource(self.arn, tags)

    def get_provisioning_artifact(self, artifact_id: str):
        return self.provisioning_artifacts[artifact_id]

    def _create_provisioning_artifact(
        self,
        account_id,
        name,
        description,
        artifact_type,
        info,
        disable_template_validation: bool = False,
    ):

        # Load CloudFormation template from S3
        if "LoadTemplateFromURL" in info:
            template_url = info["LoadTemplateFromURL"]
            template = get_stack_from_s3_url(
                template_url=template_url, account_id=account_id
            )
        else:
            raise NotImplementedError("Nope")
        # elif "ImportFromPhysicalId" in info:

        provisioning_artifact = ProvisioningArtifact(
            name=name,
            description=description,
            artifact_type=artifact_type,
            region=self.region,
            active=True,
            template=template,
        )
        self.provisioning_artifacts[
            provisioning_artifact.provisioning_artifact_id
        ] = provisioning_artifact

        return provisioning_artifact

    def to_product_view_detail_json(self) -> Dict[str, Any]:
        return {
            "ProductARN": self.arn,
            "CreatedTime": self.created_time,
            "ProductViewSummary": {
                "Id": self.product_view_summary_id,
                "ProductId": self.product_id,
                "Name": self.name,
                "Owner": self.owner,
                "ShortDescription": self.description,
                "Type": self.product_type,
                # "Distributor": "Some person",
                # "HasDefaultPath": false,
                # "SupportEmail": "frank@stallone.example"
            },
            "Status": "AVAILABLE",
        }

    def to_json(self) -> Dict[str, Any]:
        return self.to_product_view_detail_json()


class Record(BaseModel):
    def __init__(
        self,
        region: str,
        backend: "ServiceCatalogBackend",
    ):
        self.record_id = "rec-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.region = region

        self.created_time: datetime = unix_time()
        self.updated_time: datetime = self.created_time

        self.backend = backend
        self.arn = f"arn:aws:servicecatalog:{self.region}::record/{self.record_id}"


class ProvisionedProduct(BaseModel):
    def __init__(
        self,
        region: str,
        accept_language: str,
        name: str,
        stack_id: str,
        tags: Dict[str, str],
        backend: "ServiceCatalogBackend",
    ):
        self.provisioned_product_id = "pp-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.created_time: datetime = unix_time()
        self.updated_time: datetime = self.created_time
        self.region = region
        self.accept_language = accept_language

        self.name = name
        # CFN_STACK, CFN_STACKSET, TERRAFORM_OPEN_SOURCE, TERRAFORM_CLOUD
        # self.product_type = product_type
        # PROVISION_PRODUCT, UPDATE_PROVISIONED_PRODUCT, TERMINATE_PROVISIONED_PRODUCT
        self.record_type = "PROVISION_PRODUCT"
        self.product_id = ""
        self.provisioning_artifcat_id = ""
        self.path_id = ""
        self.launch_role_arn = ""

        # self.records = link to records on actions
        self.status: str = (
            "SUCCEEDED"  # CREATE,IN_PROGRESS,IN_PROGRESS_IN_ERROR,IN_PROGRESS_IN_ERROR
        )
        self.backend = backend
        self.arn = (
            f"arn:aws:servicecatalog:{region}::provisioned_product/{self.product_id}"
        )
        self.tags = tags
        self.backend.tag_resource(self.arn, tags)

    def to_provisioned_product_detail_json(self) -> Dict[str, Any]:
        return {
            "Arn": self.arn,
            "CreatedTime": self.created_date,
            "Id": self.product_id,
            "IdempotencyToken": "string",
            "LastProvisioningRecordId": "string",  # ProvisionedProduct, UpdateProvisionedProduct, ExecuteProvisionedProductPlan, TerminateProvisionedProduct
            "LastRecordId": "string",
            "LastSuccessfulProvisioningRecordId": "string",
            "LaunchRoleArn": "string",
            "Name": self.name,
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "Status": "AVAILABLE",
            "StatusMessage": "string",
            "Type": "string",
        }


class ServiceCatalogBackend(BaseBackend):
    """Implementation of ServiceCatalog APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

        self.portfolios: Dict[str, Portfolio] = dict()
        self.products: Dict[str, Product] = dict()
        self.provisioned_products: Dict[str, ProvisionedProduct] = dict()

        self.tagger = TaggingService()

    def create_portfolio(
        self,
        accept_language,
        display_name,
        description,
        provider_name,
        tags,
        idempotency_token,
    ):
        portfolio = Portfolio(
            region=self.region_name,
            accept_language=accept_language,
            display_name=display_name,
            description=description,
            provider_name=provider_name,
            tags=tags,
            idempotency_token=idempotency_token,
            backend=self,
        )
        self.portfolios[portfolio.portfolio_id] = portfolio
        return portfolio, tags

    def list_portfolios(self, accept_language, page_token):
        # implement here
        portfolio_details = list(self.portfolios.values())
        next_page_token = None
        return portfolio_details, next_page_token

    def create_product(
        self,
        accept_language,
        name,
        owner,
        description,
        distributor,
        support_description,
        support_email,
        support_url,
        product_type,
        tags,
        provisioning_artifact_parameters,
        idempotency_token,
        source_connection,
    ):
        # implement here

        product = Product(
            region=self.region_name,
            accept_language=accept_language,
            owner=owner,
            product_type=product_type,
            name=name,
            description=description,
            tags=tags,
            backend=self,
        )

        provisioning_artifact = product._create_provisioning_artifact(
            account_id=self.account_id,
            name=provisioning_artifact_parameters["Name"],
            description=provisioning_artifact_parameters["Description"],
            artifact_type=provisioning_artifact_parameters["Type"],
            info=provisioning_artifact_parameters["Info"],
        )
        self.products[product.product_id] = product

        product_view_detail = product.to_product_view_detail_json()
        provisioning_artifact_detail = (
            provisioning_artifact.to_provisioning_artifact_detail_json()
        )

        return product_view_detail, provisioning_artifact_detail, tags

    def describe_provisioned_product(self, accept_language, id, name):
        # implement here

        if id:
            product = self.products[id]
        else:
            # get by name
            product = self.products[id]

        # TODO
        #    "CloudWatchDashboards": [
        #       {
        #          "Name": "string"
        #       }
        #    ],
        provisioned_product_detail = product.to_provisioned_product_detail_json()
        cloud_watch_dashboards = None
        return provisioned_product_detail, cloud_watch_dashboards

    def search_products(
        self, accept_language, filters, sort_by, sort_order, page_token
    ):
        # implement here
        product_view_summaries = {}
        product_view_aggregations = {}
        next_page_token = {}
        return product_view_summaries, product_view_aggregations, next_page_token

    def provision_product(
        self,
        accept_language,
        product_id,
        product_name,
        provisioning_artifact_id,
        provisioning_artifact_name,
        path_id,
        path_name,
        provisioned_product_name,
        provisioning_parameters,
        provisioning_preferences,
        tags,
        notification_arns,
        provision_token,
    ):
        # implement here
        # TODO: Big damn cleanup before this counts as anything useful.
        product = None
        for product_id, item in self.products.items():
            if item.name == product_name:
                product = item

        # search product for specific provision_artifact_id or name
        # TODO: ID vs name
        provisioning_artifact = product.get_provisioning_artifact(
            provisioning_artifact_id
        )

        # path

        # Instantiate stack
        stack = create_cloudformation_stack_from_template(
            stack_name=provisioned_product_name,
            account_id=self.account_id,
            region_name=self.region_name,
            template=provisioning_artifact.template,
        )

        provisioned_product = ProvisionedProduct(
            accept_language=accept_language,
            region=self.region_name,
            name=provisioned_product_name,
            stack_id=stack.stack_id,
            tags=[],
            backend=self,
        )
        record = Record(region=self.region_name, backend=self)

        # record object

        record_detail = {
            "RecordId": record.record_id,
            "CreatedTime": record.created_time,
            "UpdatedTime": record.updated_time,
            "ProvisionedProductId": provisioned_product.provisioned_product_id,
            #     "PathId": "lpv2-abcdg3jp6t5k6",
            #     "RecordErrors": [],
            "ProductId": provisioned_product.product_id,
            #     "RecordType": "PROVISION_PRODUCT",
            #     "ProvisionedProductName": "mytestppname3",
            #     "ProvisioningArtifactId": "pa-pcz347abcdcfm",
            #     "RecordTags": [],
            #     "Status": "CREATED",
            #     "ProvisionedProductType": "CFN_STACK"
        }
        print(record_detail)
        return record_detail

    def search_provisioned_products(
        self,
        accept_language,
        access_level_filter,
        filters,
        sort_by,
        sort_order,
        page_token,
    ):
        # implement here
        provisioned_products = {}
        total_results_count = 0
        next_page_token = None
        return provisioned_products, total_results_count, next_page_token

    def list_launch_paths(self, accept_language, product_id, page_token):
        # implement here
        launch_path_summaries = {}
        next_page_token = None

        return launch_path_summaries, next_page_token

    def list_provisioning_artifacts(self, accept_language, product_id):
        # implement here
        provisioning_artifact_details = {}
        next_page_token = None

        return provisioning_artifact_details, next_page_token

    def get_provisioned_product_outputs(
        self,
        accept_language,
        provisioned_product_id,
        provisioned_product_name,
        output_keys,
        page_token,
    ):
        # implement here
        outputs = {}
        next_page_token = None
        return outputs, next_page_token

    def terminate_provisioned_product(
        self,
        provisioned_product_name,
        provisioned_product_id,
        terminate_token,
        ignore_errors,
        accept_language,
        retain_physical_resources,
    ):
        # implement here
        record_detail = {}
        return record_detail

    def get_tags(self, resource_id: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_id)

    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        tags_input = TaggingService.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags_input)

    def associate_product_with_portfolio(
        self, accept_language, product_id, portfolio_id, source_portfolio_id
    ):
        # implement here
        return


servicecatalog_backends = BackendDict(ServiceCatalogBackend, "servicecatalog")
