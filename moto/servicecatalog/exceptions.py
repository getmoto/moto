"""Exceptions raised by the servicecatalog service."""
from moto.core.exceptions import JsonRESTError
import json


class ServiceCatalogClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(ServiceCatalogClientError):
    code = 404

    def __init__(self, message: str, resource_id: str, resource_type: str):
        super().__init__("ResourceNotFoundException", message)
        self.description = json.dumps(
            {
                "resourceId": resource_id,
                "message": self.message,
                "resourceType": resource_type,
            }
        )


class ProductNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, product_id: str):
        super().__init__(
            "Product not found",
            resource_id=product_id,
            resource_type="AWS::ServiceCatalog::Product",
        )


class PortfolioNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, identifier: str, identifier_name: str):
        super().__init__(
            "Portfolio not found",
            resource_id=f"{identifier_name}={identifier}",
            resource_type="AWS::ServiceCatalog::Portfolio",
        )


class InvalidParametersException(ServiceCatalogClientError):
    code = 400

    def __init__(self, message: str):
        super().__init__("InvalidParametersException", message)
