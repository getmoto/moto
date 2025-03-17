"""ServiceCatalogBackend class with methods for supported APIs."""

import uuid
from datetime import datetime

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.paginator import paginate
from moto.utilities.utils import get_partition

PAGINATION_MODEL = {
    "list_portfolio_access": {
        "input_token": "page_token",
        "limit_key": "page_size",
        "limit_default": 20,
        "unique_attribute": "account_id",
    },
    "list_portfolios": {
        "input_token": "page_token",
        "limit_key": "page_size",
        "limit_default": 20,
        "unique_attribute": "id",
    },
}


class Portfolio(BaseModel):
    """Portfolio resource."""

    def __init__(
        self,
        portfolio_id,
        display_name,
        description,
        provider_name,
        tags,
        region_name,
        account_id,
    ):
        self.id = portfolio_id
        self.display_name = display_name
        self.description = description
        self.provider_name = provider_name
        self.created_time = datetime.now()
        self.tags = tags
        self.region_name = region_name
        self.account_id = account_id

    @property
    def arn(self):
        return f"arn:{get_partition(self.region_name)}:catalog:{self.region_name}:{self.account_id}:portfolio/{self.id}"

    def to_dict(self):
        return {
            "Id": self.id,
            "ARN": self.arn,
            "DisplayName": self.display_name,
            "Description": self.description,
            "CreatedTime": self.created_time.isoformat(),
            "ProviderName": self.provider_name,
        }


class ServiceCatalogBackend(BaseBackend):
    """Implementation of ServiceCatalog APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.portfolio_access = {}
        self.portfolios = {}
        self.idempotency_tokens = {}

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_portfolio_access(
        self,
        accept_language,
        portfolio_id,
        organization_parent_id,
        page_token,
        page_size=None,
    ):
        account_ids = self.portfolio_access.get(portfolio_id, [])
        return [{"account_id": account_id} for account_id in account_ids]

    def delete_portfolio(self, accept_language, id):
        # Remove any portfolio access entries for this portfolio
        if id in self.portfolio_access:
            del self.portfolio_access[id]

        # Remove the portfolio if it exists
        if id in self.portfolios:
            del self.portfolios[id]

        return None

    def delete_portfolio_share(
        self, accept_language, portfolio_id, account_id, organization_node
    ):
        # If we have an account_id, remove it from the portfolio's access list
        if account_id and portfolio_id in self.portfolio_access:
            if account_id in self.portfolio_access[portfolio_id]:
                self.portfolio_access[portfolio_id].remove(account_id)

        # If we have an organization_node, generate a portfolio share token
        portfolio_share_token = None
        if organization_node:
            portfolio_share_token = f"share-{portfolio_id}-{organization_node.get('Type', '')}-{organization_node.get('Value', '')}"

        return portfolio_share_token

    def create_portfolio(
        self,
        accept_language,
        display_name,
        description,
        provider_name,
        tags,
        idempotency_token,
    ):
        if idempotency_token and idempotency_token in self.idempotency_tokens:
            portfolio_id = self.idempotency_tokens[idempotency_token]
            portfolio = self.portfolios[portfolio_id]
            return portfolio.to_dict(), portfolio.tags

        portfolio_id = str(uuid.uuid4())

        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            display_name=display_name,
            description=description or "",
            provider_name=provider_name,
            tags=tags or [],
            region_name=self.region_name,
            account_id=self.account_id,
        )

        self.portfolios[portfolio_id] = portfolio

        if idempotency_token:
            self.idempotency_tokens[idempotency_token] = portfolio_id

        self.portfolio_access[portfolio_id] = []

        return portfolio.to_dict(), portfolio.tags

    def create_portfolio_share(
        self,
        accept_language,
        portfolio_id,
        account_id,
        organization_node,
        share_tag_options,
        share_principals,
    ):
        if portfolio_id not in self.portfolios:
            return None

        # If we have an account_id, add it to the portfolio's access list
        if account_id:
            if portfolio_id not in self.portfolio_access:
                self.portfolio_access[portfolio_id] = []

            if account_id not in self.portfolio_access[portfolio_id]:
                self.portfolio_access[portfolio_id].append(account_id)

            return None

        # If we have an organization_node, generate a portfolio share token
        portfolio_share_token = None
        if organization_node:
            org_type = organization_node.get("Type", "")
            org_value = organization_node.get("Value", "")
            portfolio_share_token = f"share-{portfolio_id}-{org_type}-{org_value}"

            if share_tag_options:
                portfolio_share_token += "-tags"
            if share_principals:
                portfolio_share_token += "-principals"

        return portfolio_share_token

    def list_portfolios(self, accept_language=None, page_token=None, page_size=None):
        # TODO: Implement proper pagination for this method
        portfolio_details = [
            portfolio.to_dict() for portfolio in self.portfolios.values()
        ]
        return portfolio_details, None


servicecatalog_backends = BackendDict(ServiceCatalogBackend, "servicecatalog")
