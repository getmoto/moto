"""Handles incoming servicecatalog requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import ServiceCatalogBackend, servicecatalog_backends


class ServiceCatalogResponse(BaseResponse):
    """Handler for ServiceCatalog requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="servicecatalog")
        self.automated_parameter_parsing = True

    @property
    def servicecatalog_backend(self) -> ServiceCatalogBackend:
        """Return backend instance specific for this region."""
        # TODO
        # servicecatalog_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return servicecatalog_backends[self.current_account][self.region]

    def list_portfolio_access(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        portfolio_id = self._get_param("PortfolioId")
        organization_parent_id = self._get_param("OrganizationParentId")
        page_token = self._get_param("PageToken")
        page_size = self._get_param("PageSize")

        account_id_objects, next_page_token = (
            self.servicecatalog_backend.list_portfolio_access(
                accept_language=accept_language,
                portfolio_id=portfolio_id,
                organization_parent_id=organization_parent_id,
                page_token=page_token,
                page_size=page_size,
            )
        )

        account_ids = [obj["account_id"] for obj in account_id_objects]

        return ActionResult(
            {"AccountIds": account_ids, "NextPageToken": next_page_token}
        )

    def delete_portfolio(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        id = self._get_param("Id")

        self.servicecatalog_backend.delete_portfolio(
            accept_language=accept_language,
            id=id,
        )

        return EmptyResult()

    def delete_portfolio_share(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        portfolio_id = self._get_param("PortfolioId")
        account_id = self._get_param("AccountId")
        organization_node = self._get_param("OrganizationNode")

        portfolio_share_token = self.servicecatalog_backend.delete_portfolio_share(
            accept_language=accept_language,
            portfolio_id=portfolio_id,
            account_id=account_id,
            organization_node=organization_node,
        )

        response = {}
        if portfolio_share_token:
            response["PortfolioShareToken"] = portfolio_share_token

        return ActionResult(response)

    def create_portfolio(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        display_name = self._get_param("DisplayName")
        description = self._get_param("Description")
        provider_name = self._get_param("ProviderName")
        tags = self._get_param("Tags")
        idempotency_token = self._get_param("IdempotencyToken")

        portfolio = self.servicecatalog_backend.create_portfolio(
            accept_language=accept_language,
            display_name=display_name,
            description=description,
            provider_name=provider_name,
            tags=tags,
            idempotency_token=idempotency_token,
        )

        return ActionResult({"PortfolioDetail": portfolio, "Tags": portfolio.tags})

    def create_portfolio_share(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        portfolio_id = self._get_param("PortfolioId")
        account_id = self._get_param("AccountId")
        organization_node = self._get_param("OrganizationNode")
        share_tag_options = self._get_bool_param("ShareTagOptions", False)
        share_principals = self._get_bool_param("SharePrincipals", False)

        portfolio_share_token = self.servicecatalog_backend.create_portfolio_share(
            accept_language=accept_language,
            portfolio_id=portfolio_id,
            account_id=account_id,
            organization_node=organization_node,
            share_tag_options=share_tag_options,
            share_principals=share_principals,
        )

        response = {}
        if portfolio_share_token:
            response["PortfolioShareToken"] = portfolio_share_token

        return ActionResult(response)

    def list_portfolios(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        page_token = self._get_param("PageToken")
        page_size = self._get_param("PageSize")

        portfolios, next_page_token = self.servicecatalog_backend.list_portfolios(
            accept_language=accept_language,
            page_token=page_token,
            page_size=page_size,
        )

        response = {
            "PortfolioDetails": portfolios,
            "NextPageToken": next_page_token,
        }
        return ActionResult(response)

    def describe_portfolio_shares(self) -> ActionResult:
        portfolio_id = self._get_param("PortfolioId")
        type = self._get_param("Type")
        page_token = self._get_param("PageToken")
        page_size = self._get_param("PageSize")

        next_page_token, portfolio_share_details = (
            self.servicecatalog_backend.describe_portfolio_shares(
                portfolio_id=portfolio_id,
                type=type,
                page_token=page_token,
                page_size=page_size,
            )
        )

        response = {
            "NextPageToken": next_page_token,
            "PortfolioShareDetails": portfolio_share_details,
        }

        return ActionResult(response)

    def describe_portfolio(self) -> ActionResult:
        """Handle describe_portfolio request."""
        accept_language = self._get_param("AcceptLanguage")
        id = self._get_param("Id")

        portfolio, tags, tag_options, budgets = (
            self.servicecatalog_backend.describe_portfolio(
                accept_language=accept_language,
                id=id,
            )
        )

        response: dict[str, Any] = {
            "PortfolioDetail": portfolio or {},
            "Tags": tags,
            "TagOptions": tag_options,
            "Budgets": budgets,
        }

        return ActionResult(response)

    def create_product(self) -> ActionResult:
        name = self._get_param("Name")
        owner = self._get_param("Owner")
        description = self._get_param("Description")
        distributor = self._get_param("Distributor")
        support_description = self._get_param("SupportDescription")
        support_email = self._get_param("SupportEmail")
        support_url = self._get_param("SupportUrl")
        product_type = self._get_param("ProductType")
        tags = self._get_param("Tags")
        provisioning_artifact_parameters = self._get_param(
            "ProvisioningArtifactParameters"
        )
        idempotency_token = self._get_param("IdempotencyToken")
        source_connection = self._get_param("SourceConnection")
        accept_language = self._get_param("AcceptLanguage")

        product = self.servicecatalog_backend.create_product(
            name=name,
            owner=owner,
            description=description,
            distributor=distributor,
            support_description=support_description,
            support_email=support_email,
            support_url=support_url,
            product_type=product_type,
            tags=tags,
            provisioning_artifact_parameters=provisioning_artifact_parameters,
            idempotency_token=idempotency_token,
            source_connection=source_connection,
            accept_language=accept_language,
        )

        product_view = {
            "ProductViewSummary": {
                "Id": product.id,
                "ProductId": product.id,
                "Name": product.name,
                "Owner": product.owner,
                "ShortDescription": product.description,
                "Type": product.product_type,
                "Distributor": product.distributor,
                "HasDefaultPath": False,
                "SupportEmail": product.support_email,
                "SupportDescription": product.support_description,
                "SupportUrl": product.support_url,
            },
            "Status": "AVAILABLE",
            "ProductARN": product.arn,
            "CreatedTime": product.created_time,
            "SourceConnection": product.source_connection,
        }

        return ActionResult(
            {
                "ProductViewDetail": product_view,
                "ProvisioningArtifactDetail": {},
                "Tags": product.tags,
            }
        )

    def describe_product(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        id = self._get_param("Id")
        name = self._get_param("Name")

        product = self.servicecatalog_backend.describe_product(
            accept_language=accept_language, id=id, name=name
        )

        result = {
            "ProductViewSummary": {
                "Id": product.id,
                "ProductId": product.id,
                "Name": product.name,
                "Owner": product.owner,
                "ShortDescription": product.description,
                "Type": product.product_type,
                "Distributor": product.distributor,
                "HasDefaultPath": False,
                "SupportEmail": product.support_email,
                "SupportDescription": product.support_description,
                "SupportUrl": product.support_url,
            },
            "ProvisioningArtifacts": [],
            "Budgets": [],
            "LaunchPaths": [],
        }

        return ActionResult(result)

    def delete_product(self) -> ActionResult:
        accept_language = self._get_param("AcceptLanguage")
        id = self._get_param("Id")

        self.servicecatalog_backend.delete_product(
            accept_language=accept_language,
            id=id,
        )

        return EmptyResult()
