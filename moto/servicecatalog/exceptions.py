"""Exceptions raised by the servicecatalog service."""
from moto.core.exceptions import JsonRESTError
import json


class ServiceCatalogClientError(JsonRESTError):
    code = 400


class ResourceNotFoundException(ServiceCatalogClientError):
    code = 404

    def __init__(self, message: str, resource_id: str, resource_type: str):
        super().__init__(error_type="ResourceNotFoundException", message=message)
        self.description = json.dumps(
            {
                "__type": self.error_type,
                "resourceId": resource_id,
                "message": self.message,
                "resourceType": resource_type,
            }
        )


class ProductNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, product_id: str):
        super().__init__(
            message="Product not found",
            resource_id=product_id,
            resource_type="AWS::ServiceCatalog::Product",
        )


class PortfolioNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, identifier: str, identifier_name: str):
        super().__init__(
            message="Portfolio not found",
            resource_id=f"{identifier_name}={identifier}",
            resource_type="AWS::ServiceCatalog::Portfolio",
        )


class ProvisionedProductNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, identifier: str, identifier_name: str):
        super().__init__(
            message="Provisioned product not found",
            resource_id=f"{identifier_name}={identifier}",
            resource_type="AWS::ServiceCatalog::Product",
        )


class RecordNotFound(ResourceNotFoundException):
    code = 404

    def __init__(self, identifier: str):
        super().__init__(
            message="Record not found",
            resource_id=identifier,
            resource_type="AWS::ServiceCatalog::Record",
        )


class InvalidParametersException(ServiceCatalogClientError):
    code = 400

    def __init__(self, message: str):
        super().__init__(error_type="InvalidParametersException", message=message)


class DuplicateResourceException(ServiceCatalogClientError):
    code = 400

    def __init__(self, message: str):
        super().__init__(error_type="DuplicateResourceException", message=message)
