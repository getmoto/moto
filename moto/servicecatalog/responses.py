"""Handles incoming servicecatalog requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import servicecatalog_backends


class ServiceCatalogResponse(BaseResponse):
    """Handler for ServiceCatalog requests and responses."""

    def __init__(self):
        super().__init__(service_name="servicecatalog")

    @property
    def servicecatalog_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # servicecatalog_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return servicecatalog_backends[self.current_account][self.region]

    # add methods from here

    def list_portfolio_access(self):
        params = json.loads(self.body)
        accept_language = params.get("AcceptLanguage")
        portfolio_id = params.get("PortfolioId")
        organization_parent_id = params.get("OrganizationParentId")
        page_token = params.get("PageToken")
        page_size = params.get("PageSize")

        account_id_objects, next_page_token = (
            self.servicecatalog_backend.list_portfolio_access(
                accept_language=accept_language,
                portfolio_id=portfolio_id,
                organization_parent_id=organization_parent_id,
                page_token=page_token,
                page_size=page_size,
            )
        )

        # Extract account_ids from the objects returned by the paginator
        account_ids = [obj["account_id"] for obj in account_id_objects]

        return json.dumps({"AccountIds": account_ids, "NextPageToken": next_page_token})

    def delete_portfolio(self):
        params = json.loads(self.body)
        accept_language = params.get("AcceptLanguage")
        id = params.get("Id")

        self.servicecatalog_backend.delete_portfolio(
            accept_language=accept_language,
            id=id,
        )

        # Return an empty JSON object as per the API specification
        return json.dumps({})

    # add templates from here

    def delete_portfolio_share(self):
        params = json.loads(self.body)
        accept_language = params.get("AcceptLanguage")
        portfolio_id = params.get("PortfolioId")
        account_id = params.get("AccountId")
        organization_node = params.get("OrganizationNode")

        portfolio_share_token = self.servicecatalog_backend.delete_portfolio_share(
            accept_language=accept_language,
            portfolio_id=portfolio_id,
            account_id=account_id,
            organization_node=organization_node,
        )

        response = {}
        if portfolio_share_token:
            response["PortfolioShareToken"] = portfolio_share_token

        return json.dumps(response)

    def create_portfolio(self):
        params = json.loads(self.body)

        accept_language = params.get("AcceptLanguage")
        display_name = params.get("DisplayName")
        description = params.get("Description")
        provider_name = params.get("ProviderName")
        tags = params.get("Tags")
        idempotency_token = params.get("IdempotencyToken")

        portfolio_detail, tags = self.servicecatalog_backend.create_portfolio(
            accept_language=accept_language,
            display_name=display_name,
            description=description,
            provider_name=provider_name,
            tags=tags,
            idempotency_token=idempotency_token,
        )

        return json.dumps({"PortfolioDetail": portfolio_detail, "Tags": tags})

    def create_portfolio_share(self):
        params = json.loads(self.body)
        accept_language = params.get("AcceptLanguage")
        portfolio_id = params.get("PortfolioId")
        account_id = params.get("AccountId")
        organization_node = params.get("OrganizationNode")
        share_tag_options = params.get("ShareTagOptions", False)
        share_principals = params.get("SharePrincipals", False)

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

        return json.dumps(response)

    def list_portfolios(self):
        params = self._get_params()
        accept_language = params.get("AcceptLanguage")
        page_token = params.get("PageToken")
        page_size = params.get("PageSize")

        portfolio_details, next_page_token = (
            self.servicecatalog_backend.list_portfolios(
                accept_language=accept_language,
                page_token=page_token,
                page_size=page_size,
            )
        )

        response = {
            "PortfolioDetails": portfolio_details,
            "NextPageToken": next_page_token,
        }
        return json.dumps(response)
