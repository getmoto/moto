"""ServiceCatalogBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class ServiceCatalogBackend(BaseBackend):
    """Implementation of ServiceCatalog APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def list_portfolio_access(self, accept_language, portfolio_id, organization_parent_id, page_token):
        # implement here
        return account_ids, next_page_token
    
    def delete_portfolio(self, accept_language, id):
        # implement here
        return 
    
    def delete_portfolio_share(self, accept_language, portfolio_id, account_id, organization_node):
        # implement here
        return portfolio_share_token
    

servicecatalog_backends = BackendDict(ServiceCatalogBackend, "servicecatalog")
