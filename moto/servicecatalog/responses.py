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
        params = self._get_params()
        accept_language = params.get("AcceptLanguage")
        portfolio_id = params.get("PortfolioId")
        organization_parent_id = params.get("OrganizationParentId")
        page_token = params.get("PageToken")
        page_size = params.get("PageSize")
        account_ids, next_page_token = self.servicecatalog_backend.list_portfolio_access(
            accept_language=accept_language,
            portfolio_id=portfolio_id,
            organization_parent_id=organization_parent_id,
            page_token=page_token,
        )
        # TODO: adjust response
        return json.dumps(dict(accountIds=account_ids, nextPageToken=next_page_token))

    
    def delete_portfolio(self):
        params = self._get_params()
        accept_language = params.get("AcceptLanguage")
        id = params.get("Id")
        self.servicecatalog_backend.delete_portfolio(
            accept_language=accept_language,
            id=id,
        )
        # TODO: adjust response
        return json.dumps(dict())
# add templates from here
    
    def delete_portfolio_share(self):
        params = self._get_params()
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
        # TODO: adjust response
        return json.dumps(dict(portfolioShareToken=portfolio_share_token))
