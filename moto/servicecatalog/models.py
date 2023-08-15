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
from .exceptions import ProductNotFound, PortfolioNotFound, InvalidParametersException


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
        self.portfolio_id = "port-" + "".join(
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

        self.product_ids = list()
        self.launch_path = LaunchPath(name="LP?", backend=backend)

        self.arn = (
            f"arn:aws:servicecatalog:{region}:ACCOUNT_ID:portfolio/{self.portfolio_id}"
        )
        self.tags = tags
        # self.backend.tag_resource(self.arn, tags)

    def link_product(self, product_id: str):
        if product_id not in self.product_ids:
            self.product_ids.append(product_id)

    def has_product(self, product_id: str):
        return product_id in self.product_ids

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
            "Guidance": "DEFAULT",
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
        self.product_view_summary_id = "prodview-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.product_id = "prod-" + "".join(
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
        self.arn = (
            f"arn:aws:servicecatalog:{region}:ACCOUNT_ID:product/{self.product_id}"
        )
        self.tags = tags
        # self.backend.tag_resource(self.arn, tags)

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


class Constraint(BaseModel):
    def __init__(
        self,
        constraint_type: str,
        product_id: str,
        portfolio_id: str,
        backend: "ServiceCatalogBackend",
        parameters: str = "",
        description: str = "",
        owner: str = "",
    ):
        self.constraint_id = "cons-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )

        self.created_time: datetime = unix_time()
        self.updated_time: datetime = self.created_time

        # LAUNCH
        # NOTIFICATION
        # RESOURCE_UPDATE
        # STACKSET
        # TEMPLATE

        self.constraint_type = constraint_type  # "LAUNCH"
        # "Launch as arn:aws:iam::811011756959:role/LaunchRoleBad",
        self.description = description
        self.owner = owner  # account_id = 811011756959
        self.product_id = product_id
        self.portfolio_id = portfolio_id
        self.parameters = parameters

        self.backend = backend

    def to_summary_json(self):
        return {
            "Type": self.constraint_type,
            "Description": self.description,
        }

    def to_create_constraint_json(self):
        return {
            "ConstraintId": self.constraint_id,
            "Type": self.constraint_type,
            "Description": self.description,
            "Owner": self.owner,
            "ProductId": self.product_id,
            "PortfolioId": self.portfolio_id,
        }


class LaunchPath(BaseModel):
    def __init__(self, name: str, backend: "ServiceCatalogBackend"):
        self.path_id = "lpv3-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )

        self.created_time: datetime = unix_time()
        self.updated_time: datetime = self.created_time

        self.name = name

        self.backend = backend

    def to_json(self):
        return {
            "Id": self.path_id,
        }
        #     "LaunchPathSummaries": [
        #         {
        #             "Id": "lpv3-w4u2yosjlxdkw",
        #             "ConstraintSummaries": [
        #                 {
        #                     "Type": "LAUNCH",
        #                     "Description": "Launch as arn:aws:iam::811011756959:role/LaunchRoleBad"
        #                 }
        #             ],
        #             "Tags": [
        #                 {
        #                     "Key": "tag1",
        #                     "Value": "value1"
        #                 },
        #                 {
        #                     "Key": "tag1",
        #                     "Value": "something"
        #                 }
        #             ],
        #             "Name": "First Portfolio"
        #         }
        #     ]
        # self.arn = f"arn:aws:servicecatalog:{self.region}::record/{self.record_id}"
        #   {
        #       "Id": "lpv3-w4u2yosjlxdkw",
        #       "Name": "First Portfolio"
        #   }


class Record(BaseModel):
    def __init__(
        self,
        region: str,
        product_id: str,
        provisioned_product_id: str,
        path_id: str,
        provisioned_product_name: str,
        provisioning_artifact_id: str,
        backend: "ServiceCatalogBackend",
        record_type: str = "PROVISION_PRODUCT",
        provisioned_product_type: str = "CFN_STACK",
        status: str = "CREATED",
    ):
        self.record_id = "rec-" + "".join(
            random.choice(string.ascii_lowercase) for _ in range(12)
        )
        self.region = region

        self.created_time: datetime = unix_time()
        self.updated_time: datetime = self.created_time

        self.product_id = product_id
        self.provisioned_product_id = provisioned_product_id
        self.path_id = path_id

        self.provisioned_product_name = provisioned_product_name
        self.provisioned_product_type = provisioned_product_type
        self.provisioning_artifact_id = provisioning_artifact_id
        self.record_type = record_type
        self.record_errors = list()
        self.record_tags = list()
        self.status = status

        self.backend = backend
        self.arn = f"arn:aws:servicecatalog:{self.region}::record/{self.record_id}"

    def to_record_detail_json(self):
        return {
            "RecordId": self.record_id,
            "CreatedTime": self.created_time,
            "UpdatedTime": self.updated_time,
            "ProvisionedProductId": self.provisioned_product_id,
            "PathId": self.path_id,
            "RecordErrors": self.record_errors,
            "ProductId": self.product_id,
            "RecordType": self.record_type,
            "ProvisionedProductName": self.provisioned_product_name,
            "ProvisioningArtifactId": self.provisioning_artifact_id,
            "RecordTags": self.record_tags,
            "Status": self.status,
            "ProvisionedProductType": self.provisioned_product_type,
        }


class ProvisionedProduct(BaseModel):
    def __init__(
        self,
        region: str,
        accept_language: str,
        name: str,
        stack_id: str,
        stack_outputs,
        product_id: str,
        provisioning_artifact_id: str,
        path_id: str,
        launch_role_arn: str,
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
        self.product_id = product_id
        self.provisioning_artifact_id = provisioning_artifact_id
        self.path_id = path_id
        self.launch_role_arn = launch_role_arn

        # self.records = link to records on actions
        self.last_record_id = None
        self.last_provisioning_record_id = None
        self.last_successful_provisioning_record_id = None

        # CF info
        self.stack_id = stack_id
        self.stack_outputs = stack_outputs
        self.status: str = (
            "SUCCEEDED"  # CREATE,IN_PROGRESS,IN_PROGRESS_IN_ERROR,IN_PROGRESS_IN_ERROR
        )
        self.backend = backend
        self.arn = f"arn:aws:servicecatalog:{region}:ACCOUNT_ID:stack/{self.name}/{self.provisioned_product_id}"
        self.tags = tags
        # self.backend.tag_resource(self.arn, tags)

    def to_provisioned_product_detail_json(self, include_tags=False) -> Dict[str, Any]:
        detail = {
            "Arn": self.arn,
            "CreatedTime": self.created_time,
            "Id": self.provisioned_product_id,
            "IdempotencyToken": "string",
            "LastProvisioningRecordId": self.last_provisioning_record_id,  # ProvisionedProduct, UpdateProvisionedProduct, ExecuteProvisionedProductPlan, TerminateProvisionedProduct
            "LastRecordId": self.last_record_id,
            "LastSuccessfulProvisioningRecordId": self.last_successful_provisioning_record_id,
            "LaunchRoleArn": self.launch_role_arn,
            "Name": self.name,
            "ProductId": self.product_id,
            "ProvisioningArtifactId": self.provisioning_artifact_id,
            "Status": "AVAILABLE",
            "StatusMessage": "string",
            "Type": self.record_type,
        }
        if include_tags:
            detail["Tags"] = self.tags
        return detail


class ServiceCatalogBackend(BaseBackend):
    """Implementation of ServiceCatalog APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

        self.portfolios: Dict[str, Portfolio] = dict()
        self.products: Dict[str, Product] = dict()
        self.provisioned_products: Dict[str, ProvisionedProduct] = dict()
        self.records: OrderedDict[str, Record] = dict()
        self.constraints: Dict[str, Constraint] = dict()

        self.tagger = TaggingService()

    def _get_product(self, identifier: str = "", name: str = "") -> bool:
        if identifier in self.products:
            return self.products[identifier]

        for product_id, product in self.products.items():
            if product.name == name:
                return product

        raise ProductNotFound(product_id=identifier or name)

    def _get_portfolio(self, identifier: str = "", name: str = "") -> bool:
        if identifier in self.portfolios:
            return self.portfolios[identifier]

        for portfolio_id, portfolio in self.portfolios.items():
            if portfolio.display_name == name:
                return portfolio

        raise PortfolioNotFound(
            identifier=identifier or name, identifier_name="Name" if name else "Id"
        )

    def create_portfolio(
        self,
        accept_language,
        display_name,
        description,
        provider_name,
        tags,
        idempotency_token,
    ):
        try:
            self._get_portfolio(name=display_name)
            raise InvalidParametersException(
                message="Portfolio with this name already exists"
            )
        except PortfolioNotFound:
            pass

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
        try:
            self._get_product(name=name)
            raise InvalidParametersException(
                message="Product with this name already exists"
            )
        except ProductNotFound:
            pass

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
            description=provisioning_artifact_parameters.get("Description"),
            artifact_type=provisioning_artifact_parameters.get(
                "Type", "CLOUD_FORMATION_TEMPLATE"
            ),
            info=provisioning_artifact_parameters["Info"],
        )
        self.products[product.product_id] = product

        product_view_detail = product.to_product_view_detail_json()
        provisioning_artifact_detail = (
            provisioning_artifact.to_provisioning_artifact_detail_json()
        )

        return product_view_detail, provisioning_artifact_detail, tags

    def create_constraint(
        self,
        accept_language,
        portfolio_id,
        product_id,
        parameters,
        constraint_type,
        description,
        idempotency_token,
    ):
        # implement here

        constraint = Constraint(
            backend=self,
            product_id=product_id,
            portfolio_id=portfolio_id,
            constraint_type=constraint_type,
            parameters=parameters,
        )
        self.constraints[constraint.constraint_id] = constraint

        constraint_detail = constraint.to_create_constraint_json()
        constraint_parameters = constraint.parameters

        # AVAILABLE | CREATING | FAILED
        status = "AVAILABLE"

        return constraint_detail, constraint_parameters, status

    def associate_product_with_portfolio(
        self, accept_language, product_id, portfolio_id, source_portfolio_id
    ):
        # source_portfolio_id - not implemented yet as copying portfolios not implemented
        product = self._get_product(identifier=product_id)
        portfolio = self._get_portfolio(identifier=portfolio_id)
        portfolio.link_product(product.product_id)

        return

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

        # Get product by id or name
        product = None
        if product_id:
            product = self.products[product_id]
        else:
            for product_id, item in self.products.items():
                if item.name == product_name:
                    product = item

        # Get specified provisioning artifact from product by id or name
        # search product for specific provision_artifact_id or name
        # TODO: ID vs name
        provisioning_artifact = product.get_provisioning_artifact(
            provisioning_artifact_id
        )

        # Verify path exists for product by id or name

        # Create initial stack in CloudFormation
        stack = create_cloudformation_stack_from_template(
            stack_name=provisioned_product_name,
            account_id=self.account_id,
            region_name=self.region_name,
            template=provisioning_artifact.template,
        )

        if tags is None:
            tags = list()

        # Outputs will be a provisioned product and a record
        provisioned_product = ProvisionedProduct(
            accept_language=accept_language,
            region=self.region_name,
            name=provisioned_product_name,
            stack_id=stack.stack_id,
            stack_outputs=stack.stack_outputs,
            product_id=product.product_id,
            provisioning_artifact_id=provisioning_artifact.provisioning_artifact_id,
            path_id="asdf",
            launch_role_arn="asdf2",
            tags=tags,
            backend=self,
        )
        self.provisioned_products[
            provisioned_product.provisioned_product_id
        ] = provisioned_product

        record = Record(
            region=self.region_name,
            backend=self,
            product_id=product.product_id,
            provisioned_product_id=provisioned_product.provisioned_product_id,
            provisioned_product_name=provisioned_product_name,
            path_id="",
            provisioning_artifact_id=provisioning_artifact.provisioning_artifact_id,
        )
        self.records[record.record_id] = record

        provisioned_product.last_record_id = record.record_id
        provisioned_product.last_successful_provisioning_record_id = record.record_id
        provisioned_product.last_provisioning_record_id = record.record_id

        return record.to_record_detail_json()

    def list_portfolios(self, accept_language, page_token):
        # implement here
        portfolio_details = list(self.portfolios.values())
        next_page_token = None
        return portfolio_details, next_page_token

    def get_last_record_for_provisioned_product(self, provisioned_product_id: str):
        for record_key, record in reversed(self.records.items()):
            if record.provisioned_product_id == provisioned_product_id:
                return record
        raise Exception("TODO")

    def describe_provisioned_product(self, accept_language, id, name):
        # implement here

        if id:
            provisioned_product = self.provisioned_products[id]
        else:
            # get by name
            provisioned_product = self.provisioned_products[id]

        # TODO
        #    "CloudWatchDashboards": [
        #       {
        #          "Name": "string"
        #       }
        #    ],

        provisioned_product_detail = (
            provisioned_product.to_provisioned_product_detail_json()
        )

        cloud_watch_dashboards = None
        return provisioned_product_detail, cloud_watch_dashboards

    def search_products(
        self, accept_language, filters, sort_by, sort_order, page_token
    ):
        product_view_summaries = list()
        # TODO: Filter
        for key, product in self.products.items():
            product_view_summaries.append(
                product.to_product_view_detail_json()["ProductViewSummary"]
            )

        product_view_aggregations = {
            "Owner": list(),
            "ProductType": list(),
            "Vendor": list(),
        }
        next_page_token = None
        return product_view_summaries, product_view_aggregations, next_page_token

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
        # TODO: Filter
        provisioned_products = [
            value.to_provisioned_product_detail_json(include_tags=True)
            for key, value in self.provisioned_products.items()
        ]

        total_results_count = len(provisioned_products)
        next_page_token = None
        return provisioned_products, total_results_count, next_page_token

    def list_launch_paths(self, accept_language, product_id, page_token):
        # implement here
        product = self.products[product_id]

        launch_path_summaries = list()

        for portfolio_id, portfolio in self.portfolios.items():
            launch_path_detail = portfolio.launch_path.to_json()
            launch_path_detail["Name"] = portfolio.display_name
            launch_path_detail["ConstraintSummaries"] = list()
            if product.product_id in portfolio.product_ids:
                constraint = self.get_constraint_by(
                    product_id=product.product_id, portfolio_id=portfolio_id
                )
                launch_path_detail["ConstraintSummaries"].append(
                    constraint.to_summary_json()
                )
            launch_path_summaries.append(launch_path_detail)

        next_page_token = None

        return launch_path_summaries, next_page_token

    def list_provisioning_artifacts(self, accept_language, product_id):
        # implement here

        product = self.products[product_id]
        provisioning_artifact_details = list()
        for artifact_id, artifact in product.provisioning_artifacts.items():
            provisioning_artifact_details.append(
                artifact.to_provisioning_artifact_detail_json()
            )

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
        provisioned_product = self.provisioned_products[provisioned_product_id]

        outputs = []

        for output in provisioned_product.stack_outputs:
            outputs.append(
                {
                    "OutputKey": output.key,
                    "OutputValue": output.value,
                    "Description": output.description,
                }
            )

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
        provisioned_product = self.provisioned_products[provisioned_product_id]

        record = Record(
            region=self.region_name,
            backend=self,
            product_id=provisioned_product.product_id,
            provisioned_product_id=provisioned_product.provisioned_product_id,
            provisioned_product_name=provisioned_product.name,
            path_id="",
            provisioning_artifact_id=provisioned_product.provisioning_artifact_id,
            record_type="TERMINATE_PROVISIONED_PRODUCT",
        )

        self.records[record.record_id] = record

        provisioned_product.last_record_id = record.record_id
        provisioned_product.last_successful_provisioning_record_id = record.record_id
        provisioned_product.last_provisioning_record_id = record.record_id

        record_detail = record.to_record_detail_json()

        return record_detail

    def get_tags(self, resource_id: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_id)

    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        tags_input = TaggingService.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags_input)

    def get_constraint_by(self, product_id: str, portfolio_id: str):
        for constraint_id, constraint in self.constraints.items():
            if (
                constraint.product_id == product_id
                and constraint.portfolio_id == portfolio_id
            ):
                return constraint

    def describe_portfolio(self, accept_language, identifier):
        portfolio = self._get_portfolio(identifier=identifier)
        portfolio_detail = portfolio.to_json()

        tags = []
        tag_options = None
        budgets = None
        return portfolio_detail, tags, tag_options, budgets

    def describe_product_as_admin(
        self, accept_language, identifier, name, source_portfolio_id
    ):
        # implement here
        product = self._get_product(identifier=identifier, name=name)
        product_view_detail = product.to_product_view_detail_json()

        provisioning_artifact_summaries = []
        for key, summary in product.provisioning_artifacts.items():
            provisioning_artifact_summaries.append(
                summary.to_provisioning_artifact_detail_json()
            )
        tags = []
        tag_options = None
        budgets = None

        return (
            product_view_detail,
            provisioning_artifact_summaries,
            tags,
            tag_options,
            budgets,
        )

    def describe_product(self, accept_language, identifier, name):

        (
            product_view_summary,
            provisioning_artifacts,
            _,
            _,
            budgets,
        ) = self.describe_product_as_admin(accept_language, identifier, name)
        launch_paths = []
        return product_view_summary, provisioning_artifacts, budgets, launch_paths

    def update_portfolio(
        self,
        accept_language,
        identifier,
        display_name,
        description,
        provider_name,
        add_tags,
        remove_tags,
    ):
        portfolio = self._get_portfolio(identifier=identifier)

        portfolio.display_name = display_name
        portfolio.description = description
        portfolio.provider_name = provider_name

        # tags

        portfolio_detail = portfolio.to_json()
        tags = []

        return portfolio_detail, tags

    def update_product(
        self,
        accept_language,
        identifier,
        name,
        owner,
        description,
        distributor,
        support_description,
        support_email,
        support_url,
        add_tags,
        remove_tags,
        source_connection,
    ):
        # implement here
        product_view_detail = {}
        tags = []
        return product_view_detail, tags

    def list_portfolios_for_product(self, accept_language, product_id, page_token):
        portfolio_details = []
        for portfolio_id, portfolio in self.portfolios.items():
            if product_id in portfolio.product_ids:
                portfolio_details.append(portfolio.to_json())

        next_page_token = None

        return portfolio_details, next_page_token


servicecatalog_backends = BackendDict(ServiceCatalogBackend, "servicecatalog")
