"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_api_gateway import APIGatewayClient, APIGatewayConfig
    from aws_sdk_api_gateway.models import NotFoundException
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-api-gateway is not installed", allow_module_level=True)


@mock_aws
def test_publish_mock_rest_api():
    """Build a REST API with a mocked GET /orders endpoint and deploy it to a stage."""
    config = APIGatewayConfig.resolve(region="us-east-1")

    with APIGatewayClient(config=config) as client:
        api = client.create_rest_api(
            name=f"orders-api-{uuid4()}",
            description="Order management",
            endpoint_configuration={"types": ["REGIONAL"]},
            tags={"team": "orders"},
        )
        assert api.root_resource_id

        orders = client.create_resource(
            rest_api_id=api.id, parent_id=api.root_resource_id, path_part="orders"
        )
        assert orders.path == "/orders"

        client.put_method(
            rest_api_id=api.id,
            resource_id=orders.id,
            http_method="GET",
            authorization_type="NONE",
        )
        client.put_method_response(
            rest_api_id=api.id,
            resource_id=orders.id,
            http_method="GET",
            status_code="200",
        )
        integration = client.put_integration(
            rest_api_id=api.id,
            resource_id=orders.id,
            http_method="GET",
            type="MOCK",
            request_templates={"application/json": '{"statusCode": 200}'},
        )
        assert integration.type == "MOCK"
        client.put_integration_response(
            rest_api_id=api.id,
            resource_id=orders.id,
            http_method="GET",
            status_code="200",
            response_templates={"application/json": '{"orders": []}'},
        )

        resources = client.get_resources(rest_api_id=api.id)
        assert sorted(r.path for r in resources.items or []) == ["/", "/orders"]

        method = client.get_method(
            rest_api_id=api.id, resource_id=orders.id, http_method="GET"
        )
        assert method.method_integration.type == "MOCK"
        assert list(method.method_responses) == ["200"]

        deployment = client.create_deployment(
            rest_api_id=api.id, stage_name="prod", description="Initial release"
        )
        stage = client.get_stage(rest_api_id=api.id, stage_name="prod")
        assert stage.deployment_id == deployment.id

        client.delete_rest_api(rest_api_id=api.id)
        with pytest.raises(NotFoundException):
            client.get_rest_api(rest_api_id=api.id)
